# AI Skills for Teaching Practitioners

为高校实践教学人员定制的 AI 技能资源库。

## 项目定位

本项目专为高校行政人员、辅导员、教师等**非编程背景**教学实践者设计。每个 "skill" 是一个可独立使用、半日可完成的实训模块，产出可直接用于实际工作的成果物。

## 核心理念

- **实用第一** — 每个技能解决一个真实工作痛点，产出可带走的工作成果
- **零门槛** — 无需编程基础，从真实场景切入
- **工具生态** — 使用 Trae Solo 作为 AI 工具（不使用 Coze 或其他 Agent 平台）
- **自包含** — 每个 SKILL.md 独立完整，不依赖其他技能
- **可组合** — 技能可按需组合成不同时长的培训课程
- **网络环境约束** — 所有 AI 执行任务不得要求学习者配置翻墙工具。连接 GitHub（git clone、push、pull）不受此限。所有命令行中的 Python 包安装、Node 包安装等环境依赖，必须指定国内镜像源（清华 TUNA 或阿里云）。CDN 资源优先使用国内节点（bootcdn.cn、jsdelivr.net）。禁止使用需要科学上网才能访问的外部 API 或在线服务。

## 项目结构

```
ai-skills-for-teaching-practitioners/
├── README.md               ← 本文件：项目总览
├── CONTRIBUTING.md         ← 贡献指南
├── LICENSE                 ← 开源许可
├── .gitignore
│
├── skills/                 ← 核心：所有 SKILL.md 技能文件
│   ├── cnki-literature-review/         ── 知网文献调研：多关键词检索、PDF下载、全文提取、智能筛选与结构化综述（v2）
│   └── generate-teaching-html/         ── 教学演示 HTML 生成（含公式编码诊断子 skill）
│
├── templates/              ← SKILL.md 模板文件
├── scripts/                ← 验证、构建辅助脚本
├── references/             ← 参考资料（工具文档摘要、最佳实践）
├── examples/               ← 示例技能（完整参考实现）
└── .github/                ← GitHub 模板（Issue/PR）
```

## 快速开始

```bash
# 查看所有可用技能
ls skills/*/

# 阅读某个技能
cat skills/generate-teaching-html/SKILL.md
```

## Skill 格式

每个技能遵循 Trae SKILL.md 格式：

```yaml
---
name: skill-name
description: 简要描述这个技能的功能和使用场景
---
# 技能名称

## 描述
描述这个技能的作用

## 使用场景
描述触发这个技能的条件

## 指令
清晰的分步说明，告诉智能体具体怎么做
```

详见 [templates/SKILL.md](templates/SKILL.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT
