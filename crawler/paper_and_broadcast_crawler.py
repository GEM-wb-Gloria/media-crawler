#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地方新闻单位专属高效爬虫系统 (Local News Units Crawler)
专门针对国家网信办名单中第 7 大类【地方新闻单位】（全量 573 家媒体）设计开发：
  1. 地方报社/报业传媒 (346 家，如北京日报、解放日报、广州日报、大众日报、四川日报等)
  2. 地方广播电视台/广电台网 (192 家，如各省市广播电视总台、北京时间、广视网等)
  3. 地方融媒体中心 (35 家，如县区融媒微门户)

核心技术特性:
  - 自动适配方正翔宇/大汉电子报版面系统（#ozoom, .news-content, td.font01）；
  - 自动剥离广电流媒体视频占位符，抽取播报文稿与关键帧配图；
  - 严格分类归档至:
      data/地方新闻单位/报业传媒/<媒体名>/
      data/地方新闻单位/广播电视/<媒体名>/
      data/地方新闻单位/融媒体中心/<媒体名>/
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(BASE_DIR, "crawler.log")
VISITED_FILE = os.path.join(DATA_DIR, "visited_urls.txt")
MANIFEST_FILE = os.path.join(BASE_DIR, "all_media_manifest.json")

DELAY_MIN = 0.8
DELAY_MAX = 1.6
TIMEOUT = 10
MAX_RETRIES = 3

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# 主流地方报业与广电台网权威域名映射表
LOCAL_OFFICIAL_DOMAINS = {
    "北京日报": "https://www.bjd.com.cn",
    "北京晚报": "https://bjwb.bjd.com.cn",
    "北京青年报": "https://www.ynet.com",
    "新京报": "https://www.bjnews.com.cn",
    "北京商报": "https://www.bbtnews.com.cn",
    "北京广播电视台": "https://www.brtv.org.cn",
    "天津日报": "http://epaper.tianjinwe.com",
    "今晚报": "http://epaper.jwb.com.cn",
    "天津广播电视台": "https://www.tjtv.com.cn",
    "河北日报": "https://hbrb.hebnews.cn",
    "山西日报": "http://epaper.sxrb.com",
    "解放日报": "https://www.shobserver.com",
    "文汇报": "http://dzb.whb.cn",
    "新民晚报": "https://paper.xinmin.cn",
    "上海广播电视台": "https://www.smg.cn",
    "大众日报": "http://dzrb.dzwww.com",
    "齐鲁晚报": "http://epaper.qlwb.com.cn",
    "山东广播电视台": "https://www.iqilu.com",
    "广州日报": "https://gzdaily.dayoo.com",
    "羊城晚报": "https://epaper.ycwb.com",
    "南方日报": "https://epaper.southcn.com",
    "深圳特区报": "https://sztqb.sznews.com",
    "广东广播电视台": "https://www.gdtv.cn",
    "四川日报": "https://epaper.scdaily.cn",
    "成都商报": "http://static.cdsb.com",
    "四川广播电视台": "https://www.sctv.com",
    "重庆日报": "https://epaper.cqrb.cn",
    "重庆广播电视集团（总台）": "https://www.cbg.cn",
    "湖北日报": "https://epaper.hubeidaily.net",
    "湖北广播电视台": "https://www.hbtv.com.cn",
    "湖南日报": "https://epaper.voc.com.cn",
    "浙江日报": "https://zjrb.zjol.com.cn",
    "浙江广电集团": "https://www.zjstv.com",
    "新华日报": "http://xh.xhby.net",
    "江苏省广播电视总台": "https://www.jstv.com",
    "福建日报": "https://fjrb.fjdaily.com",
    "江西日报": "http://epaper.jxxw.com.cn",
    "河南日报": "https://newpaper.dahe.cn",
    "陕西日报": "https://esb.sxdaily.com.cn",
}


def load_local_units():
    """加载全部 573 家地方新闻单位并适配权威域名"""
    if not os.path.exists(MANIFEST_FILE):
        return []
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        all_items = json.load(f)

    units = []
    for it in all_items:
        if it.get("category") == "地方新闻单位":
            name = it.get("name", "")
            if name in LOCAL_OFFICIAL_DOMAINS:
                it["url"] = LOCAL_OFFICIAL_DOMAINS[name]
            elif it.get("url") and "www." in it["url"] and ".cn" in it["url"]:
                try:
                    p = urlparse(it["url"])
                    host_encoded = p.netloc.encode("idna").decode("ascii")
                    it["url"] = f"{p.scheme or 'http'}://{host_encoded}"
                except:
                    pass
            units.append(it)
    return units


class LocalUnitArticleParser:
    """专为地方报社电子报与广电台网设计的内容解析器"""

    # 报纸与广电常用正文选择器
    CONTENT_SELECTORS = [
        "#ozoom", ".news-content", "#articleContent", "#fontzoom", ".article-content",
        ".detail-content", ".text_content", "#content", ".cnt_bd", ".content",
        ".detail_con", ".main-text", "td.font01", "#artibody", ".video-detail",
        ".TRS_Editor", "#UCAP-CONTENT"
    ]

    @classmethod
    def extract_links(cls, soup, base_url):
        links = set()
        parsed_base = urlparse(base_url)
        base_host = parsed_base.netloc.replace("www.", "")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("#"):
                continue
            full_url = urljoin(base_url, href)
            # 过滤非文章资源
            if any(full_url.lower().endswith(ext) for ext in [".jpg", ".png", ".pdf", ".mp4", ".mp3", ".zip"]):
                continue

            # 匹配典型报刊与广电文章特征
            if re.search(r'(\d{4}[/\-_]\d{2}|\d{8}|content_\d+|node_\d+|t\d+_\d+|article|/detail/|/news/)', full_url):
                clean_url = full_url.split("?")[0].split("#")[0]
                links.add(clean_url)
            elif base_host and base_host in full_url:
                if re.search(r'(/\d{6,}/|\.shtml|\.htm|\.html)', full_url):
                    clean_url = full_url.split("?")[0].split("#")[0]
                    links.add(clean_url)

        return list(links)

    @classmethod
    def parse(cls, soup, url, media_info):
        try:
            # 1. 标题提取
            title = ""
            for h in soup.find_all(["h1", "h2"]):
                txt = h.get_text(strip=True)
                if len(txt) >= 5 and "导航" not in txt and "版权" not in txt:
                    title = txt
                    break

            if not title:
                t_tag = soup.find("title")
                if t_tag:
                    raw = t_tag.get_text(strip=True)
                    for sep in ["_", "-", "--", "|"]:
                        raw = raw.split(sep)[0].strip()
                    title = raw

            if not title or len(title) < 4:
                return None

            # 2. 发布时间提取
            pub_time = ""
            for sel in [".time", ".date", ".info", ".source", "p.sou", "td.font02", "[class*='time']"]:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', el.get_text())
                    if m:
                        pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                        break

            # 3. 来源提取
            source = media_info["name"]
            for sel in [".source", "[class*='source']", ".author", ".origin"]:
                el = soup.select_one(sel)
                if el:
                    s_txt = el.get_text(strip=True)
                    s_txt = re.sub(r'^(来源|稿源|出处|作者)[:：\s]*', '', s_txt).strip()
                    if s_txt and len(s_txt) < 30:
                        source = s_txt
                        break

            # 4. 正文提取（剥离视频播放器等噪音）
            content_div = None
            for sel in cls.CONTENT_SELECTORS:
                el = soup.select_one(sel)
                if el and len(el.get_text(strip=True)) > 60:
                    content_div = el
                    break

            if not content_div:
                # 启发式文本块评分
                best_score = 0
                for div in soup.find_all(["div", "td"]):
                    p_num = len(div.find_all("p"))
                    t_len = len(div.get_text(strip=True))
                    score = p_num * 80 + t_len
                    if score > best_score and (p_num >= 2 or t_len > 150):
                        best_score = score
                        content_div = div

            content = ""
            images = []

            if content_div:
                for bad in content_div.find_all(
                    ["script", "style", "video", "audio", "iframe", "embed", "object", "footer", "button", "nav"]
                ):
                    bad.decompose()

                p_list = []
                for p in content_div.find_all(["p", "div"]):
                    if p.find(["p"]):
                        continue
                    pt = p.get_text(strip=True)
                    if len(pt) > 4:
                        if any(b in pt for b in ["责任编辑", "版权所有", "扫码下载", "点击播放", "关注公众号"]):
                            continue
                        p_list.append(pt)

                content = "\n".join(p_list)
                if len(content) < 60:
                    content = content_div.get_text(separator="\n", strip=True)

                for img in content_div.find_all("img", src=True):
                    s = img["src"].strip()
                    if s and not s.startswith("data:") and not s.endswith(".gif"):
                        images.append(urljoin(url, s))

            if len(content) < 50 and not images:
                return None

            return {
                "media_name": media_info["name"],
                "media_category": "地方新闻单位",
                "sub_category": media_info.get("sub_category", "地方报业与广电"),
                "channel": "要闻综合",
                "url": url,
                "title": title,
                "publish_time": pub_time,
                "source": source,
                "content": content,
                "images": images,
                "crawl_time": datetime.now().isoformat(),
            }

        except Exception as e:
            log.debug(f"解析地方单位文章异常 [{media_info['name']}] {url}: {e}")
            return None


class LocalUnitsCrawler:
    def __init__(self):
        self.session = requests.Session()
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

    def fetch_soup(self, url):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": url}
                r = self.session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
                if r.status_code != 200:
                    return None
                
                # 自适应编码探测
                text = ""
                meta_enc = re.search(rb'charset=["\']?([\w-]+)', r.content[:2048])
                cands = []
                if meta_enc:
                    cands.append(meta_enc.group(1).decode("ascii", errors="ignore").lower())
                cands.extend(["utf-8", "gb18030", "gbk"])

                for enc in cands:
                    try:
                        text = r.content.decode(enc)
                        if "\ufffd" not in text[:400]:
                            break
                    except:
                        pass
                if not text:
                    text = r.content.decode("utf-8", errors="replace")

                return BeautifulSoup(text, "lxml")
            except:
                time.sleep(1.0 * attempt)
        return None

    def save_record(self, article):
        """严格分类落盘: data/地方新闻单位/<子分类>/<媒体名称>/要闻综合.jsonl"""
        sub_cat = article.get("sub_category", "综合单位")
        media_name = article.get("media_name", "未知媒体")

        target_dir = os.path.join(DATA_DIR, "地方新闻单位", sub_cat, media_name)
        os.makedirs(target_dir, exist_ok=True)

        out_file = os.path.join(target_dir, "要闻综合.jsonl")
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")

    def crawl_unit(self, unit_info, max_articles=30):
        name = unit_info["name"]
        url = unit_info.get("url") or unit_info.get("raw_url") or ""
        sub_cat = unit_info.get("sub_category", "地方新闻单位")

        if not url or not url.startswith("http"):
            return 0

        log.info(f"\n[{sub_cat}] 开始抓取: 【{name}】 -> {url}")
        soup = self.fetch_soup(url)
        if not soup:
            log.warning(f"   无法访问官网入口: {url}")
            return 0

        links = LocalUnitArticleParser.extract_links(soup, url)
        log.info(f"   发现候选文章: {len(links)} 篇")

        saved = 0
        for link in links:
            if max_articles > 0 and saved >= max_articles:
                break
            if link in self.visited:
                continue

            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            art_soup = self.fetch_soup(link)
            self.visited.add(link)

            if not art_soup:
                continue

            art = LocalUnitArticleParser.parse(art_soup, link, unit_info)
            if art:
                self.save_record(art)
                saved += 1
                log.info(f"   [{saved:>2}] ✓ {art['title'][:44]}")

        self.save_visited()
        log.info(f"⭐ 媒体【{name}】抓取结束，共入库: {saved} 篇")
        return saved


def main():
    parser = argparse.ArgumentParser(description="地方新闻单位专属高效爬虫系统 (覆盖 573 家报社、电视台与融媒)")
    parser.add_argument("--site", type=str, default=None, help="指定媒体名称（如：北京日报、解放日报、广州日报、天津广播电视台等），或 'all'")
    parser.add_argument("--sub-cat", type=str, default=None, choices=["报业传媒", "广播电视", "融媒体中心", "all"], help="按地方新闻单位子分类批量爬取")
    parser.add_argument("--max-per-site", type=int, default=30, help="每个媒体抓取篇数上限（0 = 不限）")
    parser.add_argument("--list-sites", action="store_true", help="查看所有 573 家地方新闻单位列表与子分类")

    args = parser.parse_args()
    units = load_local_units()

    if args.list_sites:
        print("=" * 65)
        print(f"  地方新闻单位全量清单 (共收录 {len(units)} 家)")
        print("=" * 65)
        by_sub = {}
        for u in units:
            sc = u.get("sub_category", "其他")
            by_sub.setdefault(sc, []).append(u)
        for sc, items in by_sub.items():
            print(f"\n【{sc}】 (共 {len(items)} 家):")
            for i, it in enumerate(items[:20], 1):
                print(f"  {i:2d}. {it['name']:<14s} ({it.get('url')})")
            if len(items) > 20:
                print(f"  ... 以及其他 {len(items)-20} 家")
        return

    crawler = LocalUnitsCrawler()

    # 1. 单个媒体
    if args.site and args.site != "all":
        matched = [u for u in units if u["name"] == args.site]
        if matched:
            crawler.crawl_unit(matched[0], max_articles=args.max_per_site)
        else:
            print(f"未找到地方新闻单位: {args.site}")
        return

    # 2. 按子类批量
    target_units = units
    if args.sub_cat and args.sub_cat != "all":
        target_units = [u for u in units if u.get("sub_category") == args.sub_cat]

    log.info(f"启动地方新闻单位批量爬虫，目标总计: {len(target_units)} 家")
    for u in target_units:
        crawler.crawl_unit(u, max_articles=args.max_per_site)


if __name__ == "__main__":
    main()
