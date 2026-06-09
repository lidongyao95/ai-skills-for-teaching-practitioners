# 贡献指南

欢迎为本项目贡献技能！以下是贡献前需要了解的规范。

## 技能命名规范

```
<english-name-with-hyphens>
```

- 全小写英文字母
- 单词间用 `-` 连接
- 名称应直接体现代码所做的事

例如：`generate-teaching-html`、`teaching-html-formula-encoding`

## SKILL.md 格式要求

每个技能遵循 Trae SKILL.md 格式，必须包含以下 YAML 前端元数据：

```yaml
---
name: <技能名，小写+连字符，≤64字符>
description: <简要描述，≤1024字符>
---
# 技能名称

## 描述
描述这个技能的作用

## 使用场景
描述触发这个技能的条件

## 指令
清晰的分步说明，告诉智能体具体怎么做

## 踩坑点（推荐）
常见的错误和解决方案
```

## 内容规范

1. **语言** — 中文编写（受众为高校教学实践人员）
2. **工具** — 仅使用 Trae Solo
3. **网络环境约束** — 所有命令示例中：
   - Python 包安装必须使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>` 或 `pip install -i https://mirrors.aliyun.com/pypi/simple <package>`
   - CDN 资源优先使用国内节点：`bootcdn.cn`（主选）、`cdn.jsdelivr.net/npm`（备选）、`cdnjs.cloudflare.com`（最后回退）
   - 禁止使用需要科学上网才能访问的外部 API 或在线服务
   - GitHub 连接（`git clone`、`push`、`pull`）不受此限
4. **踩坑点** — 每个技能必须包含踩坑点，标注技术陷阱、平台适配问题
5. **自包含** — 每个技能独立完整，不依赖其他技能的内部细节
6. **成果导向** — 每个技能必须产出可用的交付物（HTML 文件、脚本等）

## 文件组织

```
skills/
├── <skill-name>/
│   ├── SKILL.md          # 技能正文（必须）
│   ├── scripts/          # 辅助脚本（可选）
│   ├── references/       # 参考资料（可选）
│   ├── examples/         # 示例输出（可选）
│   └── templates/        # 可复用模板（可选）
```

## 验证

提交前运行验证脚本：

```bash
python scripts/validate-skills.py
```

## PR 流程

1. Fork 本仓库
2. 创建分支：`feat/<skill-name>`
3. 添加 SKILL.md 及相关文件
4. 运行验证脚本确保通过
5. 提交 PR，说明技能的目标受众和适用场景

## 许可

贡献的内容默认采用 MIT 协议。
