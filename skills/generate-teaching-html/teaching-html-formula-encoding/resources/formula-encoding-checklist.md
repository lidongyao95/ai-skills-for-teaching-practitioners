# 教学 HTML 公式编码故障排查清单

> 使用方法：对照左侧现象找到匹配行，按"检查方法"逐项验证，执行对应"修复方案"。排查顺序自上而下。

| 现象/截图描述 | 可能原因 | 检查方法 | 修复方案 |
|-------------|---------|---------|---------|
| 整个页面中文和公式全部乱码 | 文件为 GBK 编码但声明 UTF-8 | F12 → Console 看 `document.characterSet`；或用 `file` 命令查文件编码 | `iconv -f GBK -t UTF-8 old.html -o new.html`；或 VS Code 右下角改编码保存 |
| 中文正常但公式区域全是乱码/方块 | `<meta charset>` 位置太靠后，浏览器提前误判编码 | F12 → Elements 查看 `<head>` 第一行是否 `<meta charset>` | 将 `<meta charset="UTF-8">` 移到 `<head>` 下第一行，在 `<title>` 之前 |
| 公式前出现 "﻿" 或意外空白字符 | UTF-8 with BOM 被浏览器渲染 | 用 `xxd page.html \| head -3` 查看文件头是否 `EF BB BF` | VS Code → 保存为 "UTF-8 without BOM"；或 `sed -i '1s/^\xEF\xBB\xBF//' page.html` |
| 所有公式显示为 LaTeX 源码（如 `\frac{a}{b}`） | 最终 HTML 中残留 LaTeX，浏览器不会自动渲染 | 用 `\\[a-zA-Z]+` 搜索所有 LaTeX 命令 | 改写为 MathML、HTML/CSS、Unicode 上下标或内联 SVG |
| 表格（`<td>`）、列表（`<li>`）中的 `\nabla\times\mathbf{E} = -\frac{\partial\mathbf{B}}{\partial t}` 等公式显示为纯文本 | 表格/列表中仍使用 LaTeX 源码 | 用 `\\[a-zA-Z]+` 搜索所有 LaTeX 命令，不限位置 | 在对应单元格或列表项中改用 `<span class="formula">`、MathML 或 SVG |
| 页面加载后公式闪现 LaTeX 源码然后消失 | 仍依赖运行时公式渲染器，首屏不是最终结构 | 检查是否存在 MathJax/KaTeX 初始化代码 | 默认删除渲染器依赖，把公式写成浏览器可直接显示的结构 |
| Console 报 "Failed to load resource" 且公式不显示 | 仍有远程资源或本地资源路径错误 | F12 → Network → 刷新，筛选 JS/CSS/font/image | 删除远程资源并内嵌；本地文件路径错误时改为 `data:` URI 或同目录相对路径 |
| 公式区域完全空白，无任何报错 | 字体缺失、容器被隐藏、或 SVG/MathML 样式错误 | F12 → Elements 查看公式节点和实际 CSS | 使用系统数学字体栈；检查 `.formula`、`math`、`svg` 样式和容器可见性 |
| 化学公式 `\ce{...}` 显示为源码 | `\ce` 是 LaTeX/mhchem 语法，不是 HTML | 搜索 `\ce` | 改写为 `H<sub>2</sub>O`、`Fe<sup>2+</sup>` 等 HTML 结构 |
| ∀ ∃ ∈ → ∪ ∩ ⊂ ∞ 等符号显示为方框 | 直接写入了 Unicode 字符，系统缺对应字体 | 检查 HTML 源码是 Unicode、HTML 实体还是 MathML | 改用 HTML 实体、MathML，或为 `.formula` 指定包含数学符号的本地字体栈 |
| 公式字体与中文正文字体不协调（过大/过小/间距乱） | 全局 CSS 覆盖了 `.formula`、`math` 或 SVG 的默认字体样式 | F12 → Elements → Computed → 选中公式元素查看 font-family | 删除全局 `* { font-family: ... }` 样式；单独设置 `.formula, math` 字体栈 |
| HTTP 响应头 `Content-Type: text/html` 无 charset | Web 服务器未声明编码 | F12 → Network → 点击页面请求 → Response Headers | Nginx: `charset utf-8;`；Apache: `AddDefaultCharset UTF-8` |
| Console 报 "katex is not defined" | 页面仍依赖未内嵌的 KaTeX 脚本 | 搜索 `katex`、`renderMathInElement`、`script src` | 默认删除 KaTeX 依赖并改写公式；确需使用时内嵌本地 KaTeX 全量资源 |
| 页面依赖 `renderMathInElement` 才能显示公式 | 仍使用公式库运行时渲染 | 检查 JS 中的渲染调用 | 把公式改为 MathML、HTML/CSS、Unicode 或内联 SVG |
| 打开控制台看到 "Mixed Content" 警告 | 页面仍加载外部 HTTP 资源 | F12 → Console 筛选 "Mixed Content" | 删除外部资源，改为内嵌或本地化 |
| 公式内部出现 HTML 标签字符（如 `&lt;` `&gt;`） | 后端模板引擎（Jinja2/PHP）转义了 LaTeX 代码 | 查看页面源码中公式部分是否被 HTML 实体编码 | 后端输出公式时使用 `safe`（Jinja2）或关闭对应区域的转义 |
| 同一页面 A 电脑正常，B 电脑乱码 | B 电脑浏览器默认编码为 GB18030/其他 | B 电脑 F12 → Console → `document.characterSet` | 确保 `<meta charset="UTF-8">` 在 `<head>` 第一行；B 电脑清除浏览器缓存 |
| 复杂公式显示不完整 | HTML/CSS 或 MathML 结构写错 | 检查公式节点的标签闭合、上下标和分式结构 | 修正结构；过复杂时改用内联 SVG 绘制 |
| 公式闪烁后变成兜底字体显示 | 仍有运行时渲染或远程字体依赖 | Network 筛选 font，Console 查看报错 | 使用系统字体栈或内嵌字体；避免运行时远程加载 |
