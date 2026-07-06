# Mosaic — Variant Perception Engine

> 把顶级对冲基金的 investment process 产品化:AI 加速 Hunch → Hypothesis 阶段,
> 持续追踪 narrative 与 key drivers,把关键信号推到飞书,
> 让 analyst 把时间花在真正产生 alpha 的判断上。

灵感来自 Ex-Citadel / D.E. Shaw PM Brett(Fundamental Edge)的方法论访谈。
产品名取自其反复强调的 **"mosaic of insight"** —— 洞察不来自单一信息,而来自碎片的拼合。

---

## 1. 为什么做这个产品(真需求)

播客里的核心论断,逐条对应到 analyst 的日常痛点:

| 播客方法论 | analyst 的真实痛点 | Mosaic 的回答 |
|---|---|---|
| "Alpha lives in the tails" —— 80% 股票定价合理,机会在两端 10% | 看 60 个 idea 才能找到 3 个值得做的,前置筛选耗掉大量时间 | **AI Sniff Test**:一键生成结构化速览,快速 filter-or-kill |
| Idea 生命周期 = Hunch → Hypothesis → Thesis | 想法散落在备忘录/微信/脑子里,没有漏斗管理,不知道每个想法卡在哪一层 | **Idea Pipeline**:三阶段看板,每次晋级/否决都留痕 |
| "Narrative cycles matter a lot" —— 股价久期 30-50 年,叙事驱动重估 | 叙事在新闻流里悄悄转向(UBER×AV、SaaS×Agentic),等你看到已经 price in | **Narrative Engine**:叙事卡片 + 证据时间线 + 动量评分 |
| 关键是 2-3 个 key drivers,"stocks ask different questions at different prices" | 信息太多,不知道哪条新闻真正 touch 到 thesis 的 driver | **Driver Monitor**:每个 thesis 挂 drivers + signposts,新闻自动映射 |
| "Public market investing is deeply Bayesian" —— 每天更新先验 | 没有机制强迫你面对新证据、更新信念,thesis creep 无人提醒 | **贝叶斯日志**:material 证据触发信念更新记录 |
| "It's a signal, not a thesis" —— 64 种可自动化的信号仪表盘 | 手工盯盘/盯新闻是低价值劳动 | **Signal Engine**:多源摄取 + AI triage(materiality/sentiment/event type/so-what) |
| "AI 可以 orchestrate 人的下游动作" —— 研究计划、访谈名单、问题清单 | 从 hypothesis 到 thesis 不知道该做哪些工作 | **Research Plan 生成器**:分析清单 + 该聊的人 + 问题列表,human-in-the-loop 勾选 |
| "Optimize for rigor, not speed" | 用户经常不在电脑前,担心错过关键变化 | **飞书早晚报 + 即时警报**:重要性 ≥4 的信号即时 DM |

**一句话定位**:不是"AI 帮你做判断",而是播客说的 **exoskeleton(外骨骼)**——
自动化低价值信号采集,把节省的时间和浮现的信号交给人的 judgment。

## 2. 明确不做什么(产品边界)

- ❌ 不生成买卖建议、不给目标价背书 —— "consensus view is a losing view",AI 产出一律标注为
  hypothesis 层素材,thesis 必须人工确认晋级("you can't borrow conviction")
- ❌ 不做行情终端 —— 价格仅作上下文,不做 K 线/技术分析(用户已有 Futu/TradingView)
- ❌ 不做持仓/交易管理 —— 到 thesis 为止,下单在券商

## 3. 核心对象模型

```
Ticker(覆盖池) ──┬── Signal(新闻/公告/情绪,AI triage 后带 materiality/sentiment/so-what)
                  │        │ 多对多
                  ├── Narrative(叙事:一个被辩论的问题 + bull/bear 立场 + 证据时间线 + 动量)
                  │
                  └── Idea(想法:hunch → hypothesis → thesis / killed)
                          ├── SniffTest(Focus-5、关键辩论、初步 bull/base/bear、advance-or-kill)
                          ├── Driver(2-3 个关键驱动)──── Signpost(确认/证伪路标)
                          │        └── Evidence(信号挂到 driver,标注 confirm/neutral/refute)
                          ├── ResearchPlan(分析清单 + 访谈对象 + 问题列表,可勾选)
                          ├── Thesis(bull/base/bear 目标价+概率 → 期望值/赔率,kill criteria)
                          └── Journal(阶段变更、信念更新、笔记 —— 过程留痕)
```

**Focus-5**(播客原框架,Sniff Test 的骨架):organic revenue growth /
margin trajectory / capital intensity / capital deployment / terminal value visibility。

## 4. 数据源(v1.1 重构:官方 wire 五通道,MacroRadar 模式)

**设计转向**:v1.0 依赖 Google News 搜索代理 —— 不 solid。v1.1 改为直连官方 wire,
市场级通道不依赖任何 ticker 输入,是发现引擎的原料:

| 通道 | 源 | 频率 |
|---|---|---|
| 宏观 | **金十数据** flash + 财经日历(MCP 直连,绕代理防 SSE 截断) | 每 20 分钟 |
| 宏观 | NYT Economy、FT、美联储官方 RSS | 每 20 分钟 |
| 市场 | WSJ Markets/Business、CNBC Top/Markets、MarketWatch、Seeking Alpha 快讯、NYT Business(官方 RSS) | 每 20 分钟 |
| 科技 | CNBC Tech、TechCrunch、The Verge、HN 头版≥80分 | 每 20 分钟 |
| 公告 | **EDGAR getcurrent 全市场流**(所有新 8-K / SC 13D 举牌) | 每 20 分钟 |
| 个股 | Google News 关键词、Yahoo 报价/财报日、EDGAR 按 CIK、StockTwits 情绪、手动录入 | 20-60 分钟 |

单源容错(一条 wire 挂了不影响其余)。凭证(金十 token、EDGAR 联系方式)存
`data/secrets.json` / 设置页 / 环境变量,不进 git。
OpenBB 评估结论:**借地图不借包** —— 其新闻 provider 基本 key-gated(benzinga/biztoc/fmp),
keyless 端点(yfinance/SEC/nasdaq)直连即可,不值得背依赖树。

## 4.5 发现引擎(v1.1 核心:从 monitor 转向 discover)

**产品哲学修正**:不是"你输入 ticker 我来盯",而是"引擎从纷杂信息流里 cut through noise,
把 narrative 和值得深挖的 key driver 喂给你"。

管线:全市场信号 → triage 抽取规范化实体(ticker + 主题标签)→ 48h 滚动聚类 →
评分 = 热度(重要性加权+时间衰减)× 跨源广度(≥3 独立信源加成)× 跨通道加成 × 新颖度(vs 30 天基线)→
高分新聚类由 AI 合成**叙事候选**(标题/核心辩论/为什么是现在/key driver 问题/多空框架/相关标的)→
用户 promote(自动建叙事+标的入池+证据挂载,进入持续追踪)或 dismiss(压制 7 天)。
AI 判为噪音的候选折叠展示,可人工翻案 —— 引擎克制,判断永远在人。
雷达页为默认落地页;新候选进飞书晨晚报。

## 5. AI 层(三级降级,永不宕机)

1. **Anthropic API**(设置页贴 key,支持自定义 base_url/代理)—— 全功能
2. **claude CLI**(检测本机 `claude -p` 可用即自动启用,走订阅)—— 全功能
3. **规则引擎兜底**(关键词事件分类 + 来源权重)—— 摄取/监控/推送照常,生成类功能显示接入指引

AI 做的事(全部输出中文、结构化 JSON、带"这是素材不是结论"标注):
- **Triage**:批量给信号打 relevance / materiality(1-5)/ sentiment(-2..+2)/ 事件类型 /
  一句话 so-what / 是否偏离共识,并映射到 narrative 与 driver
- **Sniff Test**:业务一段话 + Focus-5 + 当前价格在问什么问题 + 3 个 key debates + 初步三情景 + advance-or-kill 建议
- **Research Plan**:该做的分析、该聊的人、该问的问题
- **Narrative 建议**:从信号簇里发现新叙事
- **早晚报**:隔夜信号按叙事聚类,重要性排序,写成可读简报

## 6. 飞书通道(用户经常离开电脑 —— 一等公民)

- **早报 08:00 / 晚报 19:30**(北京时间,可配):隔夜 top signals(按叙事分组)+ 本周财报日历 + driver 警报
- **即时警报**:thesis 阶段个股 materiality≥4、或全池 materiality=5 的信号,立刻 DM
- 通道:本机 `lark-cli` bot DM(已验证),产品内可开关

## 7. 技术架构

```
backend/   Python 3.12 · FastAPI · SQLite(SQLAlchemy) · APScheduler · httpx/feedparser
           app/sources/*    摄取插件(google_news, yahoo, edgar, stocktwits)
           app/ai/*         provider 三级降级 + prompts + triage/sniff/research/brief
           app/services/*   ingest · narrative 动量引擎 · idea/EV 计算 · brief 组装 · feishu
           app/api/*        REST(dashboard/tickers/signals/narratives/ideas/brief/settings/ops)
frontend/  React 18 · Vite · TypeScript · Tailwind — 构建后由后端静态托管,单端口部署
运行        ./start.sh → http://127.0.0.1:8788(局域网可分享给朋友看)
测试        pytest(动量/EV/去重/规则分类)+ 端到端真实数据验证
```

**为什么本地优先**:研究观点是敏感数据;零服务器成本;lark-cli 就在本机。
需要公网演示时,前端可一键导出静态 demo 部署到飞书妙搭(预留)。

## 8. 界面(深色终端风,展业可看)

1. **今日** —— 隔夜要闻(materiality 排序 + so-what)、叙事动量榜、driver 警报、财报日历、最新简报
2. **信号流** —— 全量可筛(ticker/叙事/事件类型/重要性/关键词)
3. **叙事** —— 卡片墙(动量分 + 趋势箭头)→ 详情:辩论框架(bull vs bear)、证据时间线、关联 idea
4. **管线** —— Hunch / Hypothesis / Thesis / Killed 看板;一键对任意 ticker 发起 Sniff Test
5. **Idea 详情** —— Sniff 报告、研究计划勾选、drivers+signposts+证据、三情景 EV 条、贝叶斯日志
6. **覆盖池** —— ticker 表(价格/财报日/信号数)+ 添加;个股页聚合该票全部信息
7. **设置** —— LLM 状态与 key、飞书配置、调度频率、手动触发

## 9. 种子内容(播客同款案例,demo 即叙事)

- 覆盖池:NVDA、TSLA、UBER、MSFT、CRM、LLY、DKNG、0700.HK、9988.HK、1810.HK
- 预置叙事(直接来自播客举例,给朋友演示时可以讲"这就是那期播客里 PM 说的债"):
  UBER×自动驾驶、SaaS×Agentic AI、DKNG×预测市场、AI Capex 周期、GLP-1 扩散、中国互联网 AI 重估
- 预置 1 个完整 thesis 示例(UBER,含 drivers/signposts/三情景)+ 1 个 hypothesis(CRM)+ 2 个 hunch,
  内容为构建时 AI 预生成并标注 demo,展示产品满血状态

## 10. Roadmap

- **v1(本次交付)**:上述全部 —— 多源摄取、AI triage、叙事引擎、三阶段管线、Sniff Test、
  driver 监控、飞书早晚报+警报、完整前端
- **v1.1**:guidance credibility 分析(播客的"历史指引可信度"工作流,基于 EDGAR 历史 8-K)、
  财报倒计时预警强化、narrative 动量图表
- **v2**:transcript 摄取与检索、context document 管理(播客的"art of context")、
  多人协作(团队共享叙事库)、公网部署版
