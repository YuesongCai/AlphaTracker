"""First-boot seed data.

Narratives come straight from the podcast's own examples (UBER×AV,
SaaS×Agentic, DKNG×prediction markets...) so the demo tells the story.
One full thesis (UBER) demonstrates drivers/signposts/kill-criteria/journal.
Demo analysis content was AI-pre-generated at build time and is labeled so.
"""
from __future__ import annotations

import logging

from .db import get_setting, session_scope, set_setting
from .models import Driver, Idea, JournalEntry, Narrative, NarrativeTicker, Ticker

log = logging.getLogger(__name__)

SEED_FLAG = "seeded.v1"

TICKERS = [
    ("NVDA", "NVIDIA", "US", "半导体"),
    ("TSLA", "Tesla", "US", "汽车/AI"),
    ("UBER", "Uber", "US", "平台"),
    ("MSFT", "Microsoft", "US", "软件"),
    ("CRM", "Salesforce", "US", "软件/SaaS"),
    ("LLY", "Eli Lilly", "US", "医药"),
    ("DKNG", "DraftKings", "US", "博彩/消费"),
    ("0700.HK", "腾讯控股", "HK", "互联网"),
    ("9988.HK", "阿里巴巴", "HK", "互联网"),
    ("1810.HK", "小米集团", "HK", "消费电子/汽车"),
]

NARRATIVES = [
    {
        "title": "UBER × 自动驾驶:顺风还是逆风?",
        "question": "AV 规模化后,Uber 是被绕开的中间商,还是自动驾驶供给的聚合分发层?",
        "stance_bull": "AV 降低单均成本,Uber 作为需求聚合与车队运营层价值放大,TAM 扩容",
        "stance_bear": "Waymo/Tesla 自建闭环绕开 Uber,聚合层被去中介化,定价权消失",
        "kind": "company",
        "keywords": ["Uber robotaxi partnership", "Waymo Uber", "Tesla robotaxi launch"],
        "tickers": ["UBER", "TSLA"],
    },
    {
        "title": "SaaS × Agentic AI:订阅软件会被 Agent 杀死吗?",
        "question": "Agent 是 SaaS 的二次增长曲线,还是对席位订阅模式的结构性替代?",
        "stance_bull": "数据+工作流护城河仍在,agent 是增购;消耗定价打开单客户天花板",
        "stance_bear": "席位数长期萎缩,agent 平台层(模型厂商)吃掉应用层价值",
        "kind": "theme",
        "keywords": ["agentic AI enterprise software", "AI agents SaaS pricing"],
        "tickers": ["CRM", "MSFT"],
    },
    {
        "title": "DKNG × 预测市场:替代还是扩容?",
        "question": "CFTC 监管的预测市场是体育博彩的降维打击,还是拉新入口?",
        "stance_bull": "预测市场教育用户,DKNG 可自营切入;州税负担 vs 联邦牌照套利",
        "stance_bear": "Kalshi/Polymarket 无州税成本优势,分流高价值用户,压缩 hold rate",
        "kind": "company",
        "keywords": ["prediction markets sports betting", "Kalshi sports contracts"],
        "tickers": ["DKNG"],
    },
    {
        "title": "AI Capex 周期:超建还是刚需?",
        "question": "万亿级数据中心投资的回报何时被验证?谁在裸泳?",
        "stance_bull": "推理需求指数增长,算力仍供不应求,capex 有终端收入支撑",
        "stance_bear": "折旧周期错配+循环融资,收入兑现不及 capex 曲线,泡沫化",
        "kind": "theme",
        "keywords": ["AI capex data center spending", "hyperscaler capital expenditure"],
        "tickers": ["NVDA", "MSFT"],
    },
    {
        "title": "GLP-1 扩散:从减肥药到消费链冲击",
        "question": "GLP-1 渗透率曲线走到哪了?对食品/白酒/医疗器械的二阶冲击定价了吗?",
        "stance_bull": "口服剂型+适应症扩张,渗透率仍在早期,LLY/NVO 双寡头定价权",
        "stance_bear": "供给放量+仿制竞争,毛利率见顶;二阶冲击被高估",
        "kind": "theme",
        "keywords": ["GLP-1 obesity drug demand", "Eli Lilly Zepbound sales"],
        "tickers": ["LLY"],
    },
    {
        "title": "中国互联网:AI 叙事重估",
        "question": "腾讯/阿里的 AI 投入是防御性 capex 还是新增长曲线?估值折价会收敛吗?",
        "stance_bull": "推理成本下降+应用生态优势,AI 变现路径清晰,估值折价收敛",
        "stance_bear": "算力受限+变现滞后,capex 压制 FCF,折价反映治理与地缘风险",
        "kind": "theme",
        "keywords": ["Tencent AI strategy", "Alibaba AI cloud revenue"],
        "tickers": ["0700.HK", "9988.HK", "1810.HK"],
    },
]

_DEMO_META = {
    "engine": "seed",
    "disclaimer": "构建期 AI 预生成的演示内容(hypothesis 层素材),非投资建议",
}

UBER_THESIS = {
    "title": "UBER · AV 转型期的错杀多头",
    "direction": "long",
    "stage": "thesis",
    "sniff": {
        "business": "全球最大出行+即时配送聚合平台:撮合乘客/骑手与司机运力,抽取平台费;广告与会员为高毛利增量。",
        "focus5": {
            "organic_growth": {"assessment": "Bookings 中双位数增长,配送与广告快于出行", "score": 4},
            "margin_trajectory": {"assessment": "EBITDA 率持续爬坡,规模效应+广告结构性改善", "score": 4},
            "capital_intensity": {"assessment": "轻资产平台,不持有车队,capex 低", "score": 5},
            "capital_deployment": {"assessment": "已启动回购,纪律尚可;AV 合作以股权/商务协议为主", "score": 3},
            "terminal_value": {"assessment": "终局取决于 AV 格局:聚合层存活则久期长,被绕开则崩塌", "score": 2},
        },
        "price_question": "当前价格在问:AV 对 Uber 是生存威胁还是供给红利?市场按概率加权定价,波动来自叙事而非季报。",
        "debates": [
            {"question": "AV 规模化后聚合层是否被去中介化?",
             "bull": "AV 车队需要需求密度与动态调度,Uber 是最优分发层",
             "bear": "Waymo/Tesla 直营 App 自建闭环,绕开抽成"},
            {"question": "核心网约车增长的持续性?",
             "bull": "渗透率仍低,频次与新场景驱动双位数增长",
             "bear": "成熟市场饱和,价格竞争回归"},
            {"question": "AV 过渡期的资本纪律?",
             "bull": "商务合作模式轻资本,回购持续",
             "bear": "被迫补贴 AV 车队经济学,烧钱换份额"},
        ],
        "scenarios": {
            "bull": "AV 供给经由 Uber 分发,单均成本下降扩大 TAM,聚合层价值重估",
            "base": "AV 渗透缓慢,核心业务复利增长,估值区间震荡",
            "bear": "头部 AV 玩家自建闭环,Uber 沦为低毛利长尾运力池",
        },
        "verdict": {"action": "advance", "rationale": "典型的叙事错杀候选:终局分歧巨大而现金流现状扎实,值得建立完整 thesis 并监控路标"},
        "_meta": _DEMO_META,
    },
    "hypothesis": {
        "propositions": [
            {"text": "AV 过渡期(3-5年)内,第三方 AV 车队接入 Uber 的经济学优于自建直营", "status": "testing"},
            {"text": "核心平台 bookings 增速维持 ≥12%,支撑估值下限", "status": "testing"},
            {"text": "市场对 'AV=Uber 终结' 的定价过度,存在 expectations gap", "status": "testing"},
        ],
        "confirm": "Waymo 新城市优先经由 Uber 分发;AV 单均经济学公开数据支持聚合模式",
        "refute": "Tesla robotaxi 独立 App 在多城规模化且成本优势显著;Waymo 直营占比持续提升",
    },
    "thesis": {
        "variant_view": "市场把 AV 当作 Uber 的生存威胁定价;我们的差异化观点:AV 过渡期供给稀缺,聚合分发是 AV 车队最快的变现路径,Uber 的需求网络价值被低估。(播客原案例:$75 的股价隐含了 $200 顺风 / $25 逆风的概率加权)",
        "scenarios": {
            "bull": {"target": 200, "prob": 0.30, "note": "AV 顺风:分发协议+车队管理收入,重估为 AV 基础设施"},
            "base": {"target": 95, "prob": 0.45, "note": "AV 中性:核心业务复利,回购托底"},
            "bear": {"target": 25, "prob": 0.25, "note": "AV 逆风:被头部玩家绕开,多杀多"},
        },
        "ref_price": 75,  # 播客示例基于 ~$75 股价;实价偏离 >20% 时首次取价自动等比校准
        "auto_scale": True,
        "kill_criteria": [
            "Tesla robotaxi 独立 App 在 ≥3 个城市规模化运营且单均成本较 Uber 低 30%+",
            "Waymo 新增城市中直营占比连续两季上升、Uber 分发占比下降",
            "核心网约车 bookings 增速连续两季 <10%",
        ],
        "sizing_note": "中等仓位;事件(robotaxi 发布会/财报)前降杠杆",
        "_meta": _DEMO_META,
    },
    "drivers": [
        {
            "name": "AV 合作经济学(分发 vs 直营)",
            "description": "Waymo/其他 AV 车队经由 Uber 的订单占比、分成条款、新城市选择",
            "signposts": [
                {"text": "Waymo 新城市经由 Uber 独家/优先分发", "direction": "confirm", "hit": False},
                {"text": "Waymo 直营 App 在共存城市订单份额上升", "direction": "refute", "hit": False},
                {"text": "Tesla robotaxi 商业化进度超预期(多城+定价激进)", "direction": "refute", "hit": False},
            ],
        },
        {
            "name": "核心平台增长(bookings/MAPC/频次)",
            "description": "出行+配送 bookings 增速、月活跃消费者、使用频次、广告收入",
            "signposts": [
                {"text": "季度 bookings 增速 ≥15%", "direction": "confirm", "hit": False},
                {"text": "bookings 增速跌破 10%", "direction": "refute", "hit": False},
                {"text": "广告收入 run-rate 加速", "direction": "confirm", "hit": False},
            ],
        },
        {
            "name": "AV 监管与安全节奏",
            "description": "各州/各国 AV 商业运营牌照进度、重大安全事件、责任框架立法",
            "signposts": [
                {"text": "重大 AV 安全事故导致监管收紧(延缓去中介化)", "direction": "confirm", "hit": False},
                {"text": "联邦级 AV 框架加速放开(利好自建闭环玩家)", "direction": "refute", "hit": False},
            ],
        },
    ],
    "journal": [
        ("stage_change", "创建 hunch:AV 叙事导致的波动 vs 现金流基本面的背离(播客同款案例)"),
        ("stage_change", "升级为 Hypothesis:形成三个可检验命题,研究计划已生成"),
        ("belief_update", "Waymo 与 Uber 在凤凰城/奥斯汀的合作数据点支持'分发优先'假设,置信度上调"),
        ("stage_change", "升级为 Thesis:完成研究,进入监控。三情景概率 30/45/25,正偏赔率"),
    ],
    "notes": "【演示想法】播客原案例的完整落地:注意 thesis 里的差异化观点、kill criteria 与 driver 路标如何联动。价格情景为播客示例数字,已开启 auto_scale(首次取到实时价格后自动按比例校准)。",
}

CRM_HYPOTHESIS = {
    "title": "CRM · Agentic AI:被替代还是二次曲线?",
    "direction": "watch",
    "stage": "hypothesis",
    "sniff": {
        "business": "企业级 CRM 龙头,订阅收入为主,正把 Agentforce(AI agent 平台)作为第二增长曲线,按消耗计费。",
        "focus5": {
            "organic_growth": {"assessment": "核心订阅高个位数增长,增速换挡期", "score": 3},
            "margin_trajectory": {"assessment": "激进成本纪律推高利润率,但 AI 投入是逆风", "score": 3},
            "capital_intensity": {"assessment": "软件轻资产,AI 推理成本部分外购", "score": 4},
            "capital_deployment": {"assessment": "大额回购+并购历史毁誉参半", "score": 3},
            "terminal_value": {"assessment": "取决于 agent 时代应用层是否保有数据+工作流护城河", "score": 2},
        },
        "price_question": "多年低点的估值在问:席位订阅模式是否已死?任何 agent 变现证据都可能触发重估。",
        "debates": [
            {"question": "Agent 吃掉席位还是创造消耗收入?",
             "bull": "每替代一个席位产生更高消耗计费", "bear": "客户自建 agent,绕开应用层"},
            {"question": "数据护城河在 agent 时代是否成立?",
             "bull": "CRM 数据+权限+合规是 agent 落地前提", "bear": "模型厂商向上整合,数据可迁移"},
            {"question": "管理层资本配置可信度?",
             "bull": "回购纪律改善", "bear": "增长焦虑驱动大并购风险"},
        ],
        "scenarios": {
            "bull": "Agentforce 消耗收入放量,NRR 回升,戴维斯双击",
            "base": "核心稳态+agent 缓慢增长,估值修复有限",
            "bear": "席位流失加速,agent 变现不及预期,价值陷阱",
        },
        "verdict": {"action": "advance", "rationale": "SaaS×Agentic 叙事的最佳单一标的试金石,估值提供安全边际,值得跟踪验证"},
        "_meta": _DEMO_META,
    },
    "hypothesis": {
        "propositions": [
            {"text": "Agentforce 付费客户数与消耗收入连续两季环比加速", "status": "testing"},
            {"text": "席位→消耗切换期,整体 NRR 不跌破 105%", "status": "testing"},
            {"text": "agent 时代 CRM 数据护城河成立(客户不自建)", "status": "testing"},
        ],
        "confirm": "Agentforce 客户案例批量出现;消耗收入披露且加速",
        "refute": "大客户公开自建 agent 替代;NRR 连续下滑",
    },
    "journal": [
        ("stage_change", "创建 hunch:播客提到的 'SaaS 在 agentic 未来如何生存' 辩论,CRM 是试金石"),
        ("stage_change", "升级为 Hypothesis:三个命题聚焦 agent 变现证据,等待财报与客户数据点"),
    ],
    "notes": "【演示想法】处于 hypothesis 阶段:命题已定义,等待证据。下一步:生成研究计划,跟踪 Agentforce 数据点。",
}

DKNG_HUNCH = {
    "title": "DKNG · 预测市场冲击是否已过度定价?",
    "direction": "watch",
    "stage": "hunch",
    "sniff": {
        "business": "美国在线体育博彩+iGaming 双寡头之一,州牌照运营,收入=投注额×hold rate,营销与州税是主要成本。",
        "focus5": {
            "organic_growth": {"assessment": "新州渗透+parlay 结构优化驱动增长,但成熟州增速回落", "score": 3},
            "margin_trajectory": {"assessment": "营销效率改善推动 EBITDA 转正爬坡", "score": 3},
            "capital_intensity": {"assessment": "轻资产,技术与营销为主要投入", "score": 4},
            "capital_deployment": {"assessment": "仍在投入期,回购刚起步", "score": 3},
            "terminal_value": {"assessment": "预测市场若联邦化,州牌照护城河被侵蚀,终局不确定", "score": 2},
        },
        "price_question": "价格在问:CFTC 监管的预测市场会拿走多少体育投注份额?每次 Kalshi 新闻都在给这个概率重新定价。",
        "debates": [
            {"question": "预测市场是替代还是入口?",
             "bull": "预测市场教育新用户,DKNG 可申请牌照自营", "bear": "无州税+全国牌照的成本优势结构性分流"},
            {"question": "州税与联邦套利何时收敛?",
             "bull": "监管最终拉平竞争条件", "bear": "套利窗口期足够长,份额已丢"},
            {"question": "hold rate 天花板?",
             "bull": "parlay 渗透提升结构性 hold", "bear": "竞争压低定价,精明钱迁移"},
        ],
        "scenarios": {
            "bull": "预测市场冲击证伪,估值修复+自营预测市场期权",
            "base": "份额小幅流失,核心州业务稳态增长",
            "bear": "高价值用户迁移,增长与 hold 双杀",
        },
        "verdict": {"action": "advance", "rationale": "叙事驱动的波动远大于基本面变化,是'先分析股票再分析业务'的教学案例,值得升级 hypothesis"},
        "_meta": _DEMO_META,
    },
    "journal": [("stage_change", "创建 hunch:播客同款案例——预测市场 vs DKNG/FanDuel,监控 Kalshi 体育合约数据")],
    "notes": "【演示想法】hunch 阶段:sniff 完成,advance 前需要:1) Kalshi 体育合约成交量数据 2) 用户重合度研究。",
}

XIAOMI_HUNCH = {
    "title": "1810.HK · 汽车业务的估值锚在哪?",
    "direction": "watch",
    "stage": "hunch",
    "sniff": {
        "business": "消费电子(手机/IoT)+互联网服务+智能电动车:硬件引流、生态变现,汽车是第二曲线的资本重注。",
        "focus5": {
            "organic_growth": {"assessment": "手机稳态,汽车交付爬坡是核心增量", "score": 4},
            "margin_trajectory": {"assessment": "汽车毛利率爬坡速度超同业,但仍摊薄集团", "score": 3},
            "capital_intensity": {"assessment": "自建工厂+芯片投入,资本密集度显著上升", "score": 2},
            "capital_deployment": {"assessment": "生态协同逻辑清晰,但汽车吞噬现金流", "score": 3},
            "terminal_value": {"assessment": "若汽车站稳全球前五,终局价值大;竞争格局残酷", "score": 3},
        },
        "price_question": "价格在问:该给小米汽车多少倍收入?按手机公司还是按新势力估值?每次交付数据都在校准这个乘数。",
        "debates": [
            {"question": "汽车产能与需求的持续性?",
             "bull": "订单积压+产能爬坡,交付即增长", "bear": "价格战下需求前置,复购存疑"},
            {"question": "汽车毛利率能否到 20%?",
             "bull": "规模效应+自研占比提升", "bear": "竞争强度决定天花板在 15%"},
            {"question": "生态协同是真护城河吗?",
             "bull": "人车家闭环提升 LTV", "bear": "协同溢价难以量化,故事成分高"},
        ],
        "scenarios": {
            "bull": "汽车毛利率+交付双超预期,SOTP 重估",
            "base": "汽车按计划爬坡,集团利润率缓慢修复",
            "bear": "价格战+产能过剩,汽车拖累集团现金流",
        },
        "verdict": {"action": "advance", "rationale": "港股稀缺的硬科技+叙事标的,交付/毛利数据可高频验证,适合数据驱动的 thesis"},
        "_meta": _DEMO_META,
    },
    "journal": [("stage_change", "创建 hunch:汽车业务重估逻辑,等待月度交付与毛利率数据点")],
    "notes": "【演示想法】hunch 阶段。港股案例:验证数据源对 .HK 标的的覆盖。",
}


def ensure_seeded() -> None:
    with session_scope() as db:
        if get_setting(db, SEED_FLAG, False):
            return
        log.info("seeding initial data ...")

        tickers: dict[str, Ticker] = {}
        for symbol, name, market, sector in TICKERS:
            ticker = Ticker(symbol=symbol, name=name, market=market, sector=sector,
                            news_query=f"{name} stock" if market == "US" else f"{name}")
            db.add(ticker)
            tickers[symbol] = ticker
        db.flush()

        for spec in NARRATIVES:
            narrative = Narrative(
                title=spec["title"], question=spec["question"],
                stance_bull=spec["stance_bull"], stance_bear=spec["stance_bear"],
                kind=spec["kind"], keywords=spec["keywords"],
            )
            db.add(narrative)
            db.flush()
            for symbol in spec["tickers"]:
                db.add(NarrativeTicker(narrative_id=narrative.id,
                                       ticker_id=tickers[symbol].id))

        for spec, symbol in ((UBER_THESIS, "UBER"), (CRM_HYPOTHESIS, "CRM"),
                             (DKNG_HUNCH, "DKNG"), (XIAOMI_HUNCH, "1810.HK")):
            idea = Idea(
                ticker_id=tickers[symbol].id, title=spec["title"],
                direction=spec["direction"], stage=spec["stage"], is_demo=True,
                sniff=spec.get("sniff") or {}, hypothesis=spec.get("hypothesis") or {},
                thesis=spec.get("thesis") or {}, notes=spec.get("notes", ""),
            )
            db.add(idea)
            db.flush()
            for driver_spec in spec.get("drivers", []):
                db.add(Driver(idea_id=idea.id, name=driver_spec["name"],
                              description=driver_spec["description"],
                              signposts=driver_spec["signposts"]))
            for entry_type, content in spec.get("journal", []):
                db.add(JournalEntry(idea_id=idea.id, entry_type=entry_type,
                                    content=content))

        set_setting(db, SEED_FLAG, True)
        log.info("seed complete: %d tickers, %d narratives, 4 demo ideas",
                 len(TICKERS), len(NARRATIVES))
