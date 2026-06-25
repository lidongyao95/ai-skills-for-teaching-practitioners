---
name: teaching-html-formula-encoding
description: 诊断并修复教学 HTML 页面中的公式乱码问题。覆盖编码层、本地资源层、公式结构层、字体层和特殊符号五个层面，提供自上而下的系统排查流程，禁止使用 CDN 或任何网络资源。
---
# 教学 HTML 公式编码诊断

## 描述

当教学 HTML 页面中的数学/化学公式出现乱码、方块、LaTeX 源码残留、部分符号不显示等问题时，使用本技能进行系统诊断和修复。本技能建立了从底层编码到顶层显示的完整排查链，涵盖 UTF-8/GBK 编码冲突、外部网络资源残留、本地资源缺失、公式结构错误、中文字体与数学字体冲突，以及 ∀∃∈→ 等 Unicode 特殊符号不显示五类典型问题。

**核心定位：不是教你写公式，而是教你把写出公式后出问题的页面修好。**

## 使用场景

- 教师打开 HTML 教学页面，数学公式显示为乱码或方块
- 页面中 LaTeX 源码直接暴露（如 `\frac{a}{b}` 而不是渲染后的分数）
- 化学方程式不渲染，仅显示 `\ce{H2O}` 等源码
- 部分特殊符号（∀ ∃ ∈ → ∪ ∩）显示为空白或问号
- 中文内容正常但公式部分完全不可见
- 页面断网或通过 `file://` 打开时公式、样式、图片、字体丢失
- 同一个页面在 A 电脑正常、B 电脑乱码

## 指令

### 1. 自上而下的排查流程

按以下顺序逐层排查，**上层问题必须优先解决**，因为下层依赖上层正常工作：

```
第一层：编码层
  ↓
第二层：本地资源层
  ↓
第三层：公式结构层
  ↓
第四层：字体层
  ↓
第五层：特殊符号层
```

每一层排查通过后，刷新页面验证公式是否恢复正常。如果某层修复后问题仍在，继续向下一层排查。

### 2. 第一层 — 编码层诊断

**目标**：确保 HTML 文件本身是 UTF-8 编码，且页面声明与文件编码一致。

检查步骤：

1. 打开浏览器开发者工具（F12）→ Console，查看是否有 "encoding" 相关警告
2. 检查 HTML 文件 `<head>` 中是否包含 `<meta charset="UTF-8">`
3. 确认 `<meta charset>` 位于 `<head>` 的第一个子元素位置（在 `<title>` 之前），避免浏览器在读取编码声明前已按错误编码解析
4. 确认使用文本编辑器保存文件时编码为 **UTF-8 without BOM**（Windows 记事本默认保存的是带 BOM 的 UTF-8，可能导致公式开头出现乱码字符）
5. 如果使用了 Web 服务器（如 Nginx/Apache），检查 HTTP 响应头 `Content-Type` 是否包含 `charset=UTF-8`

修复方案：

```html
<head>
    <meta charset="UTF-8">
    <title>...</title>
    <!-- 其余内容 -->
</head>
```

如果文件已经是 GBK/GB2312 编码：
- 用 VS Code 打开 → 右下角点击编码 → "通过编码重新打开" → 选择 GB2312 → 再改为 "通过编码保存" → UTF-8
- 或用命令行：`iconv -f GBK -t UTF-8 input.html -o output.html`

### 3. 第二层 — 本地资源层诊断

**目标**：确认 HTML 产物没有任何网络依赖，所有资源都已内嵌或本地化。

检查步骤：

1. 浏览器 F12 → Network 标签 → 刷新页面
2. 勾选 Offline 或断开网络后刷新，确认页面仍完整显示
3. 搜索源码中的 `http://`、`https://`、`//cdn`、`<script src=`、`<link rel="stylesheet"`、`@import`、`fetch(`
4. 检查 Console 中是否有 "Failed to load resource"、CORS、字体加载失败或图片加载失败
5. 检查图片、音频、字体等是否为 `data:` URI 或用户确认的同目录相对本地文件

修复方案：

- **发现 CDN 或远程 URL**：删除远程引用，将 CSS/JS 直接内嵌进 `<style>` 和 `<script>`
- **发现远程图片/字体/音频**：转为 `data:` URI；如果资源过大，先征得用户同意再改为同目录相对本地文件
- **发现运行时网络请求**：删除 `fetch`、`XMLHttpRequest`、动态插入脚本等逻辑，改用 HTML 内置数据或本地内嵌数据

```html
<!-- 正确：样式和脚本内嵌，无网络依赖 -->
<style>
.formula { font-family: "Times New Roman", "Cambria Math", serif; }
</style>
<script>
var lessonData = [{ step: 1, title: "问题引入" }];
</script>
```

- **确需公式库**：只能使用用户提供或项目内已有的本地 MathJax/KaTeX，并完整内嵌所需 JS/CSS/字体；不得从网络加载。

### 4. 第三层 — 公式结构层诊断

**目标**：确认公式已经写成浏览器可直接显示的 MathML、HTML/CSS、Unicode 上下标或内联 SVG，而不是裸露 LaTeX 源码。

检查步骤：

1. 搜索源码中的 `\\[a-zA-Z]+`，检查是否有 `\frac`、`\sqrt`、`\ce`、`\begin` 等 LaTeX 命令残留
2. 检查复杂数学公式是否使用 `<math>`、`<mfrac>`、`<msqrt>`、`<msup>` 等 MathML 标签，或使用 `.frac` 等 HTML/CSS 组件表达
3. 检查行内短公式是否使用 `<span class="formula">`、`<sup>`、`<sub>`、Unicode 符号表达
4. 检查化学式是否使用 `<sub>`、`<sup>` 表达下标和电荷
5. 确认公式区域没有依赖 `renderMathInElement`、`MathJax.typesetPromise` 等在线渲染流程

修复方案：

- **裸 LaTeX 源码残留**：改写为 MathML、HTML/CSS、Unicode 或内联 SVG：

```html
<span class="formula">
  x =
  <span class="frac">
    <span class="num">-b &plusmn; &radic;(b<sup>2</sup> - 4ac)</span>
    <span class="den">2a</span>
  </span>
</span>
```

- **化学公式仍写作 `\ce{...}`**：改为普通 HTML 上下标：

```html
<span class="formula">HCl + NaOH &rarr; NaCl + H<sub>2</sub>O</span>
```

- **公式内有 DOM 注入的 HTML 标签**：如果公式经过后端模板引擎（如 Jinja2、PHP）输出，检查 `{{ }}` `{% %}` 等模板语法是否被错误转义

- **公式仍依赖定界符**：`$$...$$` 和 `$...$` 只适用于已内嵌公式渲染器的页面。默认离线模板不使用公式渲染器，必须改为浏览器可直接显示的结构。

### 5. 第四层 — 字体层诊断

**目标**：解决中文字体与数学字体冲突，以及本地字体/内嵌字体缺失导致的公式区域空白或方框。

检查步骤：

1. F12 → Elements → Computed 标签 → 选中公式元素 → 查看实际生效的 `font-family`
2. Network 标签筛选 woff/woff2/ttf，检查是否还有远程字体请求或本地字体 404
3. 如果页面自定义了全局 CSS 字体，确认未覆盖 `.formula`、`math` 或内联 SVG 的数学字体设置

修复方案：

- **中文字体与数学字体冲突**：不要用通配符或全局选择器覆盖公式区域的 font-family：

```css
/* 不要这样做 */
* { font-family: "Microsoft YaHei" !important; }

/* 应该分别设置 */
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
.formula, math { font-family: "Times New Roman", "Cambria Math", serif; }
```

- **字体文件加载失败**：如果 Network 中字体文件返回 404，说明本地路径有误或字体未内嵌。优先使用系统字体栈；确需自定义字体时，把字体转为 `data:` URI 并写入 `@font-face`。

- **本地打包时字体缺失**：如果用户明确要求使用本地 KaTeX/MathJax，确保 CSS、JS、字体都在同目录本地资源或已内嵌：

```
local/
├── katex.min.css
├── katex.min.js
├── contrib/
│   ├── auto-render.min.js
│   └── mhchem.min.js
└── fonts/
    ├── KaTeX_AMS-Regular.woff2
    ├── KaTeX_Main-Regular.woff2
    └── ...
```

### 6. 第五层 — 特殊符号层诊断

**目标**：修复 ∀（任意）、∃（存在）、∈（属于）、→（箭头）、∪（并集）、∩（交集）、⊂（子集）等 Unicode 数学符号显示为空白或方框的问题。

检查步骤：

1. 确认这些符号是通过 LaTeX 命令（如 `\forall` `\exists` `\in` `\to`）渲染还是直接以 Unicode 字符写入 HTML
2. 如果是 Unicode 字符直接写入，检查页面是否包含 `<meta charset="UTF-8">`（回到第一层）
3. 如果是 LaTeX 命令，改写为 MathML、HTML 实体、Unicode 或内联 SVG

修复方案：

- **优先用结构化 HTML/MathML，而非裸 LaTeX 命令**：默认离线页面不加载公式渲染器，LaTeX 命令会直接显示为源码：

```
错误做法：<p>对于任意 \varepsilon > 0，存在 \delta > 0</p>
正确做法：<p>对于任意 <span class="formula">&epsilon; &gt; 0</span>，存在 <span class="formula">&delta; &gt; 0</span></p>
```

- **如果必须使用 Unicode 字符**，在 CSS 中指定支持数学符号的字体栈：

```css
.math-unicode {
    font-family: "Cambria Math", "STIX Two Math", "Latin Modern Math", serif;
}
```

- **逻辑符号对照表**（LaTeX 命令 → Unicode 备用）：

| LaTeX | 符号 | Unicode |
|-------|------|---------|
| `\forall` | ∀ | U+2200 |
| `\exists` | ∃ | U+2203 |
| `\in` | ∈ | U+2208 |
| `\to` / `\rightarrow` | → | U+2192 |
| `\cup` | ∪ | U+222A |
| `\cap` | ∩ | U+2229 |
| `\subset` | ⊂ | U+2282 |
| `\infty` | ∞ | U+221E |

### 7. 快速诊断命令

在浏览器 Console 中执行以下诊断脚本，一键输出各层状态：

```javascript
(function() {
    console.log("=== 公式编码诊断 ===");
    console.log("1. 编码声明:", document.characterSet);
    console.log("2. 远程脚本数量:", document.querySelectorAll('script[src^=\"http\"], script[src^=\"//\"]').length);
    console.log("3. 远程样式数量:", document.querySelectorAll('link[href^=\"http\"], link[href^=\"//\"]').length);
    console.log("4. 远程媒体数量:", document.querySelectorAll('img[src^=\"http\"], audio[src^=\"http\"], video[src^=\"http\"]').length);
    console.log("5. meta charset:", document.querySelector('meta[charset]')?.outerHTML || "未找到");
    console.log("6. 公式元素数量:", document.querySelectorAll('.formula, .formula-block, math, svg[role=\"img\"]').length);
})();
```

### 8. 输出验证清单

修复完成后，逐项确认：

- [ ] 页面刷新后 Console 无报错
- [ ] 所有公式正常渲染，无 LaTeX 源码残留
- [ ] 化学方程式（如有）正常显示
- [ ] 中文内容无乱码
- [ ] 特殊符号（∀∃∈→∪∩⊂∞）正常显示
- [ ] 断网或 `file://` 打开时页面仍完整可用
- [ ] 源码中没有 `http://`、`https://`、CDN 域名、外部 `<script src>` 或外部 `<link href>`
- [ ] 在不同浏览器（Chrome、Edge、Firefox）中表现一致
- [ ] 在隐身模式/无缓存模式下也能正常加载

## 踩坑点

| 问题 | 原因 | 解决 |
|------|------|------|
|| 公式显示为 LaTeX 源码（如裸 `\frac{a}{b}` 显示在页面上） | 页面没有内嵌公式渲染器，浏览器不会自动识别 LaTeX | 改写为 MathML、HTML/CSS、Unicode 上下标或内联 SVG |
|| 公式有 `$$` 包裹但仍显示为源码 | `$$...$$` 只是公式渲染器定界符，不是浏览器原生语法 | 删除定界符，改成浏览器可直接显示的结构化公式 |
|| `\displaystyle` 等显示为普通文本 | LaTeX 命令残留在最终 HTML 中 | 改写为 MathML、HTML/CSS 分式、上下标或内联 SVG |
| `\ce{H2O}` 不渲染 | 未使用本地公式渲染器，且 `\ce` 不是 HTML 语法 | 改写为 `H<sub>2</sub>O` 等 HTML 结构 |
| 中文乱码、公式也乱码 | 文件编码是 GBK 但 `<meta charset="UTF-8">` | 用 VS Code 或 iconv 将文件转为 UTF-8 without BOM |
| `<meta charset>` 正确但仍有乱码 | `<meta>` 不在 `<head>` 的第一个位置，浏览器在读到编码声明前已按错误编码开始解析 | 将 `<meta charset="UTF-8">` 放在 `<head>` 下的第一行 |
| Windows 记事本保存后公式前出现乱码 | 记事本默认保存为 UTF-8 with BOM，BOM 字符被渲染 | 用专业编辑器保存为 UTF-8 without BOM |
| 断网后样式或公式消失 | 仍在使用 CDN、在线字体或远程脚本 | 删除所有远程资源，将 CSS/JS/字体/图片内嵌或本地化 |
| 字体文件 404 | 本地字体路径错误或字体未内嵌 | 优先使用系统字体栈；确需字体时转为 `data:` URI |
| 部分符号（∀∃∈）显示为方框 | 直接使用了 Unicode 字符，系统字体缺失对应字形 | 改用 HTML 实体、MathML，或为 `.formula` 指定包含数学符号的本地字体栈 |
| Console 报 "katex is not defined" | 页面仍依赖未内嵌的 KaTeX 脚本 | 默认删除 KaTeX 依赖并改写公式；若必须使用，内嵌本地 KaTeX 全量资源 |
| 公式渲染了但位置/大小异常 | 自定义 CSS 覆盖了 `.formula`、`math` 或 SVG 样式 | 检查全局 CSS 中是否有 `!important` 覆盖了公式字体或间距设置 |
| 同一页面 A 电脑正常 B 乱码 | A/B 电脑浏览器默认编码不同；或 A 电脑有缓存 | 确保 `<meta charset="UTF-8">` 且文件本身为 UTF-8；B 电脑清缓存后重试 |
