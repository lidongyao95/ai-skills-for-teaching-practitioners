---
name: generate-teaching-html
description: 生成教学演示 HTML 页面。输出纯本地、自我包含的单 HTML 文件，讲解学科原理（而非仅展示结果），支持跨学科复用（数学、物理、化学、计算机），中文友好，公式渲染正确。生成后固定执行公式格式检查。
---
# 生成教学演示 HTML

## 描述

当用户需要为某个学科知识点创建交互式教学演示时，生成一个纯本地、自我包含的 HTML 文件。该文件通过内嵌的 CSS 和 JavaScript 实现分步讲解、公式渲染和交互控制，可在浏览器直接打开（file:// 协议），无需任何后端或构建工具。

**核心定位：讲解原理，不是展示效果。** 每个演示都应该展示推导过程、中间步骤和"为什么"，而不是只输出最终结果。

## 使用场景

- 教师需要讲解数学公式的推导过程（如一元二次方程求根公式）
- 教师需要可视化物理定律背后的原理（如牛顿第二定律 F=ma）
- 教师需要展示化学反应式的配平逻辑
- 教师需要演示算法执行步骤（如排序、搜索）
- 任何需要"分步骤讲解原理 + 交互操作"的教学场景

## 指令

### 1. 输出格式要求

生成一个 **完整的单 HTML 文件**，所有 CSS 和 JavaScript 内嵌在 `<style>` 和 `<script>` 标签中：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>教学演示：[主题]</title>
    <!-- 所有 CSS 内嵌 -->
    <style>/* ... */</style>
</head>
<body>
    <!-- 页面结构 -->
    <!-- 所有 JS 内嵌 -->
    <script>/* ... */</script>
</body>
</html>
```

### 2. 网络资源约束（严格）

所有外部资源必须使用国内可访问的 CDN，按以下优先级：

| 优先级 | CDN | 示例 URL |
|--------|-----|---------|
| 1（首选） | bootcdn.cn | `https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.9/katex.min.css` |
| 2（备选） | jsdelivr.net | `https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css` |
| 3（回退） | cdnjs | `https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css` |

每个外部资源必须提供至少两级 fallback 链接。示例：

```html
<link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.9/katex.min.css"
      onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'">
```

**禁止使用**：unpkg.com、googleapis.com 以及任何需要科学上网的域名。

### 3. 公式渲染引擎

使用 **MathJax 3 为主引擎**（功能最全，一行 `<script>` 引入即生效，无需手动配置 delimiters），KaTeX 作为备选（公式极多时更快）。

**MathJax 方案（默认）** — 最简单，覆盖所有 LaTeX 命令，通过内联配置确保行内公式和块级公式都能正确识别：

```html
<!-- MathJax 3：内联配置显式声明行内和块级定界符 -->
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']]
  }
};
</script>
<script src="https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js"
        onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'">
</script>
```

**关键：** `MathJax = { tex: { inlineMath: ... } }` 这个配置对象必须放在 `<script src="...mathjax...">` **之前**。MathJax 在加载时读取全局 `MathJax` 对象，如果 script 标签先于配置执行，配置会被忽略，导致行内公式 `$...$` 不能渲染，只显示源码。

MathJax 的优势：
- 不需要 `auto-render`，不需要手动调用渲染函数
- 不需要额外加载 `mhchem`，`\ce{}` 原生支持
- 支持 `\begin{aligned}`、`\begin{bmatrix}` 等所有 LaTeX 环境

**KaTeX 方案（备选）** — 当页面公式数量极大（>100 条）追求渲染速度时使用：

```html
<link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.10/katex.min.css"
      onerror="this.onerror=null;this.href='https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css'">
<script src="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.10/katex.min.js"
        onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js'"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.10/contrib/auto-render.min.js"
        onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/contrib/auto-render.min.js'"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/kaTeX/0.16.10/contrib/mhchem.min.js"
        onerror="this.onerror=null;this.src='https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/contrib/mhchem.min.js'"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
        delimiters: [
            {left: "$$", right: "$$", display: true},
            {left: "$", right: "$", display: false}
        ],
        throwOnError: false
    });
});
</script>
```

**选型指南：90% 场景直接用 MathJax。** 只有页面公式极多（题库、大量推导）才切换到 KaTeX。

### 4. 页面结构模板

```html
<body>
    <!-- 顶部标题栏 -->
    <header>
        <h1 id="topic-title">[学科] — [知识点名称]</h1>
        <p id="topic-subtitle">[一句话描述]</p>
    </header>

    <!-- 学科切换器（保留接口，不强制多学科） -->
    <nav id="discipline-nav" style="display:none;">
        <button data-discipline="math">数学</button>
        <button data-discipline="physics">物理</button>
        <button data-discipline="chemistry">化学</button>
        <button data-discipline="cs">计算机</button>
    </nav>

    <!-- 步骤导航 -->
    <div id="step-navigation">
        <button id="prev-step" disabled>&laquo; 上一步</button>
        <span id="step-indicator">步骤 1 / N</span>
        <button id="next-step">下一步 &raquo;</button>
    </div>

    <!-- 主内容区 -->
    <main id="content-area">
        <!-- 每个步骤一个 section -->
    </main>

    <!-- 公式展示区 -->
    <div id="formula-display"></div>

    <!-- 交互控制区（可选：参数滑块、按钮等） -->
    <div id="interactive-controls"></div>

    <!-- 底部信息 -->
    <footer>
        <p>生成工具：Trae Solo | 可离线使用</p>
    </footer>
</body>
```

### 5. 公式的正确编写方式

**标题中不放公式。** `<h1>` ~ `<h6>` 标题只写纯文字标题，公式放在标题下方的 `<p>` 或 `<div>` 中。标题内嵌公式会导致渲染引擎来不及处理、屏幕阅读器无法朗读、搜索引擎无法索引。

KaTeX 通过扫描页面中的 **定界符**（delimiter）来识别哪些内容是公式。MathJax 也是同样原理。编写 HTML 时，每个公式需要被定界符包裹，渲染引擎才能识别它。

| 公式类型 | 写法 | 效果 |
|----------|------|------|
| 块级公式（独立一行居中） | `<div class="formula-block">$$ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$</div>` | 公式独立成行、居中 |
| 行内公式（嵌在段落中） | `当 $a \neq 0$ 时，方程有解。` | 公式与文字同行 |
| 表格中的公式 | `<td>$$ \nabla\times\mathbf{E} = -\frac{\partial\mathbf{B}}{\partial t} $$</td>` | 单元格内公式正常渲染 |
| 列表中的公式 | `<li>牛顿第二定律：$F = ma$</li>` | 列表项内正常渲染 |
| 化学方程式 | `<div class="formula-block">$$ \ce{HCl + NaOH -> NaCl + H2O} $$</div>` | MathJax 原生支持，KaTeX 需 `mhchem` |

**编写规则很简单：** 无论公式在哪（`<div>`、`<td>`、`<li>`、`<p>` 还是其他标签内），块级公式用 `$$...$$`，行内公式用 `$...$`。MathJax 自动识别这两个定界符，无需额外配置。

#### 渲染优化

几点让公式渲染更快、更稳定的做法：

1. **`<script>` 放 `<head>` 末尾，不设 `async`/`defer`**。MathJax 会排队处理页面中的公式，放在 `<head>` 中它能尽早开始初始化，不设 `async`/`defer` 保证加载顺序。

2. **`<meta charset="UTF-8">` 必须在 `<head>` 第一个子元素**。浏览器读到编码声明之前可能用错误编码预解析，导致公式乱码。这是渲染问题的头号来源。

3. **减少行内公式数量，合并成块级公式**。每个 `$...$` 行内公式都是独立渲染单元。如果一段话中有 5 个短公式，尽量改成一段文字 + 一个块级 `$$...$$` 公式区域。对 MathJax 来说，块级公式渲染效率远高于大量零散的行内公式。

4. **不要用 `display: none` 隐藏公式，改用 `visibility: hidden`**。`display: none` 的元素宽高为 0，MathJax/KaTeX 在此环境中无法正确测量和排版公式。如果步骤切换需要隐藏公式区域，使用 `visibility: hidden; height: 0; overflow: hidden` 代替。

5. **步骤切换后触发重新渲染**。如果使用 KaTeX，每次切换步骤显示新的公式区域时调用 `renderMathInElement`。MathJax 使用 `MathJax.typesetPromise()`：

```javascript
// KaTeX
function showStep(n) { /* 切换 DOM 可见性 */ renderMathInElement(document.body); }

// MathJax
function showStep(n) { /* 切换 DOM 可见性 */ MathJax.typesetPromise(); }
```

6. **公式区域内避免嵌套其他可渲染元素**。`<div class="formula-block">$$...$$</div>` 中不要混入 `<button>`、`<input>` 等交互元素，放在公式区域外。

### 6. 学科特定要求

#### 数学
- 必须展示公式的逐行推导（每一行一个 LaTeX 公式块）
- 使用 `\begin{aligned}` 对齐多行公式
- 方程求解类需展示配方法、因式分解等过程
- 示例知识点：一元二次方程求解、微积分基本定理、矩阵乘法

#### 物理
- 必须从基本定律出发推导结果
- 使用参数滑块改变变量并实时更新结果
- 示例知识点：F=ma 推导匀加速运动位移公式、欧姆定律电路模拟

#### 化学
- 使用 `\ce{...}` 渲染化学式（需 `mhchem` 扩展）
- 反应式配平需展示原子守恒推导
- 示例知识点：酸碱中和反应、氧化还原配平

#### 计算机
- 使用动画展示算法执行过程（排序、搜索、递归）
- 数据结构可视化（链表、树、图）
- 示例知识点：冒泡排序动画、二叉搜索树插入

### 7. 交互设计要求

- **步骤导航**：分步骤展示内容，支持前进/后退
- **参数调节**：使用 `<input type="range">` 滑块实时改变变量
- **展开/折叠**：复杂推导过程支持折叠，点击展开
- **公式高亮**：当前讲解步骤对应的公式部分高亮显示
- **步骤切换重新渲染**：每次切换步骤后必须调用 `renderMathInElement`，防止新显示区域公式不渲染

### 8. 中文与排版

- `<html lang="zh-CN">`
- `<meta charset="UTF-8">`
- 中文字体：`font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif;`
- 公式字体大小 ≥ 正文 1.2 倍
- 正文行高 ≥ 1.8

### 9. 输出后验证（固定步骤）

**生成 HTML 文件后，验证以下项目确保公式能正确渲染。** 如有未通过项，修复后重新输出。详细技巧参考子 skill `teaching-html-formula-encoding`（位于 `teaching-html-formula-encoding/SKILL.md`）。

1. **定界符完整性**：用正则 `\\[a-zA-Z]+` 搜索文件，确认所有 LaTeX 命令都在 `$$...$$` 或 `$...$` 之内
2. **编码声明**：确认 `<meta charset="UTF-8">` 在 `<head>` 第一行；文件以 UTF-8 without BOM 保存
3. **CDN 可访问性**：所有 `<script>` 和 `<link>` 资源使用 bootcdn.cn 或 jsdelivr.net，各有 `onerror` fallback
4. **引擎加载**：MathJax 只需一行 `<script src="...tex-mml-chtml.js">`；KaTeX 需额外加载 `auto-render` + `mhchem` + 调用 `renderMathInElement`
5. **公式总数**：确认页面中 `.katex` 或 `mjx-container` 的 DOM 元素数量与预期公式数一致

## 踩坑点

| 问题 | 原因 | 解决 |
|------|------|------|
|| 公式显示为 LaTeX 源码（`\frac`、`\displaystyle`、`\oint`、`\nabla`、`\mathbf`、`\partial` 等任何 `\<cmd>` 直接可见） | 公式未用 `$$` 或 `$` 包裹；HTML 标签内（`<td>`、`<li>` 等）的公式同样适用此规则 | 用正则 `\\[a-zA-Z]+` 搜索所有 LaTeX 命令，确保每个都在定界符内；给裸露公式加上 `$$...$$` 或 `$...$` |
| KaTeX 不渲染 | CDN 加载失败且无 fallback | 确保 `onerror` 设置了 fallback |
| 中文变为乱码 | 文件用 GBK 编码保存 | 必须保证 `<meta charset="UTF-8">` 在 `<head>` 第一行，且文件 UTF-8 编码 |
| 化学式不渲染 | 未加载 mhchem 扩展 | KaTeX 需额外加载 `contrib/mhchem.min.js` |
| 加载缓慢 | KaTeX 从国外 CDN 加载 | 全用 bootcdn.cn / jsdelivr.net，禁止 unpkg |
| 步骤切换时公式丢失 | DOM 变更后未重新渲染 | 每次切换步骤后调用 `renderMathInElement` |

## 子 Skill

本 skill 包含一个子 skill，用于深度诊断公式渲染问题：

- **`teaching-html-formula-encoding`** — 位于 `skills/teaching-html-formula-encoding/SKILL.md`。当公式格式检查发现问题时，使用子 skill 中的五层排查体系（编码层→CDN 层→渲染引擎层→字体层→特殊符号层）逐层定位和修复。
