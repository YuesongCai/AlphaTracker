# Mosaic — Variant Perception Engine

> 引擎从全市场信息流里 cut through noise,把涌现的叙事喂给你;
> AI 加速 Hunch → Hypothesis,人负责 Judgment。
> 基于一位 Ex-Citadel / D.E. Shaw PM 的 investment process 方法论构建的个人研究操作系统。

![stack](https://img.shields.io/badge/stack-FastAPI%20·%20React%20·%20SQLite-1d2634)
![data](https://img.shields.io/badge/data-Jin10%20·%20WSJ%2FCNBC%2FMW%2FSA%2FNYT%2FFT%20·%20EDGAR%20·%20HN%20·%20Yahoo-f0b429)

## 快速开始

```bash
git clone https://github.com/YuesongCai/AlphaTracker.git
cd AlphaTracker
./start.sh          # 首次自动装依赖+构建前端,之后直接起服务
# → http://127.0.0.1:8788
```

> 环境要求:macOS/Linux,Python 3.11+,Node 18+(仅首次构建前端需要)。
> macOS 常驻部署:`./scripts/install-service.sh` 注册为 LaunchAgent(登录自启、崩溃自动拉起)。
> 覆盖池支持「批量导入」直接粘贴组合代码;演示数据默认不装,`MOSAIC_DEMO=1 ./start.sh` 可选装。
> 飞书推送可选,依赖本机 `lark-cli`(设置页可改路径或关闭);SEC EDGAR 抓取建议
> `export MOSAIC_EDGAR_UA="YourTool your@email.com"` 表明身份。

首次启动自动完成:建库 → 灌入种子(10 标的、6 条播客同款叙事、4 个演示想法)→
立即抓取一轮真实数据(新闻/报价/EDGAR/情绪)。之后每 20/30/60 分钟自动更新。

## 它做什么

| 模块 | 干什么 | 对应方法论 |
|---|---|---|
| **雷达** ★ | 发现引擎主页:48h 滚动聚类全市场信号 → 热度×跨源广度×新颖度评分 → AI 合成**涌现叙事候选**(为什么是现在 / key driver / 多空框架),一键 promote 进入追踪或忽略;趋势实体、金十财经日历、分通道信号流 | 不是你输入 ticker 让它盯,是它从噪音里切出 narrative 喂你 |
| **今日** | 隔夜要闻(重要性排序+so-what)、叙事动量、driver 警报、财报日历 | 晨会前 5 分钟扫完该看的 |
| **信号流** | 多源新闻/公告自动摄取 + AI 分诊(M1-M5 重要性/情绪/事件类型/非共识标记) | "It's a signal, not a thesis" |
| **叙事** | 把"市场在辩论的问题"变成可监控对象:证据时间线 + 动量评分 | narrative cycle 决定久期资产重估 |
| **管线** | Hunch → Hypothesis → Thesis 看板,AI Sniff Test 一键嗅探(Focus-5 + 关键辩论 + 三情景) | 看 60 砍 50 深挖 10 做 3 |
| **Idea 详情** | 差异化观点、kill criteria、drivers+signposts 路标、研究计划勾选、贝叶斯日志、三情景 EV | "You can't borrow conviction" |
| **飞书** | 晨报 08:00 / 晚报 19:30 + 重大信号即时警报,人不在电脑前也不漏 | 外骨骼,不是替代 |

## AI 引擎(三级降级,永不宕机)

1. **Anthropic API** — 设置页贴 key(支持自定义 base_url 代理)
2. **claude CLI** — 本机登录过 `claude` 即自动启用,走订阅零成本
3. **规则引擎** — 无 AI 时关键词分诊,监控/推送照常

## 飞书推送

依赖本机 `lark-cli`(bot → 用户 DM)。设置页可改接收人 open_id、
简报时间、警报阈值,或整体关闭。

## 技术

- `backend/` FastAPI + SQLite + APScheduler;数据源插件式(`app/sources/`)
- `frontend/` React 18 + Vite + TS + Tailwind v4,构建后由后端同端口托管
- 测试:`cd backend && ../.venv/bin/python -m pytest tests/ -q`(29 个用例)
- 数据全部本地(`data/mosaic.db`),研究观点不出机器

## 数据源(五通道)

**市场级通道**(发现引擎的原料,不依赖你输入 ticker):

| 通道 | 源 | 说明 |
|---|---|---|
| 宏观 | **金十数据** flash + 财经日历(MCP 直连) | 中文宏观/市场最快 wire;设置页或 `data/secrets.json` 配 token,无 token 自动跳过 |
| 宏观 | NYT Economy · FT · 美联储官方 | 官方 RSS 直连 |
| 市场 | WSJ Markets/Business · CNBC Top/Markets · MarketWatch · Seeking Alpha 快讯 · NYT Business | 官方 RSS 直连,非搜索代理 |
| 科技 | CNBC Tech · TechCrunch · The Verge · **Hacker News 头版**(≥80分) | 科技叙事最早的风向标 |
| 公告 | **EDGAR getcurrent 全市场流**:所有新 8-K/SC 13D(举牌) | 全市场公司事件雷达,纯规则分诊控制 LLM 成本 |

**个股通道**(覆盖池内标的):Google News 关键词 + Yahoo 报价/财报日 + EDGAR 按 CIK + StockTwits 情绪 + 手动录入(专家访谈/渠道调研)。

> SEC 要求 UA 带联系方式:`export MOSAIC_EDGAR_UA="YourTool your@email.com"`
> 或在 `data/secrets.json` 写 `{"edgar_ua": "...", "jin10_token": "..."}`(该文件不进 git)。

## 提醒

所有 AI 产出均为 **hypothesis 层素材**,标注引擎与免责声明,不构成投资建议 ——
判断(judgment)是人的工作,这正是本产品的设计哲学。
