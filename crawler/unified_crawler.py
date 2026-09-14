#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源媒体全量统一爬虫调度引擎 (Unified Multi-Media Crawler Engine)

全量收录国家网信办《互联网新闻信息稿源单位名单》（2025版，1432家全量支持）：
  1. 中央新闻网站和重点理论网站 (31 家)
  2. 中央新闻单位报刊网站 (67 家)
  3. 部委群团报刊网站 (117 家)
  4. 其他单位报刊网站 (17 家)
  5. 地方新闻网站 (511 家)
  6. 地方新闻单位 (报业传媒/广播电视/融媒体中心，573 家)
  7. 中央政务发布平台 (85 家)
  8. 省级政务发布平台 (31 家)

核心特性：
  - 智能自适应正文提取器（兼容通用新闻CMS、国办指引标准模板、地方大汉/方正系统）
  - 接入 DomainMapper 智能寻址解析器，彻底解决地方台与县融媒的公网域名定位
  - 智能编码探测（自动支持 UTF-8 / GBK / GB2312 / GB18030）
  - 全局 URL 去重与断点续爬（维护 data/visited_urls.txt）
  - 规范分层结构化落盘（data/<媒体类别>/<媒体名称>/<频道>.jsonl）
"""

import os
import re
import sys
import json
import time
import random
import logging
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3
from bs4 import BeautifulSoup

# 忽略 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(BASE_DIR, "crawler.log")
VISITED_FILE = os.path.join(DATA_DIR, "visited_urls.txt")

os.makedirs(DATA_DIR, exist_ok=True)

from sites_registry import (
    MEDIA_SITES,
    get_all_sites,
    get_news_media_sites,
    get_sites_by_category,
    list_all_categories,
)

# 网络配置
TIMEOUT = 10
DELAY_MIN = 0.5
DELAY_MAX = 1.2
MAX_RETRIES = 2

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

# 日志初始化
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("UnifiedCrawler")


# ─── URL 去重管理器 ────────────────────────────────────────────────────────────
class VisitedManager:
    def __init__(self, filepath=VISITED_FILE):
        self.filepath = filepath
        self.visited = set()
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                for line in f:
                    u = line.strip()
                    if u:
                        self.visited.add(u)

    def is_visited(self, url):
        return url in self.visited

    def add(self, url):
        self.visited.add(url)
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(url + "\n")


visited_mgr = VisitedManager()


# ─── 高韧性自适应网络请求器 ──────────────────────────────────────────────────
class UnifiedFetcher:
    def __init__(self):
        self.session = requests.Session()

    def fetch(self, url, preferred_encoding=None):
        if not url or not url.startswith("http"):
            return None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": url,
                }
                resp = self.session.get(url, headers=headers, timeout=TIMEOUT, verify=False, allow_redirects=True)
                if resp.status_code != 200:
                    return None

                raw = resp.content
                candidates = []
                if preferred_encoding:
                    candidates.append(preferred_encoding)

                # meta charset 提取
                meta_m = re.search(rb'charset=["\']?([\w-]+)', raw[:2048])
                if meta_m:
                    candidates.append(meta_m.group(1).decode("ascii", errors="ignore").lower())

                if resp.encoding and "iso-8859" not in resp.encoding.lower():
                    candidates.append(resp.encoding.lower())

                candidates.extend(["utf-8", "gb18030", "gbk", "gb2312"])
                valid_candidates = [c for c in candidates if c and "iso-8859" not in c.lower()]

                text = ""
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

            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(0.5 * attempt)

        return None


# ─── 统一自适应内容抽取器 ───────────────────────────────────────────────────
class UnifiedExtractor:
    @classmethod
    def extract_links(cls, soup, base_url, pattern=None):
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

            # 命中站点配置正则
            if pattern and re.search(pattern, clean_url):
                links.add(clean_url)
                continue

            # 通用新闻特征匹配
            parsed_curr = urlparse(clean_url)
            if base_host and base_host in parsed_curr.netloc:
                if re.search(r'(\d{4}[/\-_]\d{2}|\d{8}|content_\d+|t\d+_\d+|article|detail|news|node_\d+|/c\.|/c\d+-)', clean_url, re.I):
                    links.add(clean_url)
                elif any(clean_url.endswith(s) for s in [".html", ".htm", ".shtml"]) and len(link_text) >= 6:
                    links.add(clean_url)

        return list(links)

    @classmethod
    def parse_article(cls, soup, url, site_cfg, channel_name="综合"):
        # 1. 标题提取
        title = ""
        for sel in site_cfg.get("title_selectors", ["h1", ".title", ".article-title", "title"]):
            if sel == "title":
                t_tag = soup.find("title")
                if t_tag:
                    raw_t = t_tag.get_text(strip=True)
                    for sep in ["_", "--", "-", "|"]:
                        raw_t = raw_t.split(sep)[0].strip()
                    if len(raw_t) >= 4 and not any(bad in raw_t for bad in ["404", "错误", "NotFound"]):
                        title = raw_t
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
            if h1 and len(h1.get_text(strip=True)) >= 4:
                title = h1.get_text(strip=True)

        if not title:
            return None

        # 2. 发布时间提取
        pub_time = ""
        for m_key in ["pubdate", "publishdate", "article:published_time", "time", "date"]:
            m_tag = soup.find("meta", attrs={"name": m_key}) or soup.find("meta", property=m_key)
            if m_tag and m_tag.get("content"):
                m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', m_tag.get("content").strip())
                if m:
                    pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                    break

        if not pub_time:
            for sel in [".time", ".date", ".info", ".source", "p.sou", "[class*='time']", "[class*='date']"]:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', el.get_text(strip=True))
                    if m:
                        pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                        break

        # 3. 来源与发文字号（适配政务平台）
        source = ""
        for sel in [".source", "[class*='source']", "p.sou em", ".author", ".origin"]:
            el = soup.select_one(sel)
            if el:
                s_txt = re.sub(r'^(来源|稿源|出处|作者)[:：\s]*', '', el.get_text(strip=True)).strip()
                if s_txt and len(s_txt) < 40:
                    source = s_txt
                    break

        doc_number = ""
        doc_match = re.search(r'(〔\d{4}〕\d+号|〔\d{4}〕第\d+号|\d{4}第\d+号|[国省市县发办]\d{4}\d+号)', soup.get_text())
        if doc_match:
            doc_number = doc_match.group(1)

        # 4. 正文提取
        content = ""
        content_selectors = site_cfg.get("content_selectors", [])
        for sel in content_selectors:
            box = soup.select_one(sel)
            if box:
                for bad in box.select("script, style, nav, .footer, .header, .share, .comment"):
                    bad.decompose()
                paras = [p.get_text(strip=True) for p in box.find_all(["p", "div"]) if len(p.get_text(strip=True)) > 15]
                txt = "\n".join(paras)
                if len(txt) >= 40:
                    content = txt
                    break

        if not content or len(content) < 40:
            all_p = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
            if all_p:
                combined = "\n".join(all_p)
                if len(combined) >= 40:
                    content = combined

        if not content or len(content) < 30:
            return None

        # 配图提取
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                full_img = urljoin(url, src)
                if not any(full_img.lower().endswith(x) for x in [".gif", ".svg", "icon", "logo"]):
                    images.append(full_img)

        return {
            "media_name": site_cfg["name"],
            "category": site_cfg["category"],
            "channel": channel_name,
            "title": title,
            "publish_time": pub_time or datetime.now().strftime("%Y-%m-%d"),
            "source": source or site_cfg["name"],
            "doc_number": doc_number,
            "content": content,
            "images": images[:5],
            "url": url,
            "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# ─── 核心调度控制层 ───────────────────────────────────────────────────────────
class UnifiedCrawler:
    def __init__(self):
        self.fetcher = UnifiedFetcher()

    def crawl_site(self, site_cfg, max_articles=2):
        name = site_cfg["name"]
        cat = site_cfg["category"]
        channels = site_cfg.get("channels", {})
        if not channels:
            channels = {"综合": site_cfg.get("home_url", "")}

        log.info(f"🚀 开始采集媒体: [{cat}] {name} (入口: {site_cfg.get('home_url')})")
        total_collected = 0

        # 分类输出目录
        safe_cat = cat.replace("/", "_")
        safe_name = name.replace("/", "_").replace("\n", "")
        out_dir = os.path.join(DATA_DIR, safe_cat, safe_name)
        os.makedirs(out_dir, exist_ok=True)

        for ch_name, ch_url in channels.items():
            if total_collected >= max_articles:
                break
            if not ch_url:
                continue

            soup = self.fetcher.fetch(ch_url, preferred_encoding=site_cfg.get("encoding"))
            if not soup:
                continue

            links = UnifiedExtractor.extract_links(soup, ch_url, site_cfg.get("url_pattern"))
            log.info(f"  频道【{ch_name}】共发现候选链接: {len(links)} 条")

            out_file = os.path.join(out_dir, f"{ch_name}.jsonl")

            for link in links:
                if total_collected >= max_articles:
                    break
                if visited_mgr.is_visited(link):
                    continue

                visited_mgr.add(link)
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                art_soup = self.fetcher.fetch(link, preferred_encoding=site_cfg.get("encoding"))
                if not art_soup:
                    continue

                data = UnifiedExtractor.parse_article(art_soup, link, site_cfg, ch_name)
                if data:
                    with open(out_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    total_collected += 1
                    log.info(f"  ✅ [{name}] 成功采集《{data['title'][:25]}...》({len(data['content'])}字)")

        log.info(f"🏁 媒体 [{name}] 采集完成，本次共落盘: {total_collected} 篇\n")
        return total_collected


def main():
    parser = argparse.ArgumentParser(description="多源媒体全量统一爬虫调度系统")
    parser.add_argument("--name", type=str, default="", help="指定媒体名称进行爬取")
    parser.add_argument("--category", type=str, default="", help="指定大类媒体进行爬取")
    parser.add_argument("--all", action="store_true", help="执行全网全量媒体自动化爬取")
    parser.add_argument("--limit", type=int, default=0, help="限制爬取媒体数量 (0为不限制)")
    parser.add_argument("--max-articles", type=int, default=2, help="每家媒体采集篇数 (默认 2)")
    parser.add_argument("--workers", type=int, default=5, help="并发媒体数 (默认 5)")
    parser.add_argument("--list-sites", action="store_true", help="列出已收录的媒体分类概况或指定分类下的媒体清单")
    args = parser.parse_args()

    if args.list_sites:
        if args.category:
            matched = get_sites_by_category(args.category)
            print(f"【{args.category}】收录媒体列表 (共 {len(matched)} 家):")
            for name, info in matched.items():
                print(f"  - {name} ({info.get('home_url')})")
        else:
            print(f"国家网信办全量合规媒体注册中心 (共 {len(MEDIA_SITES)} 家):")
            for cat in list_all_categories():
                c_sites = [k for k, v in MEDIA_SITES.items() if v["category"] == cat]
                print(f"  - 【{cat}】: 共 {len(c_sites)} 家")
            print("\n使用 --list-sites --category <分类名> 可查看该分类下的全部媒体明细。")
        return

    crawler = UnifiedCrawler()

    # 筛选待爬媒体
    target_sites = []
    if args.name:
        if args.name in MEDIA_SITES:
            target_sites.append(MEDIA_SITES[args.name])
        else:
            # 模糊匹配
            matched = [v for k, v in MEDIA_SITES.items() if args.name in k]
            if matched:
                target_sites.extend(matched)
            else:
                print(f"❌ 未找到匹配媒体: {args.name}")
                return
    elif args.category:
        sites_in_cat = get_sites_by_category(args.category)
        target_sites = list(sites_in_cat.values())
    elif args.all:
        target_sites = list(MEDIA_SITES.values())
    else:
        print("请指定 --name、--category 或 --all 参数运行！")
        print("可用媒体总数:", len(MEDIA_SITES))
        print("可用大类列表:")
        for cat in list_all_categories():
            print(f"  - {cat}")
        return

    if args.limit > 0:
        target_sites = target_sites[:args.limit]

    print(f"==================================================")
    print(f"  多源媒体全量统一爬虫调度系统启动")
    print(f"  待采集媒体总数: {len(target_sites)} 家")
    print(f"  每家采样上限: {args.max_articles} 篇")
    print(f"  并发工作线程数: {args.workers}")
    print(f"==================================================\n")

    if args.workers > 1 and len(target_sites) > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(crawler.crawl_site, site, args.max_articles)
                for site in target_sites
            ]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    log.error(f"媒体采集异常: {e}")
    else:
        for site in target_sites:
            try:
                crawler.crawl_site(site, args.max_articles)
            except Exception as e:
                log.error(f"媒体采集异常: {e}")

    print("🎉 爬取任务全部执行完毕！数据已保存至 crawler/data/ 目录。")


if __name__ == "__main__":
    main()
