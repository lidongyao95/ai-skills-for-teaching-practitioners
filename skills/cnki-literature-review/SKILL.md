---
name: cnki-literature-review
version: 2.1.0
description: "知网(CNKI)文献调研全流程：多关键词检索、PDF下载、全文提取、智能筛选与结构化综述。支持Playwright脚本自动化和agent-browser交互浏览两种模式。适用于文献综述、论文调研、知网下载、学术检索、开题报告、研究现状梳理等场景。"
metadata:
  requires:
    bins: ["python3"]
    python: ["playwright", "pymupdf"]
  optional:
    bins: ["agent-browser"]
---

# 知网文献调研（CNKI Literature Review）

> **网络前提：** 必须在高校机构 IP 环境下执行（校园网或 VPN）。

## 何时使用

- 用户要做文献综述、研究现状、开题/课题调研
- 需要从知网检索并**下载 PDF 全文**
- 需要对多篇文献做结构化摘要与对比分析

## 工作流总览

```
需求澄清 → 多关键词检索 → 智能筛选 → 下载 PDF → 提取全文 → 单篇摘要 → 综合综述
```

复制此清单跟踪进度：

```
- [ ] Step 0: 初始化工作目录
- [ ] Step 1: 澄清调研需求（主题/关键词/时间/数量）
- [ ] Step 2: 多关键词知网检索（JS提取模式）
- [ ] Step 3: 智能筛选（期刊质量 + 主题相关性）
- [ ] Step 4: 下载 PDF（需机构IP）
- [ ] Step 5: 提取 PDF 全文
- [ ] Step 6: 生成单篇结构化摘要
- [ ] Step 7: 输出综合文献综述
```

---

## Step 0: 初始化工作目录

```bash
python3 scripts/init_workspace.py --topic "研究主题" --dir ./literature-review
```

产出目录：
```
literature-review/
├── papers/pdf/       # 下载的 PDF（统一命名为 cnki-xxx.pdf）
├── papers/text/      # 提取的全文 txt
├── papers/meta/      # 元数据 JSON + mapping.json
├── summaries/        # 单篇摘要 markdown
├── search/           # 检索记录与候选列表
├── review/           # 最终综述
└── logs/             # 下载与提取日志
```

---

## Step 1: 澄清调研需求

向用户确认以下字段（缺省按合理默认值推进）：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| 主题 | 研究问题或领域 | 必填 |
| 关键词 | 3-5组检索词（含同义词） | 主题扩展 |
| 时间范围 | 发表年份 | 近一年半 |
| 文献类型 | 期刊/硕博/会议 | 核心期刊 |
| 目标数量 | 最终纳入篇数 | 15-20 篇 |

关键词设计原则：**覆盖同义表达、交叉领域、政策术语**。

示例：主题=工程实践教学 → 关键词=["工程实践 AND 教学", "产教融合 AND 工程教育", "新工科 AND 实践教学", "工程训练 AND 教学改革", "工程实践能力 AND 培养"]

将确认结果写入 `search/brief.json`。

---

## Step 2: 多关键词知网检索

### ⚠️ 核心原则：优先使用 JS evaluate 模式

**切勿使用 DOM 选择器（`page.locator("table.result-table-list tr")` 等）**，知网页面结构频繁改版，选择器极易失效。经过实战验证，`page.evaluate()` 直接从表格 `td` 元数据提取是最可靠的方式。

```bash
python3 scripts/cnki_search.py \
  --keywords "工程实践 AND 教学,产教融合 AND 工程教育,新工科 AND 实践教学" \
  --year-from 2025 \
  --year-to 2026 \
  --max-results 40 \
  --max-pages 10 \
  --result-timeout 20 \
  --output ./literature-review/search/candidates.json
```

参数说明：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--keywords` | 必填 | 逗号分隔的多组检索词 |
| `--year-from` | 当前年份-1 | 起始年份 |
| `--year-to` | 当前年份 | 结束年份 |
| `--max-results` | 40 | 每组关键词最多获取篇数 |
| `--max-pages` | 10 | 每组关键词最多翻页数；年份过滤后结果不足时可调大 |
| `--result-timeout` | 20 | 等待结果表或无结果提示的最长秒数，避免少结果/无结果时卡在页面后台请求 |
| `--headless` | false | 是否无头模式；CNKI 可能返回空白页，优先使用默认有界面模式 |

### JS 提取原理

脚本在知网结果页执行以下 JS，直接从 `<table>` 行中抓取每个 `<td>` 的文本内容作为元数据数组：

```javascript
const rows = document.querySelectorAll('table.result-table-list tr');
rows.forEach(row => {
    const tds = row.querySelectorAll('td');
    const link = row.querySelector('a.fz14, td.name a');
    // texts[0]=序号, texts[1]=题名(冗余), texts[2]=作者,
    // texts[3]=刊名, texts[4]=年份期数, texts[5]=被引, texts[6]=下载
    results.push({ title, href, texts: [...tds].map(td => td.textContent.trim()) });
});
```

### 容错机制

脚本使用 `domcontentloaded` 后自行轮询结果表，不再依赖 `networkidle`。如果搜索结果很少、页面提示无结果，或 CNKI 后台请求持续不断，脚本会在 `--result-timeout` 到达后按当前解析结果继续，避免单组关键词长时间卡住。脚本会优先使用 CNKI 左侧「年度」分组应用 `--year-from/--year-to`，再按 `--max-pages` 翻页收集候选；若年度分组无法点击或没有目标年份，才用结果表日期做兜底过滤。注意：CNKI「年度」和结果表「发表时间」/上架日期可能不是同一口径，候选 JSON 中的 `year` 表示结果表日期解析出的年份；因此结果表年份超出筛选范围不代表年度分组未生效。

如果 JS 提取也失败，使用 agent-browser 交互模式兜底：

```bash
agent-browser open "https://kns.cnki.net/kns8s/defaultresult/index?kw=工程实践%20AND%20教学"
agent-browser wait --load networkidle
agent-browser get text body > page.txt
# 从 page.txt 中手动提取论文信息，录入 candidates.json
```

---

## Step 3: 智能筛选

```bash
python3 scripts/curate.py \
  --input ./literature-review/search/candidates.json \
  --topic "工程实践,教学,实践教学" \
  --max 20 \
  --sort-by citations
```

筛选逻辑：**主题相关性评分**（从 `--topic` 拆分关键词匹配），可选叠加期刊质量过滤（`--journal-list`）。

- `--topic`：主题关键词，支持逗号、顿号、分号、空格或 `AND/OR/NOT` 分隔；例如 `"工程实践,教学"`、`"工程实践 教学"`、`"工程实践 AND 教学"` 都会解析为多个关键词
- `--journal-list`：逗号分隔的目标期刊列表，传入后按期刊白名单过滤；不传则不做期刊过滤，仅按主题相关性打分
- 自动过滤 K-12 学段论文（识别"小学""初中""高中""校本"等关键词）
- 主题关键词自动从调研主题拆分，计算 relevance_score
- Fallback 机制：若入选不足，放宽阈值，按主题相关性补录
- `--sort-by`：最终排序依据（`citations` 被引 / `downloads` 下载 / `relevance` 主题相关性），默认 `citations`。排序始终以主题相关性为第一键（先保相关、再比质量），避免高被引但跑题的论文排在前面
- **筛选后自动重新分配唯一 ID**（cnki-001 ~ cnki-N），彻底消除 ID 冲突

---

## Step 4: 下载 PDF（需机构IP）

```bash
# 首次下载（全新任务）
python3 scripts/cnki_download.py \
  --input ./literature-review/search/candidates.json \
  --workspace ./literature-review \
  --delay 5

# 已确认当前网络无需登录/验证码时，跳过首页等待
python3 scripts/cnki_download.py \
  --input ./literature-review/search/candidates.json \
  --workspace ./literature-review \
  --delay 5 \
  --manual-wait 0

# 详情页可能触发验证码时，跳过首页等待，但允许验证码页人工处理
python3 scripts/cnki_download.py \
  --input ./literature-review/search/candidates.json \
  --workspace ./literature-review \
  --delay 5 \
  --manual-wait 0 \
  --verify-wait 120

# 如果重新筛选后 ID 变化，建议加 --clean 清理旧文件避免残留
python3 scripts/cnki_download.py \
  --input ./literature-review/search/candidates.json \
  --workspace ./literature-review \
  --delay 5 --clean
```

行为：
1. 读取 `selected: true` 的文献
2. **ID 重复检查**：若存在重复 ID，直接报错退出，提示重新运行 `curate.py`
3. 打开知网首页，根据 `--manual-wait` 等待机构认证/验证码；已确认无需认证时设为 `--manual-wait 0`
4. 逐篇打开详情页，点击 PDF 下载按钮
5. 保存至 `papers/pdf/` → 命名 `cnki-XXX.pdf`（curate.py 已确保 ID 唯一）
6. **缓存复用**：若 PDF 已存在且有效，标记 `cached` 跳过下载（多次运行共用同一 PDF）
7. `--clean`：下载前清理旧的 PDF/meta/text 文件，避免 ID 重新分配后残留旧文件
8. 若详情页触发验证码/安全验证，等待 `--verify-wait` 秒，人工处理后重新打开原始文章 URL；点击 PDF 后若先跳转到验证码页，脚本会停止等待下载事件，验证通过后重新打开原始文章 URL 再点击下载
9. 若详情页、点击下载后的当前页或新开页面出现明确付费提示，跳转到 CNKI `/bar/fee_*.html` 付费页，正文出现「选择下载方式」+「单篇下载/仅下载本文/价格/开通会员」等付费页组合信号，或进入 CNKI `a.cnki.net/gw/api/get/pdf/ads/` 占位 PDF，标记为 `paid` 并从候选列表中追加未选文献作为替补；页脚/导航中的「充值中心」等通用入口不作为付费依据。识别到付费页后不再继续点击页面上的 PDF/广告 PDF 入口，也不会重试这篇付费文献。
10. 批量结束后，对普通失败文献按 `--retry-failed` 再重试，适合验证码处理后补下载
11. 若浏览器页面、context 或 browser 被 CNKI 弹窗/用户操作关闭，脚本会重新打开浏览器会话并原地重试当前文献一次
12. 更新 meta JSON，失败不中断；若未找到 PDF 下载按钮，保存页面 HTML 和截图到 `logs/download-debug/`

参数建议：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--manual-wait` | 60 | 仅用于打开知网首页后的机构认证等待；确认无需首页认证时设 0 |
| `--verify-wait` | 120 | 详情页出现验证码/安全验证时的等待秒数；脚本会用 URL、页面标题和正文综合判断验证是否完成 |
| `--retry-failed` | 1 | 批量结束后重试普通失败文献的轮数 |
| `--no-replace-paid` | false | 遇到付费下载页时不追加替补文献 |
| `--headless` | false | 无界面运行；CNKI 可能返回空白页，只适合已确认可用且无需人工处理登录、验证码或机构认证的环境 |
| `--delay` | 5 | 篇间等待秒数，避免触发风控 |

**下载前务必确认：** 访问 https://www.cnki.net 显示机构名称（如「XX大学图书馆」）。

`--manual-wait` 不负责详情页验证码，它只是在知网首页停留，方便确认机构 IP 或完成首页弹窗。某篇详情页中途弹出验证码时，不要停止脚本；在可见浏览器中完成验证，脚本会在 `--verify-wait` 内优先检测文章内容或 PDF 下载入口是否出现，并结合 URL、标题和正文判断是否仍在验证页，不会因为验证码页文字短暂变化就立刻重进详情页。若点击 PDF 后进入验证码，脚本会先退出下载事件等待，验证通过后再重新点击 PDF，避免验证完成后仍等待下载事件超时。若验证处理较晚，脚本还会在批量结束后按 `--retry-failed` 重试普通失败项。

如果某篇页面明确提示「付费下载」「购买」「余额不足」等，脚本会将该篇作为终态跳过，不放入重试队列，并从 `candidates.json` 中的未选文献追加替补；补位文献会分配新的 `cnki-XXX` ID，并保留 `original_id`。若某篇在普通失败重试阶段才被识别为付费，仍会触发候选池补位，并继续处理新补入文献。

如果某篇失败并提示「未找到 PDF 下载按钮」，优先查看 `logs/download-debug/{id}_*.png` 和对应 HTML，判断是无 PDF 入口、CAJ-only、权限/登录页，还是页面结构需要补充选择器。

---

## Step 5: 提取 PDF 全文

```bash
python3 scripts/extract_pdf_text.py --workspace ./literature-review
```

- 输入：`papers/pdf/cnki-XXX.pdf`
- 输出：`papers/text/cnki-XXX.txt`
- 扫描版 PDF 标记 `ocr_needed: true`

**为什么需要 txt？** Read 工具无法直接读取 PDF 二进制文件，必须先用 pymupdf 提取为纯文本才能供后续通读和摘要生成。这不是多余步骤，而是工具链的必要中转。

---

## Step 6: 单篇结构化摘要

对每篇已成功提取全文的文献，**必须逐篇通读全文后**生成摘要。

### 摘要模板

```markdown
# [论文标题]

## 基本信息
- 作者 / 来源 / 年份
- 研究对象与方法

## 研究问题
[1-2句概括核心研究问题]

## 核心观点与结论
- ...
- ...

## 研究方法
- ...

## 创新点
- ...

## 与本调研主题的关联
[说明为何纳入、贡献什么证据]
```

### 批量生成策略

由于单次对话 token 限制，建议分多轮读取：
1. **首轮**：批量读取 5-6 篇全文，生成对应摘要
2. **循环**：重复直到所有论文摘要完成
3. 摘要格式保持严格一致，确保后续综述可引用

---

## Step 7: 综合文献综述

读取所有 summaries，生成最终综述。**必须基于已读全文的真实内容，不得编造。**

### 综述结构

```markdown
# [主题] 文献综述

## 1. 调研说明
检索策略、数据库、时间范围、纳入/排除标准、最终篇数

## 2. 研究脉络
按主题/方法/时间线梳理演进（归纳 3-4 条主要脉络）

## 3. 主要研究发现（分主题）
### 3.1 ...
### 3.2 ...

## 4. 研究方法对比
| 序号 | 作者(年) | 研究对象 | 方法 | 主要结论 | 期刊 |
|------|----------|----------|------|----------|------|

## 5. 研究空白与争议

## 6. 对本研究的启示

## 参考文献
[GB/T 7714 格式列表]
```

---

## 浏览器模式选择指南

| 场景 | 推荐工具 | 原因 |
|------|----------|------|
| 自动批量检索+解析 | Playwright 脚本 | 结构化数据提取效率高 |
| 知网页面反爬/验证码 | Playwright `headless=false` | 可人工介入完成验证 |
| 交互式浏览/手动筛选 | agent-browser | snapshot + click 更直观 |
| PDF 批量下载 | Playwright 脚本 | 自动 expect_download |
| agent-browser 未安装 | Playwright 脚本 | 兜底方案 |

---

## 依赖安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright pymupdf
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright python3 -m playwright install chromium

# 可选：交互式浏览器
npm --registry=https://registry.npmmirror.com i -g agent-browser
# 或: brew install agent-browser
```

---

## 常见注意事项

| 阶段 | 常见问题 | 处理方式 |
|------|----------|------------|
| 搜索 | DOM 选择器 `page.locator("td.name")` 解析失败 | `page.evaluate()` 直接提取 `td.textContent` |
| 去重 | 单关键词覆盖不足，可能混入 K-12 噪声 | 使用多组关键词检索、去重，并启用 K-12 过滤 |
| 筛选 | 人工逐条判断耗时 | 使用期刊白名单 + 主题关键词双维度自动打分 |
| 筛选 | 筛选后多篇论文共享同一 ID（如 cnki-005），下载时互相覆盖 | `curate.py` 筛选后自动重新分配唯一 ID（cnki-001~cnki-N） |
| 下载 | ID 冲突导致部分 PDF 覆盖 | `cnki_download.py` 启动时检测重复 ID 并报错，`--clean` 清理旧文件 |
| 下载 | 多次任务下载同一篇文献重复浪费 | 缓存机制：已存在的有效 PDF 标记 `cached` 跳过下载 |
| 提取 | 不知道为什么要生成 txt 中间文件 | Read 工具只能读纯文本，PDF→txt 是必要中转 |
| 摘要 | 未读全文编造摘要 | 逐篇通读后按模板结构化生成 |

---

## 合规提醒

- 仅用于个人学习与研究，遵守知网与机构使用协议
- 控制下载频率（`--delay` ≥ 5），勿批量爬取
- 引用时注明出处，综述中列出完整参考文献
