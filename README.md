# Outreachly

> AI-driven, multi-channel cold-outreach autopilot — from an idea to replies, on autopilot.
>
> AI 驱动的全渠道冷启动自动驾驶 —— 从一个产品想法,到收到回复,全自动。

[English](#english) · [中文](#中文)

---

## English

**Outreachly** turns a single product description (or a ready-made customer profile) into
qualified leads and personalized outreach across **Email, LinkedIn, and Twitter/X** — with
reply tracking and CRM auto-update built in.

### What it does

1. **ICP Engine** — describe your product, get a structured Ideal Customer Profile (ICP); or
   paste your own and edit it field by field.
2. **Lead Discovery** — find real, reachable leads via **Google Places API**, **Unipile**
   (LinkedIn), and the **X API** — no self-hosted scrapers.
3. **Enrichment** — email finding (Hunter/Apollo) + verification (NeverBounce) before sending.
4. **Personalized Sequences** — AI-written cold-email sequences and channel-specific DMs.
5. **Multi-channel Outreach** — send via Email / LinkedIn / Twitter from one place.
6. **Reply & CRM** — unified inbox, intent classification, automatic follow-up & status update.

### Architecture

- **Skill** — packaged as a single Claude Skill (`skill/SKILL.md`) orchestrating the script layer.
- **Backend** — FastAPI (Python), exposes the script layer as REST + CLI.
- **Frontend** — React + Vite, fully bilingual (中文 / English).
- **Storage** — local SQLite CRM.

See [`docs/PLAN.md`](docs/PLAN.md) for the full engineering plan and acceptance criteria.

### Quick start

```bash
cp .env.example .env       # fill in your API keys
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.db.init_db   # create the SQLite schema
uvicorn app.main:app --reload
# frontend
cd frontend && npm install && npm run dev
```

---

## 中文

**Outreachly** 把一句产品描述(或一份现成的客户画像)变成精准线索,并在
**邮件、LinkedIn、Twitter/X** 三个渠道上完成个性化触达 —— 内置回复跟踪与 CRM 自动更新。

### 功能

1. **画像引擎** —— 描述产品即得结构化理想客户画像(ICP);也可直接粘贴画像并逐字段编辑。
2. **线索发现** —— 经 **Google Places API**、**Unipile**(LinkedIn)、**X API** 获取真实可联系
   线索,代码中零自建爬虫。
3. **信息增强** —— 发送前完成邮箱挖掘(Hunter/Apollo)与有效性验证(NeverBounce)。
4. **个性化序列** —— AI 撰写冷邮件序列与各渠道差异化 DM。
5. **全渠道触达** —— 邮件 / LinkedIn / Twitter 统一发送。
6. **回复与 CRM** —— 统一收件箱、意向分类、自动跟进与状态更新。

### 技术架构

- **Skill** —— 打包为单一 Claude Skill(`skill/SKILL.md`),编排脚本层。
- **后端** —— FastAPI(Python),将脚本层暴露为 REST + CLI。
- **前端** —— React + Vite,完整中英双语。
- **存储** —— 本地 SQLite CRM。

完整工程流程与验收标准见 [`docs/PLAN.md`](docs/PLAN.md)。

---

## License

[MIT](LICENSE)
