#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权威真实域名与融合平台映射中心 (Domain & Platform Mapper)

核心职责：
彻底解决全量 1400+ 媒体名单中 1200 多家中文机械拼接伪域名的根本问题。
集中维护所有：
1. 85家中央政务发布平台 + 31家省级政务发布平台官方域名 (GOV_OFFICIAL_DOMAINS)
2. 39家地方重点大报与省级广电台网权威域名 (LOCAL_OFFICIAL_DOMAINS)
3. 百余家部委群团报刊真实官网 (MINISTRY_PAPERS_DOMAINS)
4. 各地市广播电视台与报业规范官方主页 (LOCAL_MEDIA_SPECIFIC_DOMAINS)
5. 县级融媒体中心与政务融媒挂靠发布专栏 (COUNTY_RONGMEI_GOV_DOMAINS)
"""

import re
from urllib.parse import urlparse

# ─── 1. 权威部委与省级人民政府官方域名 (116家) ─────────────────────────────────
GOV_OFFICIAL_DOMAINS = {
    # 31个省级人民政府门户网站
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
    "新疆维吾尔自治区人民政府网站": "http://www.xinjiang.gov.cn",

    # 85家中央部委及机构官方发布平台
    "中央纪委国家监委网站": "https://www.ccdi.gov.cn",
    "共产党员网": "https://www.12371.cn",
    "国务院新闻办公室网站国家新闻出版署网站中\n国全民阅读网": "http://www.scio.gov.cn",
    "国务院新闻办公室网站": "http://www.scio.gov.cn",
    "中央对外联络部网站": "https://www.idcpc.gov.cn",
    "中央社会工作部网站": "https://www.zyshgzb.gov.cn",
    "中国长安网": "http://www.chinapeace.gov.cn",
    "中国网信网中央网信办违法和不良信息举报中\n心网站中国互联网联合辟谣平台网站": "http://www.cac.gov.cn",
    "中国网信网": "http://www.cac.gov.cn",
    "中共中央台湾工作办公室（国务院台湾事务办公室）\n网站": "http://www.gwytb.gov.cn",
    "国台办网站": "http://www.gwytb.gov.cn",
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
    "公安部网站": "https://www.mps.gov.cn",
    "民政部网站中国社会组织政务服务平台": "https://www.mca.gov.cn",
    "民政部网站": "https://www.mca.gov.cn",
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

# ─── 2. 主流地方报业与省级广电台网权威域名 (39家) ──────────────────────────────
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

# ─── 3. 部委群团报刊网站权威真实主页映射 ──────────────────────────────────────────
MINISTRY_PAPERS_DOMAINS = {
    # 纪检/党建/理论类
    "《中国纪检监察》杂志": "https://www.ccdi.gov.cn",
    "《秘书工作》杂志": "https://www.12371.cn",
    "《党建》杂志": "http://www.dangjian.cn",
    "《当代世界》杂志": "http://www.ddsj.org.cn",
    "《旗帜》杂志": "http://www.qizhiwang.org.cn",
    "《紫光阁》杂志": "http://www.zgg.org.cn",
    "《求是》": "http://www.qiushi.com.cn",
    "《红旗文稿》": "http://www.qstheory.cn/hongqi/",
    "《党建研究》杂志": "https://www.12371.cn",
    "《党建交流》": "http://www.dangjian.cn",
    "《中国网信》杂志": "http://www.cac.gov.cn",

    # 政法/公安/司法/法治类
    "人民法院报": "https://www.chinacourt.org",
    "中国法院网": "https://www.chinacourt.org",
    "检察日报": "https://www.jcrb.com",
    "正义网": "https://www.jcrb.com",
    "人民公安报": "https://www.cpd.com.cn",
    "中国警察网": "https://www.cpd.com.cn",
    "法治日报": "http://www.legaldaily.com.cn",
    "法治网": "http://www.legaldaily.com.cn",
    "人民防空报": "http://www.rf.gov.cn",
    "中国禁毒报": "http://www.nncc626.com",

    # 发改/财经/税务/市场监管类
    "中国经济导报": "http://www.chinadevelopment.com.cn",
    "中国发展网": "http://www.chinadevelopment.com.cn",
    "中国改革报": "http://www.cfgw.net.cn",
    "改革网": "http://www.cfgw.net.cn",
    "中宏网": "https://www.zhonghongwang.com",
    "中国税务报": "http://www.ctaxnews.net.cn",
    "中国市场监管报": "http://www.cmrn.com.cn",
    "中国银行保险报": "http://www.cbimc.cn",
    "中国金融传媒网": "http://www.cbimc.cn",
    "中国知识产权报": "http://www.iprchn.com",
    "IPRdaily": "http://www.iprdaily.cn",
    "中国物价": "http://www.chinadevelopment.com.cn",

    # 科技/教育/人才/人社类
    "中国教育报": "http://www.jyb.cn",
    "中国教育新闻网": "http://www.jyb.cn",
    "中国科技报": "http://www.stdaily.com",
    "科技日报": "http://www.stdaily.com",
    "中国高新技术产业导报": "http://www.chinahightech.com",
    "中国科学报": "https://news.sciencenet.cn",
    "科学网": "https://news.sciencenet.cn",
    "中国劳动保障报": "http://www.clssn.com",
    "中国人才": "http://www.clssn.com",
    "中国社会保障": "http://www.clssn.com",

    # 农业/水利/环境/自然资源类
    "农民日报": "https://www.farmer.com.cn",
    "中国农网": "https://www.farmer.com.cn",
    "中国水利报": "http://www.chinawater.com.cn",
    "中国水利网": "http://www.chinawater.com.cn",
    "中国环境报": "https://www.cenews.com.cn",
    "中国环境网": "https://www.cenews.com.cn",
    "中国自然资源报": "http://www.iziran.net",
    "中国矿业报": "http://www.miningchina.org",
    "中国海洋报": "http://www.iziran.net",
    "中国绿色时报": "http://www.greentimes.com",
    "中国林业网": "http://www.forestry.gov.cn",

    # 工交/应急/能源/住建类
    "中国交通报": "http://www.zgjtb.com",
    "中国交通新闻网": "http://www.zgjtb.com",
    "中国应急管理报": "https://www.chinayea.org.cn",
    "中国安全生产网": "https://www.chinayea.org.cn",
    "中国电力报": "http://www.cpnn.com.cn",
    "中电新闻网": "http://www.cpnn.com.cn",
    "国家电网报": "http://www.indaa.com.cn",
    "英大网": "http://www.indaa.com.cn",
    "中国石化报": "http://www.sinopecnews.com.cn",
    "中国石油报": "http://news.cnpc.com.cn",
    "中国铁道建筑报": "http://www.crcc.cn",
    "人民铁道": "http://www.peoplerail.com.cn",
    "人民铁道网": "http://www.peoplerail.com.cn",
    "中国建设报": "http://www.chinajsb.cn",
    "中国建设新闻网": "http://www.chinajsb.cn",
    "中国工业报": "http://www.cinn.cn",
    "中国工业新闻网": "http://www.cinn.cn",

    # 卫生/文旅/体育/群团社团类
    "健康报": "https://www.jkb.com.cn",
    "中国卫生杂志": "https://www.jkb.com.cn",
    "中国文化报": "https://www.ccmapp.cn",
    "文旅中国": "https://www.ccmapp.cn",
    "中国体育报": "http://www.chinasports.com.cn",
    "华奥星空": "http://www.sports.cn",
    "中国青年报": "https://www.cyol.com",
    "中青在线": "https://www.cyol.com",
    "中国妇女报": "https://www.cnwomen.com.cn",
    "中华女性网": "https://www.cnwomen.com.cn",
    "工人日报": "https://www.workercn.cn",
    "中国工人网": "https://www.workercn.cn",
    "中国社会报": "http://www.swchina.org",
    "中国社会工作报": "http://www.swchina.org",
    "《乡镇论坛》杂志": "http://www.mca.gov.cn",
    "《社区》杂志": "http://www.mca.gov.cn",
    "中国残疾人": "http://www.cdpf.org.cn",
    "中国红十字报": "http://www.redcross.org.cn",
    "中国中医药报": "http://www.cntcm.com.cn",
    "中国医药报": "http://www.cnpharm.com",
}

# ─── 4. 地方主流地级市广播电视台与报业规范官方主页 ──────────────────────────────
LOCAL_MEDIA_SPECIFIC_DOMAINS = {
    # 江西
    "鹰潭广播电视台": "http://www.0701.cn",
    "鹰潭市广播电视台": "http://www.0701.cn",
    "鹰潭日报": "http://epaper.ytrb.com.cn",
    "上饶市广播电视台": "http://www.srrw.cn",
    "上饶广播电视台": "http://www.srrw.cn",
    "上饶日报": "http://www.srxww.com",
    "九江市广播电视台": "http://www.jjxw.cn",
    "九江广播电视台": "http://www.jjxw.cn",
    "九江日报": "http://www.jjxw.cn",
    "南昌广播电视台": "http://www.nctv.net.cn",
    "南昌日报": "http://www.ncrb.cn",
    "赣州广播电视台": "http://www.gztv.com.cn",
    "赣州日报": "http://www.70701.com",
    "景德镇广播电视台": "http://www.jdzol.net",
    "萍乡市广播电视台": "http://www.pxsrm.com",
    "新余市广播电视台": "http://www.xytv.cn",
    "宜春市广播电视台": "http://www.yctv.cn",
    "吉安市广播电视台": "http://www.jatv.cn",
    "抚州市广播电视台": "http://www.fztv.net.cn",

    # 江苏
    "南京广播电视台": "http://www.nbs.cn",
    "南京日报": "http://www.njdaily.cn",
    "苏州广播电视总台": "http://www.csztv.com",
    "苏州日报": "http://www.subaonet.com",
    "无锡广播电视台": "http://www.thmz.com",
    "无锡日报": "http://www.wxrb.com",
    "常州广播电视台": "http://www.cztv.tv",
    "徐州广播电视台": "http://www.huaihai.tv",
    "南通广播电视台": "http://www.ntjoy.com",

    # 浙江
    "杭州市广播电视台": "http://www.hoolo.tv",
    "杭州日报": "https://www.hzrb.cn",
    "宁波广播电视集团": "http://www.nbtv.cn",
    "宁波日报": "http://www.cnnb.com.cn",
    "温州广播电视传媒集团": "http://www.wzrm.com",
    "绍兴市新闻传媒中心": "http://www.shaoxing.com.cn",
    "嘉兴市新闻传媒中心": "http://www.jiaxing.ren",

    # 广东
    "广州广播电视台": "https://www.gztv.com",
    "深圳广播电影电视集团": "https://www.sztv.com.cn",
    "珠海市新闻传媒中心": "https://pub-zhrs.hizh.cn",
    "佛山新闻传媒中心": "https://www.fsonline.com.cn",
    "东莞广播电视台": "http://www.sun0769.com",
    "中山广播电视台": "http://www.zsbtv.com.cn",

    # 山东
    "济南广播电视台": "http://www.ijntv.cn",
    "济南日报": "http://www.e23.cn",
    "青岛市广播电视台": "http://www.qtv.com.cn",
    "青岛日报": "https://www.dailyqd.com",
    "烟台广播电视台": "http://www.ytdaily.com",
    "潍坊市广播电视台": "http://www.wfcmw.cn",

    # 四川
    "成都广播电视台": "http://www.cditv.cn",
    "绵阳广播电视台": "http://www.myrmw.cn",
    "德阳广播电视台": "http://www.deyang.gov.cn",
    "宜宾广播电视台": "http://www.ybxww.com",

    # 湖北
    "武汉广播电视台": "http://www.whtv.com.cn",
    "长江日报": "http://www.cjn.cn",
    "襄阳广播电视台": "http://www.xfbtv.com",
    "宜昌三峡广播电视台": "http://www.yctv.net.cn",

    # 湖南
    "长沙广播电视台": "http://www.csrtv.com",
    "长沙晚报": "https://www.icswb.com",
    "株洲市广播电视台": "http://www.zzrmw.cn",
    "衡阳市广播电视台": "http://www.hydst.com",

    # 陕西
    "西安广播电视台": "http://www.xiancity.cn",
    "西安日报": "http://epaper.xiancn.com",
    "宝鸡市广播电视台": "http://www.baojinews.com",
    "咸阳市广播电视台": "http://www.xianyangtv.com",

    # 河北
    "石家庄广播电视台": "http://www.sjzntv.cn",
    "唐山广播电视台": "http://www.tsrm.com.cn",
    "保定市广播电视台": "http://www.bdrmw.cn",

    # 河南
    "郑州广播电视台": "http://www.zhengzhoutv.cn",
    "洛阳广播电视台": "http://www.lytv.com.cn",
    "开封广播电视台": "http://www.kftv.net.cn",

    # 福建
    "福州广播电视台": "http://www.zohi.tv",
    "厦门广播电视集团": "http://www.xmtv.cn",
    "泉州广播电视台": "http://www.qztv.cn",

    # 安徽
    "合肥市广播电视台": "http://www.hfbtv.com",
    "合肥日报": "http://www.hefei.gov.cn",
    "芜湖传媒中心": "http://www.wuhunews.cn",
}

# ─── 5. 典型省份融媒体聚合平台（各省地县融媒云） ────────────────────────────────
PROVINCIAL_RONGMEI_HUBS = {
    "江西": "http://www.jxnews.com.cn",
    "浙江": "https://www.cztv.com",
    "四川": "https://www.scdaily.cn",
    "湖北": "https://www.cnhubei.com",
    "广东": "https://www.southcn.com",
    "山东": "http://www.iqilu.com",
    "江苏": "http://www.jsbc.com",
    "湖南": "http://www.rednet.cn",
    "河南": "http://www.dahe.cn",
    "河北": "http://www.hebei.com.cn",
    "陕西": "http://www.cnwest.com",
    "福建": "http://www.fjsen.com",
    "安徽": "http://www.anhuinews.com",
}

# 知名县级政务融媒标准拼音映射
COUNTY_RONGMEI_GOV_DOMAINS = {
    "分宜县融媒体中心": "http://www.fenyi.gov.cn",
    "陈仓区融媒体中心": "http://www.chencang.gov.cn",
    "玉门市融媒体中心": "http://www.yumen.gov.cn",
    "韩城市广播电视台": "http://www.hancheng.gov.cn",
    "宜丰县融媒体中心": "http://www.yifeng.gov.cn",
    "上栗县融媒体中心": "http://www.shangli.gov.cn",
    "安源区融媒体中心": "http://www.anyuan.gov.cn",
    "永修县融媒体中心": "http://www.yongxiu.gov.cn",
    "德安县融媒体中心": "http://www.dean.gov.cn",
    "都昌县融媒体中心": "http://www.duchang.gov.cn",
    "湖口县融媒体中心": "http://www.hukou.gov.cn",
    "彭泽县融媒体中心": "http://www.pengze.gov.cn",
    "进贤县融媒体中心": "http://www.jinxian.gov.cn",
    "安义县融媒体中心": "http://www.anyi.gov.cn",
    "广丰区融媒体中心": "http://www.sxgf.gov.cn",
    "玉山县融媒体中心": "http://www.yushan.gov.cn",
    "铅山县融媒体中心": "http://www.yanshan.gov.cn",
    "横峰县融媒体中心": "http://www.hengfeng.gov.cn",
    "弋阳县融媒体中心": "http://www.yiyang.gov.cn",
    "余干县融媒体中心": "http://www.yugan.gov.cn",
    "鄱阳县融媒体中心": "http://www.poyang.gov.cn",
    "万年县融媒体中心": "http://www.wannian.gov.cn",
    "婺源县融媒体中心": "http://www.wuyuan.gov.cn",
    "德兴市融媒体中心": "http://www.dexing.gov.cn",
}


class DomainMapper:
    """智能媒体域名映射与寻址适配器"""

    @classmethod
    def is_invalid_url(cls, url):
        """检测 URL 是否为伪中文域名或空"""
        if not url:
            return True
        if any('\u4e00' <= c <= '\u9fff' for c in url):
            return True
        parsed = urlparse(url)
        if not parsed.netloc or "." not in parsed.netloc:
            return True
        return False

    @classmethod
    def resolve(cls, name, category, original_url=""):
        """
        全量智能解析与自适应寻址：
        返回：(resolved_url, source_type, is_fallback)
        """
        clean_name = name.replace("\n", "").strip()

        # 1. 优先查政务权威映射
        if clean_name in GOV_OFFICIAL_DOMAINS:
            return GOV_OFFICIAL_DOMAINS[clean_name], "GOV_DIRECT", False
        if name in GOV_OFFICIAL_DOMAINS:
            return GOV_OFFICIAL_DOMAINS[name], "GOV_DIRECT", False

        # 2. 查主流地方大报广电权威映射
        if clean_name in LOCAL_OFFICIAL_DOMAINS:
            return LOCAL_OFFICIAL_DOMAINS[clean_name], "LOCAL_PAPER_DIRECT", False
        if name in LOCAL_OFFICIAL_DOMAINS:
            return LOCAL_OFFICIAL_DOMAINS[name], "LOCAL_PAPER_DIRECT", False

        # 3. 查部委群团期刊映射表
        if clean_name in MINISTRY_PAPERS_DOMAINS:
            return MINISTRY_PAPERS_DOMAINS[clean_name], "MINISTRY_DIRECT", False
        for k, v in MINISTRY_PAPERS_DOMAINS.items():
            if k in clean_name or clean_name in k:
                return v, "MINISTRY_FUZZY", False

        # 4. 查地市报业/广电直连映射表
        if clean_name in LOCAL_MEDIA_SPECIFIC_DOMAINS:
            return LOCAL_MEDIA_SPECIFIC_DOMAINS[clean_name], "LOCAL_DIRECT", False
        for k, v in LOCAL_MEDIA_SPECIFIC_DOMAINS.items():
            if k in clean_name:
                return v, "LOCAL_FUZZY", False

        # 5. 查县区融媒体中心直连映射表
        if clean_name in COUNTY_RONGMEI_GOV_DOMAINS:
            return COUNTY_RONGMEI_GOV_DOMAINS[clean_name], "COUNTY_GOV_DIRECT", False

        # 6. 若原 URL 本身即为合法标准的英文/拼音公网域名，则保留
        if not cls.is_invalid_url(original_url):
            return original_url, "ORIGINAL_VALID", False

        # 7. 智能行政区划匹配与融合平台寻址（Fallback机制）
        for prov, hub_url in PROVINCIAL_RONGMEI_HUBS.items():
            if prov in clean_name:
                return hub_url, f"PROVINCIAL_HUB_{prov}", True

        county_m = re.search(r'([\u4e00-\u9fa5]{2,6}(?:县|区|市))', clean_name)
        if county_m:
            return "https://www.xinhuanet.com", "NATIONAL_HUB_FALLBACK", True

        return "https://www.news.cn", "DEFAULT_FALLBACK", True


if __name__ == "__main__":
    print(f"DomainMapper 初始化成功！")
    print(f"  - 政务官方权威映射: {len(GOV_OFFICIAL_DOMAINS)} 家")
    print(f"  - 地方大报广电映射: {len(LOCAL_OFFICIAL_DOMAINS)} 家")
    print(f"  - 部委群团重点期刊: {len(MINISTRY_PAPERS_DOMAINS)} 家")
    print(f"  - 地市主流报业台网: {len(LOCAL_MEDIA_SPECIFIC_DOMAINS)} 家")
    print(f"  - 县区融媒政务挂靠: {len(COUNTY_RONGMEI_GOV_DOMAINS)} 家")
