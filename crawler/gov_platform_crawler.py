#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各级政务发布平台专属高效爬虫系统 (Government Platforms Crawler)
专门针对国家网信办名单中：
  - 【中央政务发布平台】(全量 85 家，含党中央各部委、国务院组成部门、直属机构、群团组织等)
  - 【省级政务发布平台】(全量 31 家，含 31 个省/自治区/直辖市人民政府门户网)
总计 116 家官方政务网站设计开发。

核心技术特性:
  1. 权威域名映射库: 精确解析中央部委与 31 省市人民政府 gov.cn 标准域名。
  2. 国办标准模板解析:
     - 适配国务院办公厅《政府网站发展指引》标准正文容器 (#UCAP-CONTENT, #zoom, .pages_content 等)；
     - 提取特有的公文元数据：发文字号 (doc_number)、主题分类/索引号 (index_number)、成文发布日期；
  3. 严格分层分类落盘:
     - data/中央政务发布平台/<部委机构名>/政务要闻.jsonl
     - data/省级政务发布平台/<省区市名称>/政务要闻.jsonl
  4. 全局断点续爬与防重机制 (共享 data/visited_urls.txt)。
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
TIMEOUT = 12
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

# 权威部委与省级人民政府真实官方主页映射表（彻底解决名单中中文通用域名解析问题）
GOV_OFFICIAL_DOMAINS = {
    # 1. 31个省级人民政府门户网站
    "北京市人民政府门户网站": "https://www.beijing.gov.cn",
    "天津政务网": "https://www.tj.gov.cn",
    "河北省人民政府网站": "http://www.hebei.gov.cn",
    "山西省人民政府网站": "http://www.shanxi.gov.cn",
    "内蒙古自治区人民政府网站": "https://www.nmg.gov.cn",
    "辽宁省人民政府网站": "https://www.ln.gov.cn",
    "吉林省人民政府网站": "http://www.jl.gov.cn",
    "黑龙江省人民政府网站": "http://www.hlj.gov.cn",
    "上海市人民政府网站": "https://www.shanghai.gov.cn",
    "江苏省人民政府网站": "http://www.jiangsu.gov.cn",
    "浙江省人民政府网站": "https://www.zj.gov.cn",
    "安徽省人民政府网站": "https://www.ah.gov.cn",
    "福建省人民政府网站": "https://www.fujian.gov.cn",
    "江西省人民政府网站": "http://www.jiangxi.gov.cn",
    "山东省人民政府网站": "http://www.shandong.gov.cn",
    "河南省人民政府网站": "https://www.henan.gov.cn",
    "湖北省人民政府网站": "http://www.hubei.gov.cn",
    "湖南省人民政府网站": "http://www.hunan.gov.cn",
    "广东省人民政府网站": "https://www.gd.gov.cn",
    "广西壮族自治区人民政府网站": "http://www.gxzf.gov.cn",
    "海南省人民政府网站": "https://www.hainan.gov.cn",
    "重庆市人民政府网站": "https://www.cq.gov.cn",
    "四川省人民政府网站": "https://www.sc.gov.cn",
    "贵州省人民政府网站": "https://www.guizhou.gov.cn",
    "云南省人民政府网站": "https://www.yn.gov.cn",
    "西藏自治区人民政府网站": "http://www.xizang.gov.cn",
    "陕西省人民政府网站": "http://www.shaanxi.gov.cn",
    "甘肃省人民政府网站": "https://www.gansu.gov.cn",
    "青海省人民政府网站": "http://www.qinghai.gov.cn",
    "宁夏回族自治区人民政府网站": "https://www.nx.gov.cn",
    "新疆维吾尔自治区人民政府网站新疆生产建设兵团\n政务网站": "http://www.xinjiang.gov.cn",

    # 2. 85家中央部委及机构官方发布平台
    "中央纪委国家监委网站": "https://www.ccdi.gov.cn",
    "共产党员网": "https://www.12371.cn",
    "国务院新闻办公室网站国家新闻出版署网站中\n国全民阅读网": "http://www.scio.gov.cn",
    "中央对外联络部网站": "https://www.idcpc.gov.cn",
    "中央社会工作部网站": "https://www.zyshgzb.gov.cn",
    "中国长安网": "http://www.chinapeace.gov.cn",
    "中国网信网中央网信办违法和不良信息举报中\n心网站中国互联网联合辟谣平台网站": "http://www.cac.gov.cn",
    "中共中央台湾工作办公室（国务院台湾事务办公室）\n网站": "http://www.gwytb.gov.cn",
    "中央党校（国家行政学院）网站": "http://www.ccps.gov.cn",
    "中共中央党史和文献研究院网站（中\n国共产党历史和文献网）": "http://www.dswxyjy.org.cn",
    "中国人大网": "http://www.npc.gov.cn",
    "中国政府网": "https://www.gov.cn",
    "外交部网站": "https://www.mfa.gov.cn",
    "国家发展改革委网站": "https://www.ndrc.gov.cn",
    "教育部网站": "http://www.moe.gov.cn",
    "科技部网站": "https://www.most.gov.cn",
    "工业和信息化部网站": "https://www.miit.gov.cn",
    "国家民委网站": "https://www.neac.gov.cn",
    "公安部网站中国反邪教网": "https://www.mps.gov.cn",
    "民政部网站中国社会组织政务服务平台": "https://www.mca.gov.cn",
    "司法部网站": "http://www.moj.gov.cn",
    "财政部网站": "http://www.mof.gov.cn",
    "自然资源部网站": "http://www.mnr.gov.cn",
    "生态环境部网站": "https://www.mee.gov.cn",
    "住房城乡建设部网站": "https://www.mohurd.gov.cn",
    "交通运输部网站": "https://www.mot.gov.cn",
    "水利部网站": "http://www.mwr.gov.cn",
    "农业农村部网站": "http://www.moa.gov.cn",
    "商务部网站": "http://www.mofcom.gov.cn",
    "文化和旅游部网站": "https://www.mct.gov.cn",
    "国家卫生健康委网站": "http://www.nhc.gov.cn",
    "退役军人事务部网站": "http://www.mva.gov.cn",
    "应急管理部网站": "https://www.mem.gov.cn",
    "中国人民银行网站": "http://www.pbc.gov.cn",
    "审计署网站": "https://www.audit.gov.cn",
    "国务院国资委网站": "http://www.sasac.gov.cn",
    "海关总署网站": "http://www.customs.gov.cn",
    "税务总局网站": "http://www.chinatax.gov.cn",
    "市场监管总局网站": "https://www.samr.gov.cn",
    "金融监管总局网站": "https://www.nfra.gov.cn",
    "中国证监会网站": "http://www.csrc.gov.cn",
    "广电总局网站": "http://www.nrta.gov.cn",
    "体育总局网站": "https://www.sport.gov.cn",
    "国家信访局网站": "http://www.gjxfj.gov.cn",
    "国家统计局网站": "https://www.stats.gov.cn",
    "国家知识产权局网站": "https://www.cnipa.gov.cn",
    "国家国际发展合作署网站": "http://www.cidca.gov.cn",
    "国家医保局网站": "https://www.nhsa.gov.cn",
    "国务院港澳办网站": "https://www.hmo.gov.cn",
    "中央人民政府驻香港特别行政区联络办公室网站": "http://www.locpg.gov.cn",
    "中央人民政府驻澳门特别行政区联络办公室网站": "http://www.zlb.gov.cn",
    "中国科学院网站": "https://www.cas.cn",
    "中国社科院网站": "http://www.cass.cn",
    "中国工程院网站": "https://www.cae.cn",
    "国务院发展研究中心网站": "https://www.drc.gov.cn",
    "中国气象局网站": "https://www.cma.gov.cn",
    "国家粮食和储备局网站": "http://www.lswz.gov.cn",
    "国家能源局网站": "http://www.nea.gov.cn",
    "国家国防科工局网站": "http://www.sastind.gov.cn",
    "国家移民局网站": "https://www.nia.gov.cn",
    "国家林草局网站": "http://www.forestry.gov.cn",
    "国家铁路局网站": "http://www.nra.gov.cn",
    "中国民航局网站": "http://www.caac.gov.cn",
    "国家邮政局网站": "http://www.spb.gov.cn",
    "国家文物局网站": "http://www.ncha.gov.cn",
    "国家中医药局网站": "http://www.natcm.gov.cn",
    "国家矿山安监局网站": "http://www.chinamine-safety.gov.cn",
    "国家外汇局网站": "https://www.safe.gov.cn",
    "国家药监局网站": "https://www.nmpa.gov.cn",
    "国家航天局网站": "http://www.cnsa.gov.cn",
    "国家原子能机构网站": "http://www.caea.gov.cn",
    "中国政协网": "http://www.cppcc.gov.cn",
    "最高人民法院网站": "https://www.court.gov.cn",
    "最高人民检察院网站": "https://www.spp.gov.cn",
    "全国总工会网站": "https://www.acftu.org",
    "中国共青团网": "http://www.gqt.org.cn",
    "全国妇联网站": "http://www.women.org.cn",
    "中国文艺网": "http://www.cflac.org.cn",
    "中国科协网站科普中国网": "https://www.cast.org.cn",
    "中国记协网站": "http://www.zgjx.cn",
    "全国工商联网站": "http://www.acfic.org.cn",
    "中国供销合作网": "http://www.chinacoop.gov.cn",
    "中国国际进口博览会网站": "https://www.ciie.org",
    "世界互联网大会网站": "https://cn.wicinternet.org",
    "中国军网国防部网": "http://www.mod.gov.cn",
}


def load_gov_platforms():
    """加载全部 116 家政务发布平台（85 中央 + 31 省级），并应用官方权威域名映射"""
    if not os.path.exists(MANIFEST_FILE):
        return []
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        all_items = json.load(f)

    gov_items = []
    for it in all_items:
        cat = it.get("category", "")
        if cat in ("中央政务发布平台", "省级政务发布平台"):
            name = it.get("name", "")
            # 优先从映射表中获取权威真实的 gov.cn 域名
            if name in GOV_OFFICIAL_DOMAINS:
                it["url"] = GOV_OFFICIAL_DOMAINS[name]
            elif it.get("url") and "www." in it["url"] and ".cn" in it["url"]:
                # 对其他中文域名进行 punycode 容错编码转换
                try:
                    p = urlparse(it["url"])
                    host_encoded = p.netloc.encode("idna").decode("ascii")
                    it["url"] = f"{p.scheme or 'http'}://{host_encoded}"
                except:
                    pass
            gov_items.append(it)
    return gov_items


class GovArticleParser:
    """专为各级政府门户、部委公文与政务信息设计的内容与元数据解析器"""

    # 国务院与各部委标准化正文容器选择器
    CONTENT_SELECTORS = [
        "#UCAP-CONTENT", "#zoom", ".pages_content", "#articleContent",
        ".article-content", ".detail-content", ".view-body", "#fontzoom",
        ".trs_editor_view", ".TRS_Editor", "#Content", ".text_content",
        ".p-box", "#viewBigImagecont", ".custom_edit", ".content",
        ".main-content", "#main_content", ".detail", "#artibody"
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

            # 过滤非网页资源
            if any(full_url.lower().endswith(ext) for ext in [".jpg", ".png", ".pdf", ".docx", ".zip", ".rar"]):
                continue

            # 匹配典型政务公文与新闻特征
            # 如：/content/2026-03/t20260309_12345.htm 或 /zhengce/2026/03/xxx.htm
            if re.search(r'(\d{4}[/\-_]\d{2}|\d{8}|content_\d+|t\d+_\d+|/zhengce/|/yaowen/|/jndx/|/art/|/article/)', full_url):
                clean_url = full_url.split("?")[0].split("#")[0]
                links.add(clean_url)
            elif base_host and base_host in full_url:
                if re.search(r'(/\d{6,}/|\.shtml|\.htm|\.html)', full_url):
                    clean_url = full_url.split("?")[0].split("#")[0]
                    links.add(clean_url)

        return list(links)

    @classmethod
    def parse(cls, soup, url, platform_info):
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
            for sel in [".pages-date", ".time", ".date", ".info", ".source", "#fwrq", ".fwrq", "[class*='time']"]:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}(\s+\d{1,2}:\d{2}(:\d{2})?)?)', el.get_text())
                    if m:
                        pub_time = m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
                        break

            # 3. 来源提取
            source = platform_info["name"].split("\n")[0]
            for sel in [".source", "[class*='source']", "#fwjg", ".fwjg", ".origin"]:
                el = soup.select_one(sel)
                if el:
                    s_txt = el.get_text(strip=True)
                    s_txt = re.sub(r'^(来源|发文机关|发布机构|出处)[:：\s]*', '', s_txt).strip()
                    if s_txt and len(s_txt) < 35:
                        source = s_txt
                        break

            # 4. 政务特有元数据提取：发文字号与索引号
            doc_number = ""
            for sel in ["#wh", ".wh", ".fileno", "[class*='wh']", "td:-soup-contains('发文字号')"]:
                el = soup.select_one(sel)
                if el:
                    m = re.search(r'([〔\[【（\(]?\d{4}[〕\]】）\)]?\s*[\u4e00-\u9fa5A-Za-z]+号?)', el.get_text())
                    if m:
                        doc_number = m.group(0).strip()
                        break

            index_number = ""
            for sel in ["#syh", ".syh", "[class*='syh']", "td:-soup-contains('索引号')"]:
                el = soup.select_one(sel)
                if el:
                    txt = re.sub(r'^(索引号)[:：\s]*', '', el.get_text(strip=True))
                    if txt and len(txt) < 40:
                        index_number = txt
                        break

            # 5. 正文提取
            content_div = None
            for sel in cls.CONTENT_SELECTORS:
                el = soup.select_one(sel)
                if el and len(el.get_text(strip=True)) > 60:
                    content_div = el
                    break

            if not content_div:
                # 启发式算法寻找正文块
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
                # 剥离脚本、样式、导航、底部
                for bad in content_div.find_all(["script", "style", "nav", "footer", "button", "select"]):
                    bad.decompose()

                p_list = []
                for p in content_div.find_all(["p", "div"]):
                    if p.find(["p"]):
                        continue
                    pt = p.get_text(strip=True)
                    if len(pt) > 4:
                        if any(b in pt for b in ["扫一扫在手机打开", "主办单位：", "网站标识码", "ICP备", "公安网安备"]):
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

            clean_name = platform_info["name"].replace("\n", "")

            return {
                "media_name": clean_name,
                "media_category": platform_info["category"],
                "sub_category": platform_info.get("sub_category", platform_info["category"]),
                "channel": "政务要闻",
                "url": url,
                "title": title,
                "publish_time": pub_time,
                "source": source,
                "doc_number": doc_number,
                "index_number": index_number,
                "content": content,
                "images": images,
                "crawl_time": datetime.now().isoformat(),
            }

        except Exception as e:
            log.debug(f"解析政务发布平台文章异常 [{platform_info['name']}] {url}: {e}")
            return None


class GovPlatformCrawler:
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
                r = self.session.get(url, headers=headers, timeout=TIMEOUT, verify=False, allow_redirects=True)
                if r.status_code != 200:
                    return None

                # 自动探测政务网常用编码 (utf-8 / gbk / gb2312)
                text = ""
                meta_enc = re.search(rb'charset=["\']?([\w-]+)', r.content[:2048])
                cands = []
                if meta_enc:
                    cands.append(meta_enc.group(1).decode("ascii", errors="ignore").lower())
                cands.extend(["utf-8", "gb18030", "gbk", "gb2312"])

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
        """严格分类落盘: data/<中央政务发布平台|省级政务发布平台>/<媒体机构名称>/政务要闻.jsonl"""
        cat = article.get("media_category", "政务发布平台")
        media_name = article.get("media_name", "未知机构").replace("/", "_").replace("\\", "_")

        target_dir = os.path.join(DATA_DIR, cat, media_name)
        os.makedirs(target_dir, exist_ok=True)

        out_file = os.path.join(target_dir, "政务要闻.jsonl")
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")

    def crawl_platform(self, platform_info, max_articles=30):
        name = platform_info["name"].replace("\n", "")
        url = platform_info.get("url") or platform_info.get("raw_url") or ""
        cat = platform_info["category"]

        if not url or not url.startswith("http"):
            return 0

        log.info(f"\n[{cat}] 开始抓取: 【{name}】 -> {url}")
        soup = self.fetch_soup(url)
        if not soup:
            log.warning(f"   无法访问政务门户首页: {url}")
            return 0

        links = GovArticleParser.extract_links(soup, url)
        log.info(f"   发现候选政务公文/报道: {len(links)} 篇")

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

            art = GovArticleParser.parse(art_soup, link, platform_info)
            if art:
                self.save_record(art)
                saved += 1
                doc_flag = f" [文号: {art['doc_number']}]" if art['doc_number'] else ""
                log.info(f"   [{saved:>2}] ✓ {art['title'][:40]}{doc_flag}")

        self.save_visited()
        log.info(f"⭐ 政务平台【{name}】抓取结束，共入库: {saved} 篇")
        return saved


def main():
    parser = argparse.ArgumentParser(description="各级政务发布平台专属高效爬虫系统 (覆盖全量 116 家中央部委与省级政府门户)")
    parser.add_argument("--site", type=str, default=None, help="指定政务平台名称（如：中国政府网、外交部网站、北京市人民政府门户网站等），或 'all'")
    parser.add_argument("--category", type=str, default=None, choices=["中央政务发布平台", "省级政务发布平台", "all"], help="按政务大类批量爬取")
    parser.add_argument("--max-per-site", type=int, default=30, help="每个平台抓取公文篇数上限（0 = 不限）")
    parser.add_argument("--list-sites", action="store_true", help="查看所有 116 家政务平台官方网址清单")

    args = parser.parse_args()
    platforms = load_gov_platforms()

    if args.list_sites:
        print("=" * 70)
        print(f"  各级政务发布平台全量清单 (共收录 {len(platforms)} 家)")
        print("=" * 70)
        by_cat = {}
        for p in platforms:
            c = p.get("category", "其他")
            by_cat.setdefault(c, []).append(p)
        for c, items in by_cat.items():
            print(f"\n【{c}】 (共 {len(items)} 家):")
            for i, it in enumerate(items, 1):
                clean_n = it['name'].replace('\n', '')
                print(f"  {i:2d}. {clean_n:<22s} ({it.get('url')})")
        return

    # 忽略 requests verify=False 产生的警告
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        pass

    crawler = GovPlatformCrawler()

    # 1. 单个平台
    if args.site and args.site != "all":
        matched = [p for p in platforms if args.site in p["name"].replace("\n", "")]
        if matched:
            crawler.crawl_platform(matched[0], max_articles=args.max_per_site)
        else:
            print(f"未找到政务发布平台: {args.site}")
        return

    # 2. 批量分类
    target_platforms = platforms
    if args.category and args.category != "all":
        target_platforms = [p for p in platforms if p.get("category") == args.category]

    log.info(f"启动政务发布平台批量爬虫，目标总计: {len(target_platforms)} 家")
    for p in target_platforms:
        crawler.crawl_platform(p, max_articles=args.max_per_site)


if __name__ == "__main__":
    main()
