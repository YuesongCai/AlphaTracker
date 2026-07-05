# Mosaic — Variant Perception Engine

> AI 加速 Hunch → Hypothesis,人负责 Judgment。
> 基于一位 Ex-Citadel / D.E. Shaw PM 的 investment process 方法论构建的个人研究操作系统。

![stack](https://img.shields.io/badge/stack-FastAPI%20·%20React%20·%20SQLite-1d2634)
![data](https://img.shields.io/badge/data-GoogleNews%20·%20Yahoo%20·%20EDGAR%20·%20StockTwits-f0b429)

## 快速开始

```bash
git clone https://github.com/YuesongCai/AlphaTracker.git
cd AlphaTracker
./start.sh          # 首次自动装依赖+构建前端,之后直接起服务
# → http://127.0.0.1:8788
```

> 环境要求:macOS/Linux,Python 3.11+,Node 18+(仅首次构建前端需要)。
> 飞书推送可选,依赖本机 `lark-cli`(设置页可改路径或关闭);SEC EDGAR 抓取建议
> `export MOSAIC_EDGAR_UA="YourTool your@email.com"` 表明身份。

首次启动自动完成:建库 → 灌入种子(10 标的、6 条播客同款叙事、4 个演示想法)→
立即抓取一轮真实数据(新闻/报价/EDGAR/情绪)。之后每 20/30/60 分钟自动更新。

## 它做什么

| 模块 | 干什么 | 对应方法论 |
|---|---|---|
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
- 测试:`cd backend && ../.venv/bin/python -m pytest tests/ -q`(22 个用例)
- 数据全部本地(`data/mosaic.db`),研究观点不出机器

## 数据源

| 源 | 内容 | 说明 |
|---|---|---|
| Google News RSS | 个股+叙事关键词新闻 | 美股/港股/中英文皆可 |
| Yahoo Finance | 报价、财报日期 | 港股用 `0700.HK` 格式 |
| SEC EDGAR | 8-K/10-K/10-Q/13D 等公告 | 美股;自动映射 CIK |
| StockTwits | 散户情绪(多头占比) | 美股 |
| 手动录入 | 专家访谈、渠道调研等私有信息 | 信号流页右上角 |

## 提醒

所有 AI 产出均为 **hypothesis 层素材**,标注引擎与免责声明,不构成投资建议 ——
判断(judgment)是人的工作,这正是本产品的设计哲学。
