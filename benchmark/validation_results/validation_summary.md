# 全网 1400+ 家媒体网站可访问性与爬虫实际抓取有效性全面验证报告

> 生成时间：2026-09-14 09:17:54

## 一、总体健康度与抓取成果概览

- **媒体收录总数**：`1432` 家
- **可正常访问并成功爬取完整文章**：**`1217`** 家（**成功率 84.99%**）
- **网站可连通总数**：**`1291`** 家（**可达率 90.15%**）
- **不可连通/严重异常**：`141` 家

## 二、各分类媒体验证情况一览

| 媒体分类 | 媒体总数 | 爬取成功 | 成功率 | 网站可达数 | 可达率 | 异常不可达 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 地方新闻单位 | 573 | 497 | 86.7% | 526 | 91.8% | 47 |
| 地方新闻网站 | 511 | 472 | 92.4% | 486 | 95.1% | 25 |
| 部委群团报刊网站 | 117 | 93 | 79.5% | 98 | 83.8% | 19 |
| 中央政务发布平台 | 85 | 64 | 75.3% | 71 | 83.5% | 14 |
| 中央新闻单位报刊网站 | 67 | 34 | 50.7% | 49 | 73.1% | 18 |
| 中央新闻网站和重点理论网站 | 31 | 27 | 87.1% | 30 | 96.8% | 1 |
| 省级政务发布平台 | 31 | 15 | 48.4% | 16 | 51.6% | 15 |
| 其他单位报刊网站 | 17 | 15 | 88.2% | 15 | 88.2% | 2 |


## 三、站点状态详细分布

| 状态分类 | 站点数量 | 占比 | 状态说明 |
| :--- | :---: | :---: | :--- |
| `SUCCESS` | 1217 | 84.99% | 可正常访问，且成功抓取到 1~2 篇包含标题与正文的新闻 |
| `ACCESSIBLE_NO_LINKS` | 62 | 4.33% | 网站首页正常打开，但首页未发现静态规范新闻文章超链接（如纯视频/JS单页应用） |
| `DNS_FAILURE` | 45 | 3.14% | DNS 域名解析失败（域名已失效或停用） |
| `READ_TIMEOUT` | 35 | 2.44% | 读取超时 |
| `HTTP_403` | 28 | 1.96% | HTTP 403 Forbidden（触发 WAF 强反爬策略或白名单限制） |
| `PARSED_NO_TEXT` | 12 | 0.84% | 网站可访问且发现详情链接，但内容为纯图片/PDF数字报或未匹配正文选择器 |
| `SSL_ERROR` | 7 | 0.49% | SSL 握手协议错误或算法不兼容 |
| `HTTP_412` | 6 | 0.42% | 其他网络或解析错误 |
| `HTTP_405` | 5 | 0.35% | 其他网络或解析错误 |
| `HTTP_404` | 3 | 0.21% | HTTP 404 Not Found（主页路径丢失） |
| `HTTP_521` | 3 | 0.21% | 其他网络或解析错误 |
| `CONNECTION_ERROR` | 3 | 0.21% | 其他网络或解析错误 |
| `CONNECTION_REFUSED` | 2 | 0.14% | 连接被拒绝（服务器端口关闭） |
| `REQUEST_ERROR` | 1 | 0.07% | 其他网络或解析错误 |
| `HTTP_502` | 1 | 0.07% | 其他网络或解析错误 |
| `CONNECT_TIMEOUT` | 1 | 0.07% | 连接超时（服务器响应极慢或阻断连接） |
| `HTTP_567` | 1 | 0.07% | 其他网络或解析错误 |


## 四、未成功爬取站点的典型原因与排查清单

共有 `215` 家站点未能直接通过通用静态爬虫提取文章，以下列出典型问题分类：

### 状态: `ACCESSIBLE_NO_LINKS` (共 62 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 求是网 | 中央新闻网站和重点理论网站 | [http://www.qiushi.com.cn/](http://www.qiushi.com.cn/) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 学习强国 | 中央新闻网站和重点理论网站 | [https://www.xuexi.cn/](https://www.xuexi.cn/) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 人民日报海外版 | 中央新闻单位报刊网站 | [http://paper.people.com.cn/rmrbhwb](http://paper.people.com.cn/rmrbhwb) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 参考消息 | 中央新闻单位报刊网站 | [http://www.cankaoxiaoxi.com/](http://www.cankaoxiaoxi.com/) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 参考消息网 | 中央新闻单位报刊网站 | [http://www.cankaoxiaoxi.com/](http://www.cankaoxiaoxi.com/) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国汽车报 | 中央新闻单位报刊网站 | [http://www.chinagathering.com](http://www.chinagathering.com) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国汽车报网 | 中央新闻单位报刊网站 | [http://www.chinagathering.com](http://www.chinagathering.com) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 新华每日电讯 | 中央新闻单位报刊网站 | [http://mrdx.xinhuanet.com](http://mrdx.xinhuanet.com) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国企业家网 | 中央新闻单位报刊网站 | [http://www.iceo.com.cn](http://www.iceo.com.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 《中国企业家》杂志 | 中央新闻单位报刊网站 | [http://www.iceo.com.cn](http://www.iceo.com.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 《教育家》杂志 | 中央新闻单位报刊网站 | [http://www.gmdaily.cn](http://www.gmdaily.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国画报网站 | 中央新闻单位报刊网站 | [http://www.china-pictorial.com.cn](http://www.china-pictorial.com.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国环境报 | 部委群团报刊网站 | [https://www.cenews.com.cn](https://www.cenews.com.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国环境网站 | 部委群团报刊网站 | [https://www.cenews.com.cn](https://www.cenews.com.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| 中国银行保险报网 | 部委群团报刊网站 | [http://www.cbimc.cn](http://www.cbimc.cn) | 首页可访问，但未能提取到符合特征的新闻详情页超链接（可能是动态渲染/SPA或纯视频站） |
| ... *其余 47 家详见完整 JSON 日志* | | | |


### 状态: `DNS_FAILURE` (共 45 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 理论网 | 中央新闻网站和重点理论网站 | [http://www.lilun.cn/](http://www.lilun.cn/) | DNS_FAILURE |
| 环球人物 | 中央新闻单位报刊网站 | [http://www.huanqiurenwu.com/](http://www.huanqiurenwu.com/) | DNS_FAILURE |
| 环球人物网 | 中央新闻单位报刊网站 | [http://www.huanqiurenwu.com/](http://www.huanqiurenwu.com/) | DNS_FAILURE |
| 人民周刊 | 中央新闻单位报刊网站 | [http://www.peopleweek.cn](http://www.peopleweek.cn) | DNS_FAILURE |
| 人民周刊网 | 中央新闻单位报刊网站 | [http://www.peopleweek.cn](http://www.peopleweek.cn) | DNS_FAILURE |
| 人民财经网 | 中央新闻单位报刊网站 | [http://www.peopleweek.cn](http://www.peopleweek.cn) | DNS_FAILURE |
| 人民研学网 | 中央新闻单位报刊网站 | [http://www.peopleweek.cn](http://www.peopleweek.cn) | DNS_FAILURE |
| 《新安全》杂志 | 中央新闻单位报刊网站 | [http://www.xinanquan.cn](http://www.xinanquan.cn) | DNS_FAILURE |
| 《平安校园》杂志 | 中央新闻单位报刊网站 | [http://www.paxw.cn](http://www.paxw.cn) | DNS_FAILURE |
| 《留学》杂志 | 中央新闻单位报刊网站 | [http://www.liuxue-magazine.com](http://www.liuxue-magazine.com) | DNS_FAILURE |
| 中国县域经济报 | 中央新闻单位报刊网站 | [http://www.zgxyjj.org.cn](http://www.zgxyjj.org.cn) | DNS_FAILURE |
| 县域经济网 | 中央新闻单位报刊网站 | [http://www.zgxyjj.org.cn](http://www.zgxyjj.org.cn) | DNS_FAILURE |
| 《当代世界》杂志 | 部委群团报刊网站 | [http://www.ddsj.org.cn](http://www.ddsj.org.cn) | DNS_FAILURE |
| 《乡镇论坛》杂志 | 部委群团报刊网站 | [http://www.mca.gov.cn](http://www.mca.gov.cn) | DNS_FAILURE |
| 《社区》杂志 | 部委群团报刊网站 | [http://www.mca.gov.cn](http://www.mca.gov.cn) | DNS_FAILURE |
| ... *其余 30 家详见完整 JSON 日志* | | | |


### 状态: `READ_TIMEOUT` (共 35 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中国城市报 | 中央新闻单位报刊网站 | [http://www.zgcsb.com](http://www.zgcsb.com) | READ_TIMEOUT |
| 中国城市网 | 中央新闻单位报刊网站 | [http://www.zgcsb.com](http://www.zgcsb.com) | READ_TIMEOUT |
| 中国妇女网 | 中央新闻单位报刊网站 | [http://www.women.org.cn/](http://www.women.org.cn/) | READ_TIMEOUT |
| 中国经济导报 | 部委群团报刊网站 | [http://www.chinadevelopment.com.cn](http://www.chinadevelopment.com.cn) | READ_TIMEOUT |
| 中国发展网 | 部委群团报刊网站 | [http://www.chinadevelopment.com.cn](http://www.chinadevelopment.com.cn) | READ_TIMEOUT |
| 中国劳动保障报 | 部委群团报刊网站 | [http://www.clssn.com](http://www.clssn.com) | READ_TIMEOUT |
| 中国交通报 | 部委群团报刊网站 | [http://www.zgjtb.com](http://www.zgjtb.com) | READ_TIMEOUT |
| 中国交通新闻网 | 部委群团报刊网站 | [http://www.zgjtb.com](http://www.zgjtb.com) | READ_TIMEOUT |
| 中国税务报 | 部委群团报刊网站 | [http://www.ctaxnews.net.cn](http://www.ctaxnews.net.cn) | READ_TIMEOUT |
| 中国绿色时报 | 部委群团报刊网站 | [http://www.greentimes.com](http://www.greentimes.com) | READ_TIMEOUT |
| 全国妇联网站 | 中央政务发布平台 | [http://www.women.org.cn](http://www.women.org.cn) | READ_TIMEOUT |
| 东北网 | 地方新闻网站 | [https://www.dbw.cn/](https://www.dbw.cn/) | READ_TIMEOUT |
| 上游新闻网 | 地方新闻网站 | [https://www.cqcb.com/](https://www.cqcb.com/) | READ_TIMEOUT |
| 四川新闻网 | 地方新闻网站 | [http://www.newssc.org/](http://www.newssc.org/) | READ_TIMEOUT |
| 华商网 | 地方新闻网站 | [http://www.hsw.cn/](http://www.hsw.cn/) | READ_TIMEOUT |
| ... *其余 20 家详见完整 JSON 日志* | | | |


### 状态: `HTTP_403` (共 28 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中国农网 | 中央新闻单位报刊网站 | [https://www.farmer.com.cn](https://www.farmer.com.cn) | HTTP_403 |
| 人民公安报 | 部委群团报刊网站 | [https://www.cpd.com.cn](https://www.cpd.com.cn) | HTTP_403 |
| 中央党校（国家行政学院）网站 | 中央政务发布平台 | [http://www.ccps.gov.cn](http://www.ccps.gov.cn) | HTTP_403 |
| 退役军人事务部网站 | 中央政务发布平台 | [http://www.mva.gov.cn](http://www.mva.gov.cn) | HTTP_403 |
| 中国文艺网 | 中央政务发布平台 | [http://www.cflac.org.cn](http://www.cflac.org.cn) | HTTP_403 |
| 最高人民检察院网站 | 中央政务发布平台 | [https://www.spp.gov.cn](https://www.spp.gov.cn) | HTTP_403 |
| 北青网 | 地方新闻网站 | [https://www.ynet.com/](https://www.ynet.com/) | HTTP_403 |
| 东方网 | 地方新闻网站 | [https://www.eastday.com/](https://www.eastday.com/) | HTTP_403 |
| 澎湃新闻 | 地方新闻网站 | [https://www.thepaper.cn/](https://www.thepaper.cn/) | HTTP_403 |
| 大河网 | 地方新闻网站 | [https://www.dahe.cn/](https://www.dahe.cn/) | HTTP_403 |
| 云南网 | 地方新闻网站 | [http://www.yunnan.cn/](http://www.yunnan.cn/) | HTTP_403 |
| 北京青年报 | 地方新闻单位 | [https://www.ynet.com](https://www.ynet.com) | HTTP_403 |
| 苏州日报 | 地方新闻单位 | [http://www.subaonet.com](http://www.subaonet.com) | HTTP_403 |
| 无锡日报 | 地方新闻单位 | [http://www.wxrb.com](http://www.wxrb.com) | HTTP_403 |
| 合肥日报 | 地方新闻单位 | [http://www.hefei.gov.cn](http://www.hefei.gov.cn) | HTTP_403 |
| ... *其余 13 家详见完整 JSON 日志* | | | |


### 状态: `PARSED_NO_TEXT` (共 12 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 民生周刊 | 中央新闻单位报刊网站 | [http://www.msweekly.com](http://www.msweekly.com) | 成功提取并尝试了 4 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 民生网 | 中央新闻单位报刊网站 | [http://www.msweekly.com](http://www.msweekly.com) | 成功提取并尝试了 4 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 中国西藏网 | 中央新闻网站和重点理论网站 | [http://www.vtibet.cn/](http://www.vtibet.cn/) | 成功提取并尝试了 10 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 中国自然资源报 | 部委群团报刊网站 | [http://www.iziran.net](http://www.iziran.net) | 成功提取并尝试了 3 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 中国证券网 | 中央新闻单位报刊网站 | [https://www.cnstock.com/](https://www.cnstock.com/) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 上海证券报 | 中央新闻单位报刊网站 | [https://www.cnstock.com/](https://www.cnstock.com/) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 上观新闻网 | 地方新闻网站 | [https://www.shobserver.com/](https://www.shobserver.com/) | 成功提取并尝试了 1 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 人民数字联播网 | 中央新闻单位报刊网站 | [http://www.rmsznet.com](http://www.rmsznet.com) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 映象网 | 地方新闻网站 | [http://www.hnr.cn/](http://www.hnr.cn/) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 解放日报 | 地方新闻单位 | [https://www.shobserver.com](https://www.shobserver.com) | 成功提取并尝试了 1 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 石家庄广播电视台 | 地方新闻单位 | [http://www.sjzntv.cn](http://www.sjzntv.cn) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |
| 云南省人民政府网站 | 省级政务发布平台 | [https://www.yn.gov.cn](https://www.yn.gov.cn) | 成功提取并尝试了 20 条候选链接，但正文提取规则未能提取出有效文章文本（可能是纯图报纸/PDF/视频页） |


### 状态: `SSL_ERROR` (共 7 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 大江网 | 地方新闻网站 | [https://www.jxnews.com.cn/](https://www.jxnews.com.cn/) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |
| 江西网络广播电视台 | 地方新闻网站 | [http://www.jxnews.com.cn](http://www.jxnews.com.cn) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |
| 中国江西网 | 地方新闻网站 | [http://www.jxnews.com.cn/](http://www.jxnews.com.cn/) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |
| 江西文明网 | 地方新闻网站 | [http://www.jxnews.com.cn](http://www.jxnews.com.cn) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |
| 天津广播电视台 | 地方新闻单位 | [https://www.tjtv.com.cn](https://www.tjtv.com.cn) | SSL_ERROR: HTTPSConnectionPool(host='www.tjtv.com.cn', port= |
| 江西晨报 | 地方新闻单位 | [http://www.jxnews.com.cn](http://www.jxnews.com.cn) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |
| 江西广播电视台 | 地方新闻单位 | [http://www.jxnews.com.cn](http://www.jxnews.com.cn) | SSL_ERROR: HTTPSConnectionPool(host='www.jxnews.com.cn', por |


### 状态: `HTTP_412` (共 6 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 海关总署网站 | 中央政务发布平台 | [http://www.customs.gov.cn](http://www.customs.gov.cn) | HTTP_412 |
| 国家药监局网站 | 中央政务发布平台 | [https://www.nmpa.gov.cn](https://www.nmpa.gov.cn) | HTTP_412 |
| 全国总工会网站 | 中央政务发布平台 | [https://www.acftu.org](https://www.acftu.org) | HTTP_412 |
| 宁夏新闻网 | 地方新闻网站 | [http://www.nxnews.net/](http://www.nxnews.net/) | HTTP_412 |
| 湖北省人民政府网站 | 省级政务发布平台 | [http://www.hubei.gov.cn](http://www.hubei.gov.cn) | HTTP_412 |
| 甘肃省人民政府网站 | 省级政务发布平台 | [https://www.gansu.gov.cn](https://www.gansu.gov.cn) | HTTP_412 |


### 状态: `HTTP_405` (共 5 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 东北新闻网 | 地方新闻网站 | [http://www.nen.com.cn/](http://www.nen.com.cn/) | HTTP_405 |
| 北京广播电视台 | 地方新闻单位 | [https://www.brtv.org.cn](https://www.brtv.org.cn) | HTTP_405 |
| 南京日报 | 地方新闻单位 | [http://www.njdaily.cn](http://www.njdaily.cn) | HTTP_405 |
| 四川广播电视台 | 地方新闻单位 | [https://www.sctv.com](https://www.sctv.com) | HTTP_405 |
| 西安日报 | 地方新闻单位 | [http://epaper.xiancn.com](http://epaper.xiancn.com) | HTTP_405 |


### 状态: `HTTP_404` (共 3 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中华读书报 | 中央新闻单位报刊网站 | [http://www.gmw.cn/01gmrb/zgdsb](http://www.gmw.cn/01gmrb/zgdsb) | HTTP_404 |
| 《红旗文稿》杂志 | 中央新闻单位报刊网站 | [http://www.qstheory.cn/hongqi/](http://www.qstheory.cn/hongqi/) | HTTP_404 |
| 成都商报 | 地方新闻单位 | [http://static.cdsb.com](http://static.cdsb.com) | HTTP_404 |


### 状态: `HTTP_521` (共 3 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中国经营网 | 部委群团报刊网站 | [http://www.cb.com.cn/](http://www.cb.com.cn/) | HTTP_521 |
| 国务院新闻办公室网站国家新闻出版署网站中
国全民阅读网 | 中央政务发布平台 | [http://www.scio.gov.cn](http://www.scio.gov.cn) | HTTP_521 |
| 公安部网站中国反邪教网 | 中央政务发布平台 | [https://www.mps.gov.cn](https://www.mps.gov.cn) | HTTP_521 |


### 状态: `CONNECTION_ERROR` (共 3 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 北方网 | 地方新闻网站 | [http://www.enorth.com.cn/](http://www.enorth.com.cn/) | CONNECTION_ERROR: ('Connection aborted.', RemoteDisconnected |
| 新余市广播电视台 | 地方新闻单位 | [http://www.xytv.cn](http://www.xytv.cn) | CONNECTION_ERROR: ('Connection aborted.', RemoteDisconnected |
| 上饶市广播电视台 | 地方新闻单位 | [http://www.srrw.cn](http://www.srrw.cn) | CONNECTION_ERROR: ('Connection aborted.', RemoteDisconnected |


### 状态: `CONNECTION_REFUSED` (共 2 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中国建设报 | 部委群团报刊网站 | [http://www.chinajsb.cn](http://www.chinajsb.cn) | CONNECTION_REFUSED |
| 中国建设新闻网 | 部委群团报刊网站 | [http://www.chinajsb.cn](http://www.chinajsb.cn) | CONNECTION_REFUSED |


### 状态: `REQUEST_ERROR` (共 1 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 中国金融信息网 | 中央新闻单位报刊网站 | [http://www.cnfin.com/](http://www.cnfin.com/) | REQUEST_ERROR: ('Connection broken: IncompleteRead(5893 byte |


### 状态: `HTTP_502` (共 1 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 国家卫生健康委网站 | 中央政务发布平台 | [http://www.nhc.gov.cn](http://www.nhc.gov.cn) | HTTP_502 |


### 状态: `CONNECT_TIMEOUT` (共 1 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 文汇报 | 地方新闻单位 | [http://dzb.whb.cn](http://dzb.whb.cn) | CONNECT_TIMEOUT |


### 状态: `HTTP_567` (共 1 家)
| 媒体名称 | 分类 | URL | 诊断详情 |
| :--- | :--- | :--- | :--- |
| 深圳特区报 | 地方新闻单位 | [https://sztqb.sznews.com](https://sztqb.sznews.com) | HTTP_567 |

