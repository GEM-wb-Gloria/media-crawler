#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源主流媒体新闻统一爬虫系统 (Unified Multi-Media News Crawler)
全量收录国家网信办《互联网新闻信息稿源单位名单》（2025版）中所有媒体网站：
  - 中央新闻网站和重点理论网站 (全量 31 家)
  - 中央新闻单位报刊网站 (全量 67 家)
  - 部委群团报刊网站 (全量 117 家)
  - 地方新闻网站 (全量 511 家)
  - 其他单位报刊网站 (全量 17 家)
总计 743 家核心新闻媒体，全量支持、无一遗漏！

功能特性:
  1. 智能自适应正文提取器（兼容全量站点的不同CMS架构，自动过滤噪声）
  2. 智能编码探测（自动支持 UTF-8 / GBK / GB2312 / GB18030）
  3. 全局 URL 去重与断点续爬（维护 data/visited_urls.txt）
  4. 多级分层分类存储（严格输出到 data/<媒体类别>/<媒体名称>/<频道>.jsonl）
"""

import os
import re
import json
import time
import random
import logging
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# 导入全量媒体配置中心
try:
    from sites_registry import (
        MEDIA_SITES,
        get_news_media_sites,
        get_sites_by_category,
        list_all_categories,
    )
except ImportError:
    from crawler.sites_registry import (
        MEDIA_SITES,
        get_news_media_sites,
        get_sites_by_category,
        list_all_categories,
    )

# ─── 基础路径与参数配置 ───────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(BASE_DIR, "crawler.log")
VISITED_FILE = os.path.join(DATA_DIR, "visited_urls.txt")

# 礼貌抓取延时区间（秒）
DELAY_MIN = 0.8
DELAY_MAX = 1.6

# HTTP 请求超时与重试
TIMEOUT = 10
MAX_RETRIES = 3

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# ─── 日志系统初始化 ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─── 网络传输与自适应编码处理 ─────────────────────────────────────────────────

class HttpFetcher:
    """高韧性网页抓取器，自适应处理 GBK/GB18030/UTF-8 各种编码及反爬伪装"""

    def __init__(self):
        self.session = requests.Session()

    def fetch_soup(self, url, preferred_encoding=None):
        if not url or not url.startswith("http"):
            return None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive",
                    "Referer": url,
                }
                resp = self.session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
                if resp.status_code != 200:
                    log.warning(f"HTTP {resp.status_code} 跳过: {url}")
                    return None

                raw = resp.content
                text = ""

                # 编码候选池
                candidates = []
                if preferred_encoding:
                    candidates.append(preferred_encoding)

                # meta charset 提取
                meta_enc = re.search(rb'charset=["\']?([\w-]+)', raw[:2048])
                if meta_enc:
                    candidates.append(meta_enc.group(1).decode("ascii", errors="ignore").lower())

                if resp.encoding:
                    candidates.append(resp.encoding.lower())

                candidates.extend(["utf-8", "gb18030", "gbk"])
                valid_candidates = [c for c in candidates if c and "iso-8859" not in c.lower()]

                for enc in valid_candidates:
                    try:
                        text = raw.decode(enc)
                        if "\ufffd" not in text[:400]:
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue

                if not text:
                    text = raw.decode("utf-8", errors="replace")

                return BeautifulSoup(text, "lxml")

            except requests.RequestException as e:
                log.debug(f"[重试 {attempt}/{MAX_RETRIES}] 请求异常 {url}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(1.0 * attempt)

        return None


# ─── 通用智能新闻内容抽取器 ───────────────────────────────────────────────────

class UniversalNewsExtractor:
    """通用智能新闻解析器：站点规则优先 + 文本密度启发式兜底，兼容所有743家媒体"""

    IGNORE_EXTENSIONS = (
        ".jpg", ".png", ".gif", ".pdf", ".zip", ".rar", ".mp4", ".mp3",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".css", ".js"
    )

    @classmethod
    def extract_links(cls, soup, base_url, pattern):
        """从页面提取候选文章链接"""
        links = set()
        parsed_base = urlparse(base_url)
        base_host = parsed_base.netloc.replace("www.", "")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("#"):
                continue
            full_url = urljoin(base_url, href)
            if any(full_url.lower().endswith(ext) for ext in cls.IGNORE_EXTENSIONS):
                continue
            
            # 必须匹配模式，且属于该网站同域或同根域
            if re.search(pattern, full_url):
                clean_url = full_url.split("?")[0].split("#")[0]
                links.add(clean_url)
            elif base_host and base_host in full_url:
                # 针对没有精细正则的通用匹配：包含日期格式或详情路径
                if re.search(r'(\d{4}[/\-_]\d{2}|\d{8}|content_\d+|t\d+_\d+|/c\.|/c\d+-)', full_url):
                    clean_url = full_url.split("?")[0].split("#")[0]
                    links.add(clean_url)

        return list(links)

    @classmethod
    def parse_article(cls, soup, url, site_cfg, channel_name):
        """通用结构化提取单篇新闻的标题、时间、来源、正文、配图"""
        try:
            # 1. 标题提取
            title = ""
            for sel in site_cfg.get("title_selectors", []):
                if sel == "title":
                    t_tag = soup.find("title")
                    if t_tag:
                        raw_title = t_tag.get_text(strip=True)
                        for sep in ["_", "--", "-", "|"]:
                            raw_title = raw_title.split(sep)[0].strip()
                        title = raw_title
                        break
                else:
                    el = soup.select_one(sel)
                    if el:
                        t = el.get_text(strip=True)
                        if len(t) >= 5 and "导航" not in t and "菜单" not in t:
                            title = t
                            break

            if not title:
                h1 = soup.find("h1")
                if h1 and len(h1.get_text(strip=True)) >= 5:
                    title = h1.get_text(strip=True)

            if not title or len(title) < 4:
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

            # 3. 来源提取
            source = ""
            for sel in [".source", "[class*='source']", "p.sou em", ".author", ".origin"]:
                el = soup.select_one(sel)
                if el:
                    s_txt = el.get_text(strip=True)
                    s_txt = re.sub(r'^(来源|稿源|出处|作者)[:：\s]*', '', s_txt).strip()
                    if s_txt and len(s_txt) < 35:
                        source = s_txt
                        break

            # 4. 正文与配图抽取 (智能文本密度 + 专用容器优先)
            content_div = None
            selectors = site_cfg.get("content_selectors", []) + [
                "#rwb_zw", ".detail", ".left_zw", ".u-mainText", ".article-body",
                "#content", ".main-arti", ".TRS_Editor", "#articleText", ".content",
                ".article-content", ".article", ".text", "#Content", ".cnt_bd"
            ]

            for sel in selectors:
                el = soup.select_one(sel)
                if el and len(el.get_text(strip=True)) > 80:
                    content_div = el
                    break

            # 兜底方案：遍历所有 div 找到包含最多文本且 p 标签最多的容器
            if not content_div:
                max_score = 0
                for div in soup.find_all("div"):
                    p_count = len(div.find_all("p"))
                    txt_len = len(div.get_text(strip=True))
                    score = p_count * 100 + txt_len
                    if score > max_score and p_count >= 2 and txt_len > 120:
                        max_score = score
                        content_div = div

            content = ""
            images = []

            if content_div:
                for bad_tag in content_div.find_all(
                    ["script", "style", "ins", "iframe", "noscript", "footer", "button", "nav", "aside"]
                ):
                    bad_tag.decompose()

                p_list = []
                for p in content_div.find_all(["p", "div"]):
                    if p.find(["p"]):
                        continue
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 4:
                        if any(bad in p_text for bad in ["责任编辑", "版权所有", "扫码关注", "分享到", "点击查看"]):
                            continue
                        p_list.append(p_text)

                content = "\n".join(p_list)
                if len(content) < 80:
                    content = content_div.get_text(separator="\n", strip=True)

                for img in content_div.find_all("img", src=True):
                    src = img["src"].strip()
                    if src and not src.startswith("data:") and not src.endswith(".gif"):
                        images.append(urljoin(url, src))

            if len(content) < 50 and not images:
                return None

            return {
                "media_name": site_cfg["name"],
                "media_category": site_cfg["category"],
                "channel": channel_name,
                "url": url,
                "title": title,
                "publish_time": pub_time,
                "source": source or site_cfg["name"],
                "content": content,
                "images": images,
                "crawl_time": datetime.now().isoformat(),
            }

        except Exception as e:
            log.debug(f"解析文章异常 [{site_cfg['name']}] {url}: {e}")
            return None


# ─── 多级分类存储与去重中心 ───────────────────────────────────────────────────

class StorageManager:
    """负责将新闻严格按照【媒体类别 / 媒体名称 / 频道.jsonl】组织入库与全局URL去重"""

    def __init__(self, data_root=DATA_DIR):
        self.data_root = data_root
        self.visited = self.load_visited()

    def load_visited(self):
        if not os.path.exists(VISITED_FILE):
            return set()
        with open(VISITED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def save_visited(self):
        with open(VISITED_FILE, "w", encoding="utf-8") as f:
            for u in sorted(self.visited):
                f.write(u + "\n")

    def is_visited(self, url):
        return url in self.visited

    def mark_visited(self, url):
        self.visited.add(url)

    def save_article(self, article):
        """严格按层级组织落盘: data/<media_category>/<media_name>/<channel>.jsonl"""
        category = article.get("media_category", "其他类别")
        media_name = article.get("media_name", "未知媒体")
        channel = article.get("channel", "综合")

        safe_channel = re.sub(r'[^\w\u4e00-\u9fff]', '_', channel)
        target_dir = os.path.join(self.data_root, category, media_name)
        os.makedirs(target_dir, exist_ok=True)

        file_path = os.path.join(target_dir, f"{safe_channel}.jsonl")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")


# ─── 统一爬虫调度引擎 ─────────────────────────────────────────────────────────

class MultiMediaCrawler:
    def __init__(self):
        self.fetcher = HttpFetcher()
        self.storage = StorageManager()

    def crawl_site(self, site_name, max_articles=80, max_per_channel=25):
        """爬取单个指定站点"""
        if site_name not in MEDIA_SITES:
            log.error(f"未找到媒体站点: {site_name}，可执行 --list-sites 查看完整名单。")
            return 0

        cfg = MEDIA_SITES[site_name]
        cat = cfg["category"]
        home_url = cfg["home_url"]

        if not home_url:
            log.warning(f"媒体【{site_name}】无有效官网链接，跳过。")
            return 0

        log.info(f"\n{'='*65}")
        log.info(f" 🚀 开始抓取媒体: 【{site_name}】")
        log.info(f" 稿源级别: {cat} | 入口URL: {home_url}")
        limit_desc = "不限" if max_articles == 0 else f"{max_articles}篇"
        ch_limit_desc = "不限" if max_per_channel == 0 else f"{max_per_channel}篇/频道"
        log.info(f" 抓取上限: 单站 {limit_desc} | 单频道 {ch_limit_desc}")
        log.info(f"{'='*65}")

        total_saved = 0

        for ch_name, ch_url in cfg["channels"].items():
            if max_articles > 0 and total_saved >= max_articles:
                log.info(f"媒体【{site_name}】达到单站上限 {max_articles} 篇，停止。")
                break

            log.info(f"📂 正在扫描频道: 【{site_name} - {ch_name}】: {ch_url}")
            soup = self.fetcher.fetch_soup(ch_url, preferred_encoding=cfg.get("encoding"))
            if not soup:
                log.warning(f"   无法访问入口: {ch_url}")
                continue

            links = UniversalNewsExtractor.extract_links(soup, ch_url, cfg["url_pattern"])
            log.info(f"   发现文章链接: {len(links)} 条")

            ch_saved = 0
            for link in links:
                if (max_articles > 0 and total_saved >= max_articles) or (
                    max_per_channel > 0 and ch_saved >= max_per_channel
                ):
                    break

                if self.storage.is_visited(link):
                    continue

                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                art_soup = self.fetcher.fetch_soup(link, preferred_encoding=cfg.get("encoding"))
                self.storage.mark_visited(link)

                if not art_soup:
                    continue

                article = UniversalNewsExtractor.parse_article(art_soup, link, cfg, ch_name)
                if article:
                    self.storage.save_article(article)
                    ch_saved += 1
                    total_saved += 1
                    log.info(f"   [{total_saved:>3}] ✓ [{ch_name}] {article['title'][:46]}")

            log.info(f"   频道【{ch_name}】入库: {ch_saved} 篇")

        self.storage.save_visited()
        log.info(f"⭐ 媒体【{site_name}】抓取结束，共入库: {total_saved} 篇\n")
        return total_saved

    def crawl_batch(self, sites_dict, max_per_site=80, max_per_channel=25):
        """批量调度字典中的媒体"""
        summary = {}
        log.info(f"\n{'#'*68}")
        log.info(f"  多源新闻媒体爬虫批量任务启动  |  目标媒体数: {len(sites_dict)}")
        log.info(f"{'#'*68}")

        grand_total = 0
        for i, (name, cfg) in enumerate(sites_dict.items(), 1):
            log.info(f"\n>>> 进度 [{i}/{len(sites_dict)}] 正在处理: {name} ({cfg['category']})")
            saved = self.crawl_site(name, max_articles=max_per_site, max_per_channel=max_per_channel)
            summary[name] = saved
            grand_total += saved
            time.sleep(random.uniform(1.2, 2.0))

        log.info(f"\n{'#'*68}")
        log.info(f"  批量任务全部完成！总计入库: {grand_total} 篇文章")
        log.info(f"{'#'*68}\n")
        return summary


# ─── 统一命令行入口与智能全网调度 ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="国家网信办合规全量媒体统一智能爬虫系统 (全量收录 1432 家主流新闻、报业、广电及政务平台)"
    )
    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="爬取单个媒体（如：人民网、新华网、北京日报、中国政府网等），或设为 'all' 爬取全网所有媒体",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="按稿源大类批量爬取（中央新闻网站和重点理论网站、中央新闻单位报刊网站、部委群团报刊网站、地方新闻网站、其他单位报刊网站、地方新闻单位、中央政务发布平台、省级政务发布平台，或 'all'）",
    )
    parser.add_argument(
        "--sub-cat",
        type=str,
        default=None,
        choices=["报业传媒", "广播电视", "融媒体中心", "all"],
        help="针对【地方新闻单位】进一步指定子类批量爬取",
    )
    parser.add_argument(
        "--max-per-site",
        type=int,
        default=50,
        help="每个媒体最多爬取的文章数（传入 0 表示不限上限）",
    )
    parser.add_argument(
        "--max-per-channel",
        type=int,
        default=20,
        help="纯新闻门户每个频道最多爬取的文章数（传入 0 表示不限上限）",
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="查看全网所有已注册媒体名单及分类统计",
    )

    args = parser.parse_args()

    # 延迟按需加载地方与政务专用爬虫引擎
    from paper_and_broadcast_crawler import LocalUnitsCrawler, load_local_units
    from gov_platform_crawler import GovPlatformCrawler, load_gov_platforms

    local_units = load_local_units()
    gov_platforms = load_gov_platforms()
    news_sites = get_news_media_sites()

    # ── 1. 查看媒体列表 ──
    if args.list_sites:
        print("=" * 72)
        print(f"  国家网信办全量媒体注册清单 (总计收录 1432 家媒体，全网 100% 覆盖)")
        print("=" * 72)
        all_categories = [
            "中央新闻网站和重点理论网站",
            "中央新闻单位报刊网站",
            "部委群团报刊网站",
            "地方新闻网站",
            "其他单位报刊网站",
            "地方新闻单位",
            "中央政务发布平台",
            "省级政务发布平台",
        ]

        for cat in all_categories:
            if args.category and args.category != "all" and args.category != cat:
                continue

            if cat == "地方新闻单位":
                items = local_units
                if args.sub_cat and args.sub_cat != "all":
                    items = [it for it in items if it.get("sub_category") == args.sub_cat]
                print(f"\n【{cat}】 (共 {len(items)} 家):")
                for i, it in enumerate(items[:15], 1):
                    print(f"  {i:3d}. [{it.get('sub_category', '')}] {it['name']:<18s} ({it.get('url')})")
                if len(items) > 15:
                    print(f"  ... 以及其他 {len(items)-15} 家地方报社/电视台/融媒中心 (使用 --category 地方新闻单位 查看全量)")

            elif cat in ("中央政务发布平台", "省级政务发布平台"):
                items = [p for p in gov_platforms if p.get("category") == cat]
                print(f"\n【{cat}】 (共 {len(items)} 家):")
                for i, it in enumerate(items[:15], 1):
                    clean_n = it['name'].replace('\n', '')
                    print(f"  {i:3d}. {clean_n:<22s} ({it.get('url')})")
                if len(items) > 15:
                    print(f"  ... 以及其他 {len(items)-15} 家政务平台")

            else:
                sub = [k for k, v in news_sites.items() if v["category"] == cat]
                print(f"\n【{cat}】 (共 {len(sub)} 家):")
                for i, name in enumerate(sub[:15], 1):
                    url = MEDIA_SITES[name]["home_url"]
                    print(f"  {i:3d}. {name:<18s} ({url})")
                if len(sub) > 15:
                    print(f"  ... 以及其他 {len(sub)-15} 家新闻网")

        print("\n" + "=" * 72)
        return

    # ── 2. 单个媒体调度 (智能分流引擎) ──
    if args.site and args.site != "all":
        site_query = args.site.strip()

        # A. 检查是否匹配政务发布平台
        matched_gov = [p for p in gov_platforms if site_query in p["name"].replace("\n", "")]
        if matched_gov:
            target = matched_gov[0]
            log.info(f"==> 智能路由命中【政务发布平台】专属引擎: {target['name']}")
            gov_crawler = GovPlatformCrawler()
            gov_crawler.crawl_platform(target, max_articles=args.max_per_site)
            return

        # B. 检查是否匹配地方新闻单位（报社/电视台/融媒）
        matched_local = [u for u in local_units if site_query == u["name"] or site_query in u["name"]]
        if matched_local:
            target = matched_local[0]
            log.info(f"==> 智能路由命中【地方报业/广电/融媒】专属引擎: {target['name']} ({target.get('sub_category')})")
            local_crawler = LocalUnitsCrawler()
            local_crawler.crawl_unit(target, max_articles=args.max_per_site)
            return

        # C. 检查是否匹配纯新闻门户
        if site_query in MEDIA_SITES:
            log.info(f"==> 智能路由命中【多源主流新闻】通用引擎: {site_query}")
            news_crawler = MultiMediaCrawler()
            news_crawler.crawl_site(site_query, max_articles=args.max_per_site, max_per_channel=args.max_per_channel)
            return

        # 模糊查找纯新闻门户
        fuzzy_news = [k for k in MEDIA_SITES.keys() if site_query in k]
        if fuzzy_news:
            target = fuzzy_news[0]
            log.info(f"==> 模糊匹配到新闻媒体: {target}")
            news_crawler = MultiMediaCrawler()
            news_crawler.crawl_site(target, max_articles=args.max_per_site, max_per_channel=args.max_per_channel)
            return

        print(f"错误: 未在 1432 家媒体库中找到媒体 '{args.site}'。请执行 python3 media_crawler.py --list-sites 查看已收录媒体。")
        return

    # ── 3. 按分类批量调度 ──
    if args.category and args.category != "all":
        cat = args.category

        if cat == "地方新闻单位":
            target_units = local_units
            if args.sub_cat and args.sub_cat != "all":
                target_units = [u for u in local_units if u.get("sub_category") == args.sub_cat]
            log.info(f"==> 启动【地方新闻单位】批量引擎，目标媒体: {len(target_units)} 家")
            local_crawler = LocalUnitsCrawler()
            for u in target_units:
                local_crawler.crawl_unit(u, max_articles=args.max_per_site)
            return

        elif cat in ("中央政务发布平台", "省级政务发布平台"):
            target_gov = [p for p in gov_platforms if p.get("category") == cat]
            log.info(f"==> 启动【{cat}】批量引擎，目标平台: {len(target_gov)} 家")
            gov_crawler = GovPlatformCrawler()
            for p in target_gov:
                gov_crawler.crawl_platform(p, max_articles=args.max_per_site)
            return

        else:
            matched = get_sites_by_category(cat)
            if not matched:
                print(f"错误: 未找到分类 '{cat}'。")
                return
            log.info(f"==> 启动【{cat}】新闻批量引擎，目标媒体: {len(matched)} 家")
            news_crawler = MultiMediaCrawler()
            news_crawler.crawl_batch(matched, max_per_site=args.max_per_site, max_per_channel=args.max_per_channel)
            return

    # ── 4. 全量全网一键调度 (1432家全覆盖) ──
    log.info("\n" + "=" * 72)
    log.info("  全网全量 1432 家媒体智能调度任务启动 (覆盖新闻网 + 地方报业广电 + 各级政务平台)")
    log.info("=" * 72)

    # 1) 新闻门户批次 (743家)
    log.info(f"\n>>> [1/3] 启动纯新闻门户批次 (共 {len(news_sites)} 家)")
    news_crawler = MultiMediaCrawler()
    news_crawler.crawl_batch(news_sites, max_per_site=args.max_per_site, max_per_channel=args.max_per_channel)

    # 2) 地方新闻单位批次 (573家)
    log.info(f"\n>>> [2/3] 启动地方报社、电视台、融媒体批次 (共 {len(local_units)} 家)")
    local_crawler = LocalUnitsCrawler()
    for u in local_units:
        local_crawler.crawl_unit(u, max_articles=args.max_per_site)

    # 3) 各级政务发布平台批次 (116家)
    log.info(f"\n>>> [3/3] 启动中央与省级政务发布平台批次 (共 {len(gov_platforms)} 家)")
    gov_crawler = GovPlatformCrawler()
    for p in gov_platforms:
        gov_crawler.crawl_platform(p, max_articles=args.max_per_site)

    log.info("\n" + "=" * 72)
    log.info("  全网 1432 家媒体数据爬取任务全部执行完毕！")
    log.info("=" * 72)


if __name__ == "__main__":
    main()

