# 教学 HTML 公式编码故障排查清单

> 使用方法：对照左侧现象找到匹配行，按"检查方法"逐项验证，执行对应"修复方案"。排查顺序自上而下。

| 现象/截图描述 | 可能原因 | 检查方法 | 修复方案 |
|-------------|---------|---------|---------|
| 整个页面中文和公式全部乱码 | 文件为 GBK 编码但声明 UTF-8 | F12 → Console 看 `document.characterSet`；或用 `file` 命令查文件编码 | `iconv -f GBK -t UTF-8 old.html -o new.html`；或 VS Code 右下角改编码保存 |
| 中文正常但公式区域全是乱码/方块 | `<meta charset>` 位置太靠后，浏览器提前误判编码 | F12 → Elements 查看 `<head>` 第一行是否 `<meta charset>` | 将 `<meta charset="UTF-8">` 移到 `<head>` 下第一行，在 `<title>` 之前 |
| 公式前出现 "﻿" 或意外空白字符 | UTF-8 with BOM 被浏览器渲染 | 用 `xxd page.html \| head -3` 查看文件头是否 `EF BB BF` | VS Code → 保存为 "UTF-8 without BOM"；或 `sed -i '1s/^\xEF\xBB\xBF//' page.html` |
| 所有公式显示为 LaTeX 源码（如 `\frac{a}{b}`） | `renderMathInElement` 未调用或 KaTeX JS 未加载 | Console 执行 `typeof katex` 和 `typeof renderMathInElement` | 确保加载 `auto-render.min.js` 并在 `DOMContentLoaded` 中调用 `renderMathInElement` |
| 表格（`<td>`）、列表（`<li>`）中的 `\nabla\times\mathbf{E} = -\frac{\partial\mathbf{B}}{\partial t}` 等公式显示为纯文本 | 同一规则：任何 HTML 标签内的公式都需要 `$$` 或 `$` 定界符，KaTeX 不会因为公式在表格内就自动识别 | 用 `\\[a-zA-Z]+` 搜索所有 LaTeX 命令，不限位置 | 在 `<td>$$...$$</td>` 或 `<td>$...$</td>` 内包裹公式 |
| 页面加载后公式闪现 LaTeX 源码然后消失 | `renderMathInElement` 调用太晚（放 `window.onload` 而非 `DOMContentLoaded`） | 检查 JS 代码中的事件绑定 | 改用 `document.addEventListener("DOMContentLoaded", ...)` |
| Console 报 "Failed to load resource" 且公式不显示 | CDN 被墙或超时 | F12 → Network → 筛选 katex → 查看状态码和耗时 | 将 CDN 切到 bootcdn.cn；为每个 `<script>/<link>` 加 `onerror` fallback |
| 公式区域完全空白，无任何报错 | KaTeX 字体文件加载失败 | F12 → Network → 筛选 woff/woff2 → 检查字体文件状态码 | 确认 `fonts/` 目录与 CSS 在同一 CDN；检查 CSS 中 `@font-face` `src` 路径 |
| 化学公式 `\ce{...}` 显示为源码 | mhchem 扩展未加载 | Console 执行 `katex.renderToString("\\ce{H2O}")` → 报错即缺失 | 加载 `contrib/mhchem.min.js`；确保在 KaTeX 主 JS 之后加载 |
| ∀ ∃ ∈ → ∪ ∩ ⊂ ∞ 等符号显示为方框 | 直接写入了 Unicode 字符，系统缺对应字体 | 检查 HTML 源码是 `∀` 还是 `$\forall$` | 改用 LaTeX 命令 `$\forall$` `$\exists$` `$\to$` 让 KaTeX 渲染 |
| 公式字体与中文正文字体不协调（过大/过小/间距乱） | 全局 CSS 覆盖了 `.katex` 的默认字体样式 | F12 → Elements → Computed → 选中 `.katex` 元素 → 查看 font-family | 删除全局 `* { font-family: ... }` 样式；不覆盖 `.katex` 类 |
| HTTP 响应头 `Content-Type: text/html` 无 charset | Web 服务器未声明编码 | F12 → Network → 点击页面请求 → Response Headers | Nginx: `charset utf-8;`；Apache: `AddDefaultCharset UTF-8` |
| Console 报 "katex is not defined" | KaTeX 主脚本加载失败或加载顺序错 | Network 确认 `katex.min.js` 是否成功返回 | 检查 CDN URL 版本号（0.16.9）；确保 JS 在 CSS 之后加载 |
| `renderMathInElement` 不认 `\ce{}` 定界符 | auto-render 配置未包含 `\ce` 定界符 | 检查 `delimiters` 配置数组 | 添加 `{left: "\\ce{", right: "}", display: false}` 到 delimiters |
| 打开控制台看到 "Mixed Content" 警告 | HTTPS 页面加载 HTTP CDN 资源 | F12 → Console 筛选 "Mixed Content" | 将 CDN URL 统一改为 `https://` |
| 公式内部出现 HTML 标签字符（如 `&lt;` `&gt;`） | 后端模板引擎（Jinja2/PHP）转义了 LaTeX 代码 | 查看页面源码中公式部分是否被 HTML 实体编码 | 后端输出公式时使用 `safe`（Jinja2）或关闭对应区域的转义 |
| 同一页面 A 电脑正常，B 电脑乱码 | B 电脑浏览器默认编码为 GB18030/其他 | B 电脑 F12 → Console → `document.characterSet` | 确保 `<meta charset="UTF-8">` 在 `<head>` 第一行；B 电脑清除浏览器缓存 |
| KaTeX 渲染了但部分复杂公式报 "ParseError" | LaTeX 语法错误或使用了 KaTeX 不支持的宏 | Console 查看完整报错信息，定位具体公式 | 检查是否拼写错误（如 `\frec` 而非 `\frac`）；或改用 MathJax fallback |
| 公式闪烁后变成兜底字体显示 | KaTeX CSS 加载成功但 JS 未执行，浏览器按普通文本显示 | Console `typeof katex` → undefined | 检查 `katex.min.js` 的 `<script>` 标签是否正确且未被 `async`/`defer` 导致乱序 |
