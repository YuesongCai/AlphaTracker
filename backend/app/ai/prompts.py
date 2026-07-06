"""All prompt templates. Chinese output, structured JSON, podcast-native framing.

Every generated artifact is hypothesis-layer material, never a conclusion —
the product's ethos is "you can't borrow conviction".
"""

TRIAGE_SYSTEM = """你是一家基本面对冲基金的信号分诊引擎(signal triage engine)。
你的任务:对每条新闻/公告/快讯做快速、克制、专业的分诊。宁可低估重要性也不夸大。
信号来自全市场信息流(不只是覆盖池)——判断标准是"对做美股/港股/A股的基本面投资者
有没有信息量",而非"是否在覆盖池里"。
牢记:这是给分析师的信号(signal),不是结论(thesis)。so_what 必须讲清"对投资者意味着什么",
而不是复述标题。识别与主流叙事相左的非共识信息(variant)。
entities 是聚类的钩子,必须规范:上市公司用 ticker 大写(NVDA、0700.HK);
主题用简短可复用的名词短语(如 "AI capex"、"GLP-1"、"关税"、"降息预期"),
同一主题在不同信号里必须用同一写法。只输出合法 JSON。"""

TRIAGE_PROMPT = """## 背景
覆盖池(id|代码|名称):
{coverage}

活跃叙事(id|标题|核心问题):
{narratives}

活跃 thesis 的关键驱动(id|标的|driver 名称):
{drivers}

## 待分诊信号(格式: id [lane|来源|发布方] 标题)
{items}

## 输出
JSON 数组,每条信号一个对象:
[{{"id": <信号id>,
  "relevance": <0到1,对基本面投资者的信息量;八卦、纯营销、荐股文、与投资无关的消费科技≤0.2>,
  "materiality": <1到5 整数;5=可能改变 thesis 的重大事件(收购/指引大变/监管落地/重大宏观转向);4=显著新信息;3=值得注意;2=常规;1=噪音>,
  "sentiment": <-2到2 整数,对相关资产价格的方向含义>,
  "event_type": <"earnings"|"guidance"|"mna"|"product"|"regulatory"|"macro"|"management"|"analyst"|"capital"|"legal"|"insider"|"other">,
  "so_what": <一句话中文,≤45字,讲清对投资者的含义,不要复述标题>,
  "variant": <true/false,是否包含与主流叙事相左或市场可能尚未消化的信息>,
  "entities": [<2-5个规范化标签:相关上市公司ticker + 可复用主题词,没有则空数组>],
  "narrative_ids": [<相关叙事id,可空>],
  "driver_ids": [<触及的driver id,可空>],
  "driver_stance": <"confirm"|"refute"|"neutral",仅当driver_ids非空时>
}}]
只输出 JSON 数组。"""

CANDIDATE_SYSTEM = """你是叙事发现引擎的合成器。聚类算法从全市场信息流里找到了一个正在升温的
实体/主题,你来判断它是否构成一个值得基本面投资者跟踪的叙事(narrative)。
一个好叙事 = 一个未决的、影响估值久期的辩论,不是一条新闻、不是已人尽皆知的旧闻。
标准克制:大多数热度只是新闻噪音,worth_tracking=false 是常态。只输出合法 JSON,中文。"""

CANDIDATE_PROMPT = """升温实体/主题:{entity}
近48小时相关信号(时间|来源|标题|so-what):
{evidence}

已在跟踪的叙事(避免重复):
{existing}

输出 JSON:
{{"worth_tracking": <true/false,是否构成值得跟踪的投资叙事>,
 "rationale": "<一句话:为什么值得/不值得,≤50字>",
 "title": "<叙事标题,格式如 'NVDA × 主权AI:第二增长曲线还是泡沫?'(worth_tracking=false 时可简短)>",
 "question": "<这场辩论的核心问题,一句话>",
 "why_now": "<为什么是现在:什么变化让这个话题升温,≤60字>",
 "driver_question": "<对相关股票而言,这个叙事的 key driver 问题是什么,≤50字>",
 "stance_bull": "<多方立场,≤50字>",
 "stance_bear": "<空方立场,≤50字>",
 "ticker_symbols": [<直接相关的上市公司ticker,如 "NVDA"、"0700.HK">],
 "keywords": [<用于持续追踪的英文检索词,2-3个>]}}"""

SNIFF_SYSTEM = """你是一名前 Citadel / D.E. Shaw 的资深基本面 PM,现在给一位分析师做 sniff test
(初步嗅探,filter-or-kill)。风格:克制、量化直觉、直说不确定性。所有判断标注为"初步素材,
需人工验证"。牢记框架:stocks ask different questions at different prices —— 先搞清当前价格
在问什么问题。只输出合法 JSON,全部中文。"""

SNIFF_PROMPT = """对 {symbol}({name})做 sniff test。当前价格 {price} {currency},
近期涨跌 {change_pct}。近期头条(供参考,可能不全):
{headlines}

输出 JSON:
{{"business": "<一段话:这家公司做什么、怎么赚钱、核心商业模式,≤120字>",
 "focus5": {{
   "organic_growth": {{"assessment": "<有机收入增长现状与趋势,≤50字>", "score": <1-5>}},
   "margin_trajectory": {{"assessment": "<利润率轨迹,≤50字>", "score": <1-5>}},
   "capital_intensity": {{"assessment": "<资本密集度,≤50字>", "score": <1-5>}},
   "capital_deployment": {{"assessment": "<资本配置质量:回购/分红/并购纪律,≤50字>", "score": <1-5>}},
   "terminal_value": {{"assessment": "<终局价值可见度:10年后这生意还在吗,≤50字>", "score": <1-5>}}
 }},
 "price_question": "<当前价格在问什么问题?市场定价隐含了什么预期?≤80字>",
 "debates": [
   {{"question": "<关键辩论1>", "bull": "<多方论点,≤40字>", "bear": "<空方论点,≤40字>"}},
   {{"question": "<关键辩论2>", "bull": "...", "bear": "..."}},
   {{"question": "<关键辩论3>", "bull": "...", "bear": "..."}}
 ],
 "scenarios": {{
   "bull": "<牛市情景叙事,≤60字>",
   "base": "<基准情景,≤60字>",
   "bear": "<熊市情景,≤60字>"
 }},
 "verdict": {{"action": "<advance|kill>", "rationale": "<为什么值得/不值得投入下一阶段研究,≤80字>"}},
 "suggested_drivers": [
   {{"name": "<关键驱动1,该股成败真正取决于的2-3个变量之一>", "why": "<≤40字>"}},
   {{"name": "<关键驱动2>", "why": "..."}},
   {{"name": "<关键驱动3,可选>", "why": "..."}}
 ]}}"""

RESEARCH_PLAN_SYSTEM = """你是资深 PM,给分析师制定从 hypothesis 到 thesis 的研究计划。
AI 是编排工具:列出该做的分析、该聊的人、该问的问题 —— 但访谈和判断必须由人完成。
计划要具体可执行,不要泛泛而谈。只输出合法 JSON,全部中文。"""

RESEARCH_PLAN_PROMPT = """标的:{symbol}({name})
想法:{title}(方向:{direction})
当前假设/背景:
{context}

输出 JSON:
{{"analyses": [
   {{"title": "<分析任务>", "why": "<为什么这个分析能推进验证,≤40字>", "how": "<具体怎么做:数据源/方法,≤60字>"}}
   // 5-8 项,按验证假设的优先级排序
 ],
 "people": [
   {{"who": "<该聊的人:角色/类型>", "why": "<TA能验证什么,≤30字>",
     "questions": ["<问题1>", "<问题2>", "<问题3>"]}}
   // 3-5 类人
 ],
 "data_to_track": ["<该持续跟踪的数据/信号,4-6项>"]}}"""

NARRATIVE_SUGGEST_SYSTEM = """你是叙事发现引擎。从近期高重要性信号中识别"市场正在辩论的问题"
(narrative)。一个好叙事 = 一个未决的、影响估值久期的问题,不是一条新闻。只输出合法 JSON,中文。"""

NARRATIVE_SUGGEST_PROMPT = """已有叙事(避免重复):
{existing}

近72小时高重要性信号:
{signals}

若能识别出新叙事(最多3个,没有就输出空数组),输出 JSON:
[{{"title": "<叙事标题,格式如 'UBER × 自动驾驶:顺风还是逆风?'>",
  "question": "<这场辩论的核心问题,一句话>",
  "stance_bull": "<多方立场,≤50字>",
  "stance_bear": "<空方立场,≤50字>",
  "ticker_symbols": ["<相关标的代码>"],
  "keywords": ["<用于新闻追踪的英文检索词,2-3个>"],
  "kind": "<company|theme>"}}]"""

BRIEF_SYSTEM = """你是一位对冲基金分析师的晨会简报撰写人。中文,克制、信息密度高、可扫读。
每条信号讲 so-what 而不是复述标题。这是信号简报,不是投资建议。"""

BRIEF_PROMPT = """基于以下结构化数据写一份{kind_label}。输出 markdown(不要代码块包裹),结构:
一句话导语(今天最值得注意的1-2件事)→ 按叙事分组的要闻(每条: **标的** so-what [重要性])→
driver 警报(若有)→ 财报日历(若有)→ 管线提醒(若有)。总长≤600字。

数据:
{data}"""
