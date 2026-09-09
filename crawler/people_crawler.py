#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人民网新闻爬虫 (People's Daily Crawler)
目标: http://www.people.com.cn
功能: 爬取首页及各频道新闻的标题、正文、时间、来源、URL等
语言选择理由: Python + requests + BeautifulSoup
  - 人民网为服务端渲染的静态HTML，无需无头浏览器
  - requests 处理 HTTP 高效稳定，对 GB2312/UTF-8 混合编码支持好
  - BeautifulSoup + lxml 解析中文 HTML 准确率高
  - 生态丰富，适合后续与 NLP/事实核查流水线集成
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
import re
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

# ─── 配置区 ────────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE   = os.path.join(BASE_DIR, "crawler.log")

# 礼貌延迟（秒），随机化以避免被封
DELAY_MIN = 1.0
DELAY_MAX = 2.5

# 单次运行最多爬取的文章数（0 = 不限）
MAX_ARTICLES = 500

# 请求超时
TIMEOUT = 15

# 重试次数
MAX_RETRIES = 3

# User-Agent 轮换池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

# 要爬取的频道入口（频道名 -> 频道首页URL）
CHANNELS = {
    "首页":     "http://www.people.com.cn",
    "时政":     "http://politics.people.com.cn/",
    "国际":     "http://world.people.com.cn/",
    "经济科技": "http://finance.people.com.cn/",
    "社会法治": "http://society.people.com.cn/",
    "文旅体育": "http://ent.people.com.cn/",
    "健康生活": "http://health.people.com.cn/",
    "军事":     "http://military.people.com.cn/",
    "观点":     "http://opinion.people.com.cn/",
    "教育":     "http://edu.people.com.cn/",
    "反腐":     "http://fanfu.people.com.cn/",
    "理论":     "http://theory.people.com.cn/",
    "党建":     "http://dangjian.people.com.cn/",
}

# ─── 日志配置 ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─── 工具函数 ──────────────────────────────────────────────────────────────────

def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "http://www.people.com.cn/",
    })
    return session


def fetch(session, url):
    """抓取页面，自动处理 GB2312/UTF-8 编码，带重试"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()

            raw = resp.content
            # 从 meta 标签或 HTTP 头检测编码
            meta_enc = re.search(rb'charset=["\']?([\w-]+)', raw[:2048])
            if meta_enc:
                enc = meta_enc.group(1).decode("ascii", errors="ignore").lower()
                if enc in ("gb2312", "gbk", "gb18030"):
                    text = raw.decode(enc, errors="replace")
                else:
                    text = raw.decode("utf-8", errors="replace")
            elif resp.encoding and resp.encoding.lower() in ("gb2312", "gbk", "gb18030"):
                text = raw.decode(resp.encoding, errors="replace")
            else:
                text = raw.decode("utf-8", errors="replace")

            return BeautifulSoup(text, "lxml")

        except requests.RequestException as e:
            log.warning(f"[尝试 {attempt}/{MAX_RETRIES}] 请求失败 {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    return None


def polite_sleep():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def is_article_url(url):
    """判断 URL 是否为文章详情页"""
    if not url:
        return False
    parsed = urlparse(url)
    if not re.search(r'people\.(com\.cn|cn)', parsed.netloc):
        return False
    path = parsed.path
    # 人民网文章URL特征：含 /n1/ /n2/ /nw/ 或 /cXXX-XXXX.html 格式
    if re.search(r'/(n1|n2|nw|n)/', path):
        return True
    if re.match(r'.*/c\d+-\d+\.html$', path):
        return True
    return False


def normalize_url(base, href):
    if not href or href.startswith("javascript:") or href == "#":
        return None
    return urljoin(base, href.strip())


# ─── 链接提取 ──────────────────────────────────────────────────────────────────

def extract_article_links(soup, base_url):
    links = set()
    for a in soup.find_all("a", href=True):
        url = normalize_url(base_url, a["href"])
        if url and is_article_url(url):
            links.add(url)
    return list(links)


# ─── 文章解析 ──────────────────────────────────────────────────────────────────

def parse_article(soup, url, channel):
    """解析文章页，提取结构化字段"""
    try:
        # ── 标题 ──
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            og = soup.find("meta", property="og:title")
            if og:
                title = og.get("content", "").strip()
        if not title:
            t = soup.find("title")
            if t:
                title = t.get_text(strip=True).split("_")[0].split("--")[0].strip()
        if not title:
            return None

        # ── 发布时间 ──
        pub_time = ""
        for sel in ["p.sou", "span.time", "[class*='time']", "[class*='date']",
                    ".box01 .fl", "p.time", ".show_time"]:
            el = soup.select_one(sel)
            if el:
                raw_t = el.get_text(strip=True)
                m = re.search(r'\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}', raw_t)
                if m:
                    pub_time = m.group()
                    tm = re.search(r'\d{2}:\d{2}(:\d{2})?', raw_t)
                    if tm:
                        pub_time += " " + tm.group()
                    break
        if not pub_time:
            for meta_name in ["pubdate", "publishdate", "article:published_time"]:
                m_tag = (soup.find("meta", attrs={"name": meta_name}) or
                         soup.find("meta", property=meta_name))
                if m_tag:
                    pub_time = m_tag.get("content", "").strip()
                    break

        # ── 来源 ──
        source = ""
        for sel in ["[class*='source']", "[class*='origin']",
                    "p.sou em", ".box_con em", ".show_source"]:
            el = soup.select_one(sel)
            if el:
                source = el.get_text(strip=True)
                break

        # ── 关键词 ──
        keywords = ""
        kw_tag = soup.find("meta", attrs={"name": "keywords"})
        if kw_tag:
            keywords = kw_tag.get("content", "").strip()

        # ── 描述（摘要）──
        description = ""
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            description = desc_tag.get("content", "").strip()

        # ── 正文 ──
        content = ""
        content_selectors = [
            "#rwb_zw",        # 人民网最常见正文容器
            ".rm_txt_con",
            "#content",
            ".box_con",
            ".article_content",
            ".text",
            "#p_content",
        ]
        content_div = None
        for sel in content_selectors:
            content_div = soup.select_one(sel)
            if content_div:
                break

        if content_div:
            for tag in content_div.find_all(
                    ["script", "style", "ins", "iframe", "noscript"]):
                tag.decompose()
            paragraphs = []
            for p in content_div.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 5:
                    paragraphs.append(text)
            content = "\n".join(paragraphs)
            if len(content) < 100:
                content = content_div.get_text(separator="\n", strip=True)

        # ── 文章内图片 ──
        images = []
        if content_div:
            for img in content_div.find_all("img", src=True):
                img_url = normalize_url(url, img["src"])
                if img_url:
                    images.append(img_url)

        # 过滤正文过短且无图片的页面
        if len(content) < 50 and not images:
            return None

        return {
            "url":          url,
            "channel":      channel,
            "title":        title,
            "publish_time": pub_time,
            "source":       source,
            "keywords":     keywords,
            "description":  description,
            "content":      content,
            "images":       images,
            "crawl_time":   datetime.now().isoformat(),
        }

    except Exception as e:
        log.error(f"解析文章出错 {url}: {e}")
        return None


# ─── 断点续爬 ──────────────────────────────────────────────────────────────────

VISITED_FILE = os.path.join(OUTPUT_DIR, "visited_urls.txt")

def load_visited():
    if not os.path.exists(VISITED_FILE):
        return set()
    with open(VISITED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_visited(urls):
    with open(VISITED_FILE, "w", encoding="utf-8") as f:
        for u in sorted(urls):
            f.write(u + "\n")


# ─── 写出数据 ──────────────────────────────────────────────────────────────────

def save_article(article, channel):
    """按频道写入 JSON Lines 文件"""
    safe_channel = re.sub(r'[^\w\u4e00-\u9fff]', '_', channel)
    out_file = os.path.join(OUTPUT_DIR, f"{safe_channel}.jsonl")
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(article, ensure_ascii=False) + "\n")


# ─── 主流程 ────────────────────────────────────────────────────────────────────

def crawl():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    visited = load_visited()
    session = get_session()

    total_saved = 0
    all_new_visited = set()

    log.info(f"{'='*50}")
    log.info(f"  人民网爬虫启动  |  已有记录 {len(visited)} 条")
    log.info(f"{'='*50}")

    for channel_name, channel_url in CHANNELS.items():
        if MAX_ARTICLES and total_saved >= MAX_ARTICLES:
            log.info(f"已达最大文章数 {MAX_ARTICLES}，停止。")
            break

        log.info(f"\n── 频道: 【{channel_name}】{channel_url}")

        soup = fetch(session, channel_url)
        if not soup:
            log.warning(f"频道首页抓取失败: {channel_url}")
            continue

        article_links = extract_article_links(soup, channel_url)
        log.info(f"   发现文章链接: {len(article_links)} 条")

        channel_saved = 0
        for art_url in article_links:
            if MAX_ARTICLES and total_saved >= MAX_ARTICLES:
                break
            if art_url in visited:
                continue

            polite_sleep()
            art_soup = fetch(session, art_url)
            all_new_visited.add(art_url)

            if not art_soup:
                continue

            article = parse_article(art_soup, art_url, channel_name)
            if article:
                save_article(article, channel_name)
                channel_saved += 1
                total_saved += 1
                log.info(f"   [{total_saved:>4}] ✓ {article['title'][:55]}")
            else:
                log.debug(f"   跳过（内容不足）: {art_url}")

        log.info(f"   频道【{channel_name}】本次保存: {channel_saved} 篇")
        polite_sleep()

    visited |= all_new_visited
    save_visited(visited)

    log.info(f"\n{'='*50}")
    log.info(f"  爬取完成！本次共保存 {total_saved} 篇文章")
    log.info(f"  数据目录: {OUTPUT_DIR}")
    log.info(f"{'='*50}")
    return total_saved


if __name__ == "__main__":
    crawl()
