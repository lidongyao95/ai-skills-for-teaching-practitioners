---
name: teaching-html-formula-encoding
description: 诊断并修复教学 HTML 页面中的公式乱码问题。覆盖编码层、CDN 层、渲染引擎层、字体层和特殊符号五个层面，提供自上而下的系统排查流程。
---
# 教学 HTML 公式编码诊断

## 描述

当教学 HTML 页面中的数学/化学公式出现乱码、方块、LaTeX 源码残留、部分符号不显示等问题时，使用本技能进行系统诊断和修复。本技能建立了从底层编码到顶层渲染的完整排查链，涵盖 UTF-8/GBK 编码冲突、CDN 资源加载失败、KaTeX/MathJax 渲染引擎故障、mhchem 扩展缺失、中文字体与数学字体冲突，以及 ∀∃∈→ 等 Unicode 特殊符号不显示五类典型问题。

**核心定位：不是教你写公式，而是教你把写出公式后出问题的页面修好。**

## 使用场景

- 教师打开 HTML 教学页面，数学公式显示为乱码或方块
- 页面中 LaTeX 源码直接暴露（如 `\frac{a}{b}` 而不是渲染后的分数）
- 化学方程式不渲染，仅显示 `\ce{H2O}` 等源码
- 部分特殊符号（∀ ∃ ∈ → ∪ ∩）显示为空白或问号
- 中文内容正常但公式部分完全不可见
- CDN 资源在国内网络环境下加载超时或失败
- 同一个页面在 A 电脑正常、B 电脑乱码

## 指令

### 1. 自上而下的排查流程

按以下顺序逐层排查，**上层问题必须优先解决**，因为下层依赖上层正常工作：

```
第一层：编码层
  ↓
第二层：CDN 资源加载层
  ↓
第三层：渲染引擎层
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

### 3. 第二层 — CDN 资源加载层诊断

**目标**：确认 KaTeX/MathJax 的 CSS 和 JS 文件成功从 CDN 加载。

检查步骤：

1. 浏览器 F12 → Network 标签 → 刷新页面
2. 筛选 CSS 和 JS 文件，查找 katex、mathjax、mhchem 等关键词
3. 检查是否有状态码为 404（未找到）、403（被屏蔽）、或长时间 pending（超时）的请求
4. 检查 Console 中是否有 "Failed to load resource" 或 CORS 相关错误
5. 在 Console 中执行 `typeof katex` 和 `typeof renderMathInElement`，如果返回 `"undefined"` 说明 KaTeX 未加载成功

修复方案：

- **CDN 不可达**：将 CDN 域名切换到国内可访问的源。优先级：bootcdn.cn > jsdelivr.net > cdnjs（国内部分地区 cdnjs 被限速）
- **版本号过期**：检查 CDN URL 中的版本号是否有效；KaTeX 当前稳定版为 0.16.9
- **缺少 fallback**：每个 `<script>` 和 `<link>` 标签应添加 `onerror` 回退逻辑

```html
<!-- 带 fallback 的 KaTeX 加载示例 -->
<link rel="stylesheet"
      href="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.9/katex.min.css"
      onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'">
<script src="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.9/katex.min.js"
        onerror="var s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';document.head.appendChild(s);">
</script>
```

- **HTTPS 混用**：如果页面通过 HTTPS 访问，CDN 资源也必须使用 HTTPS，否则浏览器会拦截

### 4. 第三层 — 渲染引擎层诊断

**目标**：确认 KaTeX/MathJax 正确初始化，`auto-render` 扩展被调用，且化学宏包 mhchem 已加载。

检查步骤：

1. Console 执行 `typeof renderMathInElement`，若为 `"function"` 则 auto-render 已加载
2. 搜索页面源码，确认存在 `renderMathInElement(document.body)` 或等效调用
3. 确认渲染调用在 DOM 渲染完毕之后执行（放在 `DOMContentLoaded` 事件中或 `<script>` 放在 `</body>` 之前）
4. 如果使用了化学公式 `\ce{...}`，检查是否加载了 `mhchem.min.js`
5. Console 执行 `katex.renderToString("\\ce{H2O}")`，如果报错 "KaTeX parse error: Undefined control sequence: \ce" 则 mhchem 未加载

修复方案：

- **auto-render 未调用或调用时机错误**：

```javascript
document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
        delimiters: [
            {left: "$$", right: "$$", display: true},
            {left: "$", right: "$", display: false},
            {left: "\\[", right: "\\]", display: true},
            {left: "\\(", right: "\\)", display: false}
        ],
        throwOnError: false  // 防止单个公式错误导致全部不渲染
    });
});
```

- **mhchem 扩展缺失**：在 KaTeX 主脚本之后加载：

```html
<script src="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.9/contrib/mhchem.min.js"
        onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/mhchem.min.js'">
</script>
```

- **公式内有 DOM 注入的 HTML 标签**：如果公式经过后端模板引擎（如 Jinja2、PHP）输出，检查 `{{ }}` `{% %}` 等模板语法是否被错误转义

- **公式本身没有任何定界符包裹（最常见！）**：LaTeX 公式必须用 `$$...$$`（块级）或 `$...$`（行内）包裹才能被 KaTeX 识别。如果 HTML 中直接写了裸露的 LaTeX 源码（如 `<div>\displaystyle \frac{a}{b}</div>`），KaTeX 不会渲染它。用以下方法排查：
  1. 右键 → 查看页面源代码，搜索 `\frac`、`\displaystyle` 等 LaTeX 命令
  2. 检查这些命令是否被 `$$` 或 `$` 包裹
  3. 如果没有包裹：给公式加上 `$$...$$`（块级公式）或 `$...$`（行内公式）
  4. 如果已经有包裹但仍不渲染：检查定界符是否被 HTML 转义（如 `&amp;dollar;` 代替 `$`）
  5. 检查 `renderMathInElement` 配置中的 `delimiters` 是否包含 `{left: "$$", right: "$$", display: true}` 这一项

### 5. 第四层 — 字体层诊断

**目标**：解决中文字体与数学字体冲突，以及 KaTeX 字体文件加载失败导致的公式区域空白。

检查步骤：

1. F12 → Elements → Computed 标签 → 选中公式元素 → 查看实际生效的 `font-family`
2. Network 标签筛选 woff/woff2/ttf，检查 KaTeX 字体文件是否成功加载
3. 如果页面自定义了全局 CSS 字体，确认未覆盖 KaTeX 的 `.katex` 类字体设置

修复方案：

- **中文字体与数学字体冲突**：确保 KaTeX 的字体声明优先级最高，不要用通配符或全局选择器覆盖 `.katex` 的 font-family：

```css
/* 不要这样做 */
* { font-family: "Microsoft YaHei" !important; }

/* 应该分别设置 */
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
/* .katex 使用自己的字体，不覆盖 */
```

- **KaTeX 字体文件加载失败**：如果 Network 中 KaTeX 字体文件返回 404，说明 CDN 链接有误或版本不匹配。检查 katex.min.css 中的 `@font-face` 引用的字体路径是否可访问。如果字体路径是相对路径，确保 CSS 文件和字体文件在同一 CDN 域名下。

- **本地打包时字体缺失**：如果用户将 KaTeX 下载到本地使用，确保 `fonts/` 目录与 `katex.min.css` 在同一层级：

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
3. 如果是 LaTeX 命令且 KaTeX 正常渲染，检查符号是否在 KaTeX 支持列表中（绝大多数标准 LaTeX 数学符号都支持）

修复方案：

- **优先用 LaTeX 命令而非 Unicode 字符**：KaTeX 渲染的数学符号使用专用数学字体，比系统 Unicode 字体更可靠且美观一致：

```
错误做法：<p>对于任意 ε > 0，存在 δ > 0</p>
正确做法：<p>对于任意 $\varepsilon > 0$，存在 $\delta > 0$</p>
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
    console.log("2. KaTeX 加载:", typeof katex !== "undefined" ? "✅ 已加载" : "❌ 未加载");
    console.log("3. auto-render:", typeof renderMathInElement !== "undefined" ? "✅ 已加载" : "❌ 未加载");
    console.log("4. mhchem:", (typeof katex !== "undefined" && typeof katex.__parse === "function") ? "检查 renderMathInElement 配置" : "❌ KaTeX 本身未加载");
    console.log("5. meta charset:", document.querySelector('meta[charset]')?.outerHTML || "❌ 未找到");
    console.log("6. 页面公式数量:", document.querySelectorAll('.katex').length);
})();
```

### 8. 输出验证清单

修复完成后，逐项确认：

- [ ] 页面刷新后 Console 无报错
- [ ] 所有公式正常渲染，无 LaTeX 源码残留
- [ ] 化学方程式（如有）正常显示
- [ ] 中文内容无乱码
- [ ] 特殊符号（∀∃∈→∪∩⊂∞）正常显示
- [ ] 在不同浏览器（Chrome、Edge、Firefox）中表现一致
- [ ] 在隐身模式/无缓存模式下也能正常加载

## 踩坑点

| 问题 | 原因 | 解决 |
|------|------|------|
|| 公式显示为 LaTeX 源码（如裸 `\frac{a}{b}` 显示在页面上） | 公式没有被 `$$` 或 `$` 定界符包裹 | 用 `$$...$$` 包裹块级公式，用 `$...$` 包裹行内公式；检查 `renderMathInElement` 的 delimiters 配置 |
|| 公式有 `$$` 包裹但仍显示为源码 | `renderMathInElement` 未调用、调用时 DOM 未就绪、或 `<script>` 标签顺序错误 | 将渲染调用放入 `DOMContentLoaded`；确保 KaTeX JS 在 CSS 之后、渲染调用在两者之后 |
|| `\displaystyle` 等显示为普通文本 | 公式缺少 `$$` 包裹（`\displaystyle` 是 LaTeX 命令必须在数学环境内） | 将整个公式用 `$$...$$` 包裹；单行公式如 `$a^2+b^2=c^2$` 用 `$...$` |
| `\ce{H2O}` 不渲染 | 未加载 mhchem 扩展 | 在 KaTeX 主脚本后加载 `contrib/mhchem.min.js` |
| 中文乱码、公式也乱码 | 文件编码是 GBK 但 `<meta charset="UTF-8">` | 用 VS Code 或 iconv 将文件转为 UTF-8 without BOM |
| `<meta charset>` 正确但仍有乱码 | `<meta>` 不在 `<head>` 的第一个位置，浏览器在读到编码声明前已按错误编码开始解析 | 将 `<meta charset="UTF-8">` 放在 `<head>` 下的第一行 |
| Windows 记事本保存后公式前出现乱码 | 记事本默认保存为 UTF-8 with BOM，BOM 字符被渲染 | 用专业编辑器保存为 UTF-8 without BOM |
| CDN 资源 403/超时 | 当前 CDN 域名在国内被墙或限速 | 切换到 bootcdn.cn；确保 `<script>` 设置了 `onerror` fallback |
| KaTeX 字体文件 404 | 字体 CSS 路径与 CDN 版本不匹配 | 确保 katex.min.css 与字体文件使用相同 CDN 和相同版本号 |
| 部分符号（∀∃∈）显示为方框 | 直接使用了 Unicode 字符，系统字体缺失对应字形 | 改用 LaTeX 命令（`\forall` `\exists` `\in`），让 KaTeX 用数学字体渲染 |
| Console 报 "katex is not defined" | KaTeX JS 未从 CDN 成功加载 | 检查 Network 标签，确定是 404（URL 错误）还是超时（CDN 不可达），更换 CDN |
| 公式渲染了但位置/大小异常 | 自定义 CSS 覆盖了 `.katex` 的样式 | 检查全局 CSS 中是否有 `!important` 覆盖了 KaTeX 的字体或间距设置 |
| 同一页面 A 电脑正常 B 乱码 | A/B 电脑浏览器默认编码不同；或 A 电脑有缓存 | 确保 `<meta charset="UTF-8">` 且文件本身为 UTF-8；B 电脑清缓存后重试 |
