#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量 1400+ 家媒体网站可访问性与爬取有效性验证脚本
(Full Media Accessibility & Crawling Validation Runner)

核心功能：
1. 并发扫描所有 1432 家媒体的连通性（HTTP/HTTPS、SSL、状态码）
2. 真实尝试提取首页中的文章详情链接，并抓取 1~2 篇有效新闻（包含标题、发布时间、正文）
3. 结构化记录每个站点的验证状态与诊断原因，支持断点续跑
4. 保存爬取到的样本数据，自动生成全景统计分析报告
"""

import os
import re
import sys
import json
import time
import random
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from datetime import datetime

import requests
import urllib3
from bs4 import BeautifulSoup

# 禁用未校验 SSL 的警告信息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BENCHMARK_DIR)
CRAWLER_DIR = os.path.join(PROJECT_ROOT, "crawler")
if CRAWLER_DIR not in sys.path:
    sys.path.insert(0, CRAWLER_DIR)

from sites_registry import MEDIA_SITES

# ─── 路径与输出配置 ───────────────────────────────────────────────────────────
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "validation_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

PROGRESS_FILE = os.path.join(RESULTS_DIR, "validation_log.jsonl")
SAMPLES_FILE = os.path.join(RESULTS_DIR, "sample_articles.jsonl")
SUMMARY_REPORT = os.path.join(RESULTS_DIR, "validation_summary.md")
SUMMARY_JSON = os.path.join(RESULTS_DIR, "validation_summary.json")

# ─── 请求配置 ─────────────────────────────────────────────────────────────────
TIMEOUT = 8
DEFAULT_WORKERS = 25
SAMPLES_PER_SITE = 2

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

IGNORE_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp4", ".mp3", ".avi", ".flv", ".mov", ".wmv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".css", ".js", ".json", ".xml"
)

# 常见正文选择器列表（覆盖绝大部分主流新闻CMS及政务系统）
CONTENT_SELECTORS = [
    "#rwb_zw", ".detail", ".left_zw", ".u-mainText", ".article-body",
    "#content", ".main-arti", ".TRS_Editor", "#articleText", ".content",
    ".article-content", ".article", ".text", "#Content", ".cnt_bd",
    "#UCAP-CONTENT", "#zoom", ".pages_content", ".news-content", "#ozoom",
    ".articleCont", ".con_txt", ".article-detail", ".con-text", ".xl_content"
]

# 常见标题选择器列表
TITLE_SELECTORS = [
    "h1", ".title", ".article-title", ".main-title", ".art-title",
    ".con-tit", ".content-title", "title"
]


def create_session():
    """创建并配置带有默认 Header 的 Session"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
    })
    return session


def detect_and_decode(resp):
    """自适应探测并解码网页内容"""
    raw = resp.content
    candidates = []

    # 1. 从 HTTP Header
    if resp.encoding and "iso-8859" not in resp.encoding.lower():
        candidates.append(resp.encoding.lower())

    # 2. 从 HTML meta charset
    meta_m = re.search(rb'charset=["\']?([\w-]+)', raw[:2048])
    if meta_m:
        enc_str = meta_m.group(1).decode("ascii", errors="ignore").lower()
        candidates.append(enc_str)

    # 3. 兜底编码列表
    candidates.extend(["utf-8", "gb18030", "gbk", "gb2312"])

    for enc in candidates:
        if not enc:
            continue
        try:
            text = raw.decode(enc)
            if "\ufffd" not in text[:300]:
                return text
        except (UnicodeDecodeError, LookupError):
            continue

    return raw.decode("utf-8", errors="replace")


def fetch_html(url, session=None):
    """请求指定 URL 并返回解码后的 HTML 字符串与状态信息"""
    close_sess = False
    if session is None:
        session = create_session()
        close_sess = True

    try:
        resp = session.get(url, timeout=TIMEOUT, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            return None, f"HTTP_{resp.status_code}", resp.status_code
        text = detect_and_decode(resp)
        return text, "OK", 200
    except requests.exceptions.SSLError as e:
        return None, f"SSL_ERROR: {str(e)[:60]}", -1
    except requests.exceptions.ConnectTimeout:
        return None, "CONNECT_TIMEOUT", -2
    except requests.exceptions.ReadTimeout:
        return None, "READ_TIMEOUT", -3
    except requests.exceptions.ConnectionError as e:
        err_msg = str(e)
        if "Name or service not known" in err_msg or "nodename nor servname provided" in err_msg:
            return None, "DNS_FAILURE", -4
        elif "Connection refused" in err_msg:
            return None, "CONNECTION_REFUSED", -5
        return None, f"CONNECTION_ERROR: {err_msg[:60]}", -6
    except Exception as e:
        return None, f"REQUEST_ERROR: {str(e)[:60]}", -7
    finally:
        if close_sess:
            session.close()


def extract_candidate_links(soup, base_url, site_pattern=None):
    """从页面中提取潜在的新闻文章链接"""
    links = set()
    parsed_base = urlparse(base_url)
    base_host = parsed_base.netloc.replace("www.", "")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        link_text = a.get_text(strip=True)
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        full_url = urljoin(base_url, href)
        clean_url = full_url.split("?")[0].split("#")[0]

        if any(clean_url.lower().endswith(ext) for ext in IGNORE_EXTENSIONS):
            continue

        # 站点注册的特定正则优先
        if site_pattern and re.search(site_pattern, clean_url):
            links.add(clean_url)
            continue

        # 通用启发式匹配：必须与原站同根域名或包含其主机名
        parsed_curr = urlparse(clean_url)
        if not (base_host and base_host in parsed_curr.netloc):
            continue

        # 特征1: 路径含日期格式 (2024/01/02, 20250310等)
        # 特征2: 路径含 content_, t202x, article, detail, node_
        # 特征3: 以 .html, .htm, .shtml 结尾且链接文字大于等于 6 个字
        is_news_pattern = bool(re.search(
            r'(\d{4}[/\-_]\d{2}|\d{8}|content_\d+|t\d+_\d+|article|detail|news|node_\d+|/c\.|/c\d+-)',
            clean_url, re.IGNORECASE
        ))
        is_html_with_title = (
            any(clean_url.endswith(s) for s in [".html", ".htm", ".shtml"])
            and len(link_text) >= 6
            and not any(x in link_text for x in ["首页", "更多", "登录", "注册", "关于我们", "联系我们"])
        )

        if is_news_pattern or is_html_with_title:
            links.add(clean_url)

    # 优先打乱挑选，避开全部聚集在同一导航栏
    link_list = list(links)
    random.shuffle(link_list)
    return link_list[:20]  # 最多保留 20 个候选供探测


def parse_news_content(soup, url):
    """解析单篇文章内容，提取标题、时间、正文"""
    # 1. 标题提取
    title = ""
    for sel in TITLE_SELECTORS:
        if sel == "title":
            t_tag = soup.find("title")
            if t_tag:
                raw_title = t_tag.get_text(strip=True)
                for sep in ["_", "--", "-", "|"]:
                    raw_title = raw_title.split(sep)[0].strip()
                if len(raw_title) >= 4 and not any(x in raw_title for x in ["404", "错误", "NotFound", "Not Found"]):
                    title = raw_title
                    break
        else:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(strip=True)
                if len(t) >= 4 and "导航" not in t and "菜单" not in t:
                    title = t
                    break

    if not title:
        h1 = soup.find("h1")
        if h1:
            t = h1.get_text(strip=True)
            if len(t) >= 4:
                title = t

    if not title:
        return None

    # 2. 发布时间提取
    pub_time = ""
    for m_key in ["pubdate", "publishdate", "article:published_time", "time", "date"]:
        m_tag = soup.find("meta", attrs={"name": m_key}) or soup.find("meta", property=m_key)
        if m_tag and m_tag.get("content"):
            raw_c = m_tag.get("content").strip()
            m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', raw_c)
            if m:
                pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                break

    if not pub_time:
        for sel in [".time", ".date", ".info", ".source", "p.sou", "[class*='time']", "[class*='date']"]:
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', txt)
                if m:
                    pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                    break

    # 3. 正文提取
    content = ""
    # 策略A：指定选择器
    for sel in CONTENT_SELECTORS:
        container = soup.select_one(sel)
        if container:
            # 移除常见干扰元素
            for bad in container.select("script, style, nav, .footer, .header, .share, .comment"):
                bad.decompose()
            paras = [p.get_text(strip=True) for p in container.find_all(["p", "div"]) if len(p.get_text(strip=True)) > 15]
            txt = "\n".join(paras)
            if len(txt) >= 40:
                content = txt
                break

    # 策略B：通用段落启发式
    if not content or len(content) < 40:
        all_p = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
        if all_p:
            combined = "\n".join(all_p)
            if len(combined) >= 40:
                content = combined

    if not content or len(content) < 40:
        return None

    return {
        "title": title,
        "publish_time": pub_time,
        "content": content[:300],  # 样本只截取前 300 字
        "content_length": len(content),
        "url": url,
    }


def validate_single_site(site_info, max_samples=SAMPLES_PER_SITE):
    """
    验证单个站点的可访问性与爬取有效性：
    1. 连通性测试 (Home URL)
    2. 发现候选文章链接
    3. 抓取 1~2 篇有效新闻
    """
    name = site_info["name"]
    category = site_info["category"]
    home_url = site_info["home_url"]
    url_pattern = site_info.get("url_pattern")

    result = {
        "name": name,
        "category": category,
        "home_url": home_url,
        "status": "UNKNOWN",
        "http_code": 0,
        "response_time_ms": 0,
        "links_found": 0,
        "crawled_count": 0,
        "samples": [],
        "error_msg": "",
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not home_url:
        result["status"] = "NO_URL"
        result["error_msg"] = "清单中缺少 URL 配置"
        return result

    session = create_session()
    start_time = time.time()

    # Step 1: 访问首页
    html, msg, code = fetch_html(home_url, session)
    result["response_time_ms"] = int((time.time() - start_time) * 1000)
    result["http_code"] = code

    if not html:
        result["status"] = msg.split(":")[0]
        result["error_msg"] = msg
        session.close()
        return result

    # Step 2: 提取候选链接
    soup = BeautifulSoup(html, "lxml")
    candidate_links = extract_candidate_links(soup, home_url, url_pattern)
    result["links_found"] = len(candidate_links)

    if not candidate_links:
        result["status"] = "ACCESSIBLE_NO_LINKS"
        result["error_msg"] = "首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站）"
        session.close()
        return result

    # Step 3: 尝试抓取有效文章
    successful_samples = []
    crawl_attempts = 0

    for link in candidate_links:
        if len(successful_samples) >= max_samples:
            break
        crawl_attempts += 1
        sub_html, sub_msg, sub_code = fetch_html(link, session)
        if not sub_html:
            continue

        sub_soup = BeautifulSoup(sub_html, "lxml")
        article_data = parse_news_content(sub_soup, link)
        if article_data:
            successful_samples.append(article_data)

    result["crawled_count"] = len(successful_samples)
    result["samples"] = successful_samples

    if successful_samples:
        result["status"] = "SUCCESS"
        result["error_msg"] = ""
    else:
        result["status"] = "PARSED_NO_TEXT"
        result["error_msg"] = f"成功提取并尝试了 {crawl_attempts} 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页）"

    session.close()
    return result


def load_completed_records():
    """读取已完成的进度记录"""
    completed = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    completed[data["name"]] = data
                except Exception:
                    pass
    return completed


def append_progress(record):
    """追加写入验证进度"""
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 若有抓取成功的样本，写入样本文件
    if record.get("samples"):
        with open(SAMPLES_FILE, "a", encoding="utf-8") as f:
            for sample in record["samples"]:
                sample_item = {
                    "media_name": record["name"],
                    "category": record["category"],
                    "home_url": record["home_url"],
                    **sample
                }
                f.write(json.dumps(sample_item, ensure_ascii=False) + "\n")


def generate_summary_report(all_results):
    """生成全量统计分析报告 Markdown 与 JSON"""
    total = len(all_results)
    if total == 0:
        return

    status_counts = {}
    category_stats = {}

    for r in all_results.values():
        st = r["status"]
        cat = r["category"]
        status_counts[st] = status_counts.get(st, 0) + 1

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "success": 0, "accessible": 0, "failed": 0}
        category_stats[cat]["total"] += 1
        if st == "SUCCESS":
            category_stats[cat]["success"] += 1
            category_stats[cat]["accessible"] += 1
        elif st in ("ACCESSIBLE_NO_LINKS", "PARSED_NO_TEXT"):
            category_stats[cat]["accessible"] += 1
        else:
            category_stats[cat]["failed"] += 1

    success_total = status_counts.get("SUCCESS", 0)
    accessible_total = sum(v["accessible"] for v in category_stats.values())

    # 保存 JSON 汇总
    summary_data = {
        "total_sites": total,
        "success_crawled": success_total,
        "success_rate": f"{(success_total / total * 100):.2f}%" if total else "0%",
        "accessible_sites": accessible_total,
        "accessible_rate": f"{(accessible_total / total * 100):.2f}%" if total else "0%",
        "status_breakdown": status_counts,
        "category_breakdown": category_stats,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    # 编写 Markdown 报告
    md = []
    md.append("# 全网 1400+ 家媒体网站可访问性与爬虫实际抓取有效性全面验证报告\n")
    md.append(f"> 生成时间：{summary_data['generated_at']}\n")
    md.append("## 一、总体健康度与抓取成果概览\n")
    md.append(f"- **媒体收录总数**：`{total}` 家")
    md.append(f"- **可正常访问并成功爬取完整文章**：**`{success_total}`** 家（**成功率 {summary_data['success_rate']}**）")
    md.append(f"- **网站可连通总数**：**`{accessible_total}`** 家（**可达率 {summary_data['accessible_rate']}**）")
    md.append(f"- **不可连通/严重异常**：`{total - accessible_total}` 家\n")

    md.append("## 二、各分类媒体验证情况一览\n")
    md.append("| 媒体分类 | 媒体总数 | 爬取成功 | 成功率 | 网站可达数 | 可达率 | 异常不可达 |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for cat, stat in sorted(category_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        c_tot = stat["total"]
        c_suc = stat["success"]
        c_acc = stat["accessible"]
        c_fail = stat["failed"]
        suc_rate = f"{(c_suc / c_tot * 100):.1f}%" if c_tot else "0%"
        acc_rate = f"{(c_acc / c_tot * 100):.1f}%" if c_tot else "0%"
        md.append(f"| {cat} | {c_tot} | {c_suc} | {suc_rate} | {c_acc} | {acc_rate} | {c_fail} |")
    md.append("\n")

    md.append("## 三、站点状态详细分布\n")
    md.append("| 状态分类 | 站点数量 | 占比 | 状态说明 |")
    md.append("| :--- | :---: | :---: | :--- |")
    status_desc = {
        "SUCCESS": "可正常访问，且成功抓取到 1~2 篇包含标题与正文的新闻",
        "PARSED_NO_TEXT": "网站可访问且发现详情链接，但内容为纯图片/PDF数字报或未匹配正文选择器",
        "ACCESSIBLE_NO_LINKS": "网站首页正常打开，但首页未发现静态规范新闻文章超链接（如纯视频/JS单页应用）",
        "CONNECT_TIMEOUT": "连接超时（服务器响应极慢或阻断连接）",
        "READ_TIMEOUT": "读取超时",
        "DNS_FAILURE": "DNS 域名解析失败（域名已失效或停用）",
        "CONNECTION_REFUSED": "连接被拒绝（服务器端口关闭）",
        "HTTP_403": "HTTP 403 Forbidden（触发 WAF 强反爬策略或白名单限制）",
        "HTTP_404": "HTTP 404 Not Found（主页路径丢失）",
        "HTTP_500": "HTTP 500/502/503 服务器内部错误",
        "SSL_ERROR": "SSL 握手协议错误或算法不兼容",
    }
    for st, cnt in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        desc = status_desc.get(st, "其他网络或解析错误")
        pct = f"{(cnt / total * 100):.2f}%" if total else "0%"
        md.append(f"| `{st}` | {cnt} | {pct} | {desc} |")
    md.append("\n")

    # 失败与异常站点清单
    md.append("## 四、未成功爬取站点的典型原因与排查清单\n")
    failed_sites = [r for r in all_results.values() if r["status"] != "SUCCESS"]
    if failed_sites:
        md.append(f"共有 `{len(failed_sites)}` 家站点未能直接通过通用静态爬虫提取文章，以下列出典型问题分类：\n")
        # 按状态分组列出
        grouped_failed = {}
        for f in failed_sites:
            grouped_failed.setdefault(f["status"], []).append(f)

        for st, f_list in sorted(grouped_failed.items(), key=lambda x: len(x[1]), reverse=True):
            md.append(f"### 状态: `{st}` (共 {len(f_list)} 家)")
            md.append("| 媒体名称 | 分类 | URL | 诊断详情 |")
            md.append("| :--- | :--- | :--- | :--- |")
            for item in f_list[:15]:  # 每个状态最多列出 15 家供查看
                err = item["error_msg"].replace("\n", " ")[:60]
                md.append(f"| {item['name']} | {item['category']} | [{item['home_url']}]({item['home_url']}) | {err} |")
            if len(f_list) > 15:
                md.append(f"| ... *其余 {len(f_list) - 15} 家详见完整 JSON 日志* | | | |")
            md.append("\n")

    with open(SUMMARY_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return summary_data


def main():
    parser = argparse.ArgumentParser(description="全量 1400+ 家媒体网站可访问性与爬取有效性验证")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"并发线程数 (默认 {DEFAULT_WORKERS})")
    parser.add_argument("--limit", type=int, default=0, help="限制验证媒体数量 (0 为全部)")
    parser.add_argument("--samples", type=int, default=SAMPLES_PER_SITE, help=f"每家媒体抓取样本数 (默认 {SAMPLES_PER_SITE})")
    parser.add_argument("--category", type=str, default="", help="仅测试指定大类媒体")
    parser.add_argument("--reset", action="store_true", help="清空历史进度重新测试")
    parser.add_argument("--report-only", action="store_true", help="仅根据已有日志重新生成总结报告")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        if os.path.exists(SAMPLES_FILE):
            os.remove(SAMPLES_FILE)
        print("已重置所有历史验证日志。")

    completed_records = load_completed_records()

    if args.report_only:
        print(f"根据当前已完成的 {len(completed_records)} 条记录生成报告...")
        summary = generate_summary_report(completed_records)
        print(f"报告已生成至: {SUMMARY_REPORT}")
        return

    # 获取全量待测试媒体
    all_sites = MEDIA_SITES
    target_sites = []
    for name, site_info in all_sites.items():
        if args.category and site_info["category"] != args.category:
            continue
        target_sites.append(site_info)

    if args.limit > 0:
        target_sites = target_sites[:args.limit]

    total_count = len(target_sites)
    pending_sites = [s for s in target_sites if s["name"] not in completed_records]

    print(f"==================================================")
    print(f"  全量媒体可访问性与爬取有效性验证引擎启动")
    print(f"  目标媒体总数: {total_count} 家")
    print(f"  已完成历史验证: {len(completed_records)} 家")
    print(f"  本次待验证数量: {len(pending_sites)} 家")
    print(f"  并发工作线程数: {args.workers}")
    print(f"  每家采样文章数: {args.samples}")
    print(f"==================================================\n")

    if not pending_sites:
        print("所有指定媒体均已验证完毕！正在重新生成汇总报告...")
        generate_summary_report(completed_records)
        print(f"报告已更新至: {SUMMARY_REPORT}")
        return

    start_run_time = time.time()
    processed_count = 0
    current_success = sum(1 for r in completed_records.values() if r["status"] == "SUCCESS")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_site = {
            executor.submit(validate_single_site, site, args.samples): site
            for site in pending_sites
        }

        for future in as_completed(future_to_site):
            site = future_to_site[future]
            try:
                res = future.result()
            except Exception as e:
                res = {
                    "name": site["name"],
                    "category": site["category"],
                    "home_url": site["home_url"],
                    "status": "UNHANDLED_EXCEPTION",
                    "http_code": -99,
                    "response_time_ms": 0,
                    "links_found": 0,
                    "crawled_count": 0,
                    "samples": [],
                    "error_msg": str(e)[:100],
                    "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

            completed_records[res["name"]] = res
            append_progress(res)

            processed_count += 1
            if res["status"] == "SUCCESS":
                current_success += 1
                status_symbol = "✅ 爬取成功"
            elif res["status"] in ("ACCESSIBLE_NO_LINKS", "PARSED_NO_TEXT"):
                status_symbol = f"⚠️ 连通但未爬到正文 ({res['status']})"
            else:
                status_symbol = f"❌ 访问异常 ({res['status']})"

            # 实时进度打印
            total_done = len(completed_records)
            pct = (total_done / total_count) * 100
            print(f"[{total_done}/{total_count} {pct:5.1f}%] {status_symbol} | {res['name']} ({res['response_time_ms']}ms) | 文章: {res['crawled_count']} 篇")

            # 每 50 家自动刷新一次总览报告
            if processed_count % 50 == 0:
                generate_summary_report(completed_records)

    # 最终生成一次完整报告
    summary = generate_summary_report(completed_records)
    elapsed = time.time() - start_run_time

    print("\n" + "=" * 50)
    print("  全量媒体验证全部完成！")
    print(f"  总耗时: {elapsed:.1f} 秒")
    print(f"  最终统计: 总媒体 {summary['total_sites']} 家")
    print(f"  爬取成功: {summary['success_crawled']} 家 ({summary['success_rate']})")
    print(f"  网站可达: {summary['accessible_sites']} 家 ({summary['accessible_rate']})")
    print(f"  完整报告: {SUMMARY_REPORT}")
    print(f"  样本数据: {SAMPLES_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
