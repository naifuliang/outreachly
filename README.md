# Outreachly

> AI-driven, multi-channel cold-outreach autopilot — packaged as a single Claude Skill.
>
> AI 驱动的全渠道冷启动自动驾驶 —— 打包为单一 Claude Skill。

[English](#english) · [中文](#中文)

---

## English

**Outreachly** is a single, importable Claude Skill. Drop the folder into your skills directory
and Claude can turn a product description (or a ready customer profile) into qualified leads and
personalized outreach across **Email, LinkedIn, and Twitter/X**, with reply tracking in a local
CRM.

**Design:** Claude does the reasoning (build the ICP, write sequences/DMs, classify replies)
right in the conversation. The `scripts/` only do what an LLM can't: call external APIs and
read/write the SQLite CRM. The result is small and easy to import — no web server or build step
required.

### Use it

```bash
pip install -r requirements.txt      # only dependency: httpx
cp .env.example .env                  # add keys for the channels you'll use
python scripts/crm.py init           # create the local CRM
# then just talk to Claude with the skill installed.
python scripts/serve_ui.py --open    # OPTIONAL local dashboard (skip if not wanted)
```

### Layout

```
SKILL.md          # skill manifest + workflow (Claude orchestrates)
scripts/          # external-IO tools: crm, discovery, enrichment, send, UI launcher
reference/        # icp_schema.json, channels.md (loaded on demand)
web/index.html    # OPTIONAL single-file bilingual dashboard
data/             # local SQLite CRM
```

See [`docs/PLAN.md`](docs/PLAN.md) for the roadmap and acceptance criteria, and
[`reference/channels.md`](reference/channels.md) for provider APIs.

---

## 中文

**Outreachly** 是一个可直接导入的 Claude Skill。把文件夹放进 skills 目录,Claude 就能把一句产品
描述(或一份现成画像)变成精准线索,并在 **邮件、LinkedIn、Twitter/X** 上完成个性化触达,回复
跟踪记录在本地 CRM。

**设计理念:** 推理类工作(生成画像、撰写序列/私信、判别回复意向)由 Claude 在对话中直接完成;
`scripts/` 只做 LLM 做不了的事 —— 调外部 API、读写 SQLite CRM。因此整体很小、易于导入,无需
Web 服务器或构建步骤。

### 使用

```bash
pip install -r requirements.txt      # 唯一依赖:httpx
cp .env.example .env                  # 填入你要用的渠道密钥
python scripts/crm.py init           # 创建本地 CRM
# 安装好 skill 后,直接与 Claude 对话即可。
python scripts/serve_ui.py --open    # 可选:本地看板(不需要可跳过)
```

### 目录

```
SKILL.md          # skill 清单 + 工作流(Claude 编排)
scripts/          # 外部 IO 工具:CRM、采集、增强、发送、UI 启动器
reference/        # icp_schema.json、channels.md(按需加载)
web/index.html    # 可选:单文件中英双语看板
data/             # 本地 SQLite CRM
```

路线图与验收标准见 [`docs/PLAN.md`](docs/PLAN.md),渠道 API 见
[`reference/channels.md`](reference/channels.md)。

---

## License

[MIT](LICENSE)
