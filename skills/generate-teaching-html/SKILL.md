---
name: generate-teaching-html
description: 生成教学演示 HTML 页面。输出纯本地、自我包含的单 HTML 文件，禁止使用 CDN 或任何网络资源，讲解学科原理（而非仅展示结果），支持跨学科复用（数学、物理、化学、计算机），中文友好，公式显示正确。生成后固定执行离线资源与公式格式检查。
---
# 生成教学演示 HTML

## 描述

当用户需要为某个学科知识点创建交互式教学演示时，生成一个纯本地、自我包含的 HTML 文件。该文件通过内嵌的 CSS 和 JavaScript 实现分步讲解、公式显示和交互控制，可在浏览器直接打开（file:// 协议），无需任何后端、构建工具、CDN 或互联网连接。

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

### 2. 本地资源约束（强制）

生成结果必须是 **零网络依赖** 的本地 HTML。默认产物为单个 `.html` 文件，所有样式、脚本和媒体资源都必须内嵌在文件中。

**强制禁止：**

- 禁止使用 CDN，包括但不限于 bootcdn、jsdelivr、cdnjs、unpkg、googleapis
- 禁止出现任何 `http://`、`https://` 或协议相对 URL（`//example.com/...`）
- 禁止使用外部 `<script src="...">`、`<link href="...">`、`@import url(...)`、在线字体、在线图片、在线音视频
- 禁止在运行时通过 `fetch`、`XMLHttpRequest`、动态插入 `<script>` 等方式拉取网络资源

**允许方式：**

- CSS 必须写在 `<style>` 中，JavaScript 必须写在 `<script>` 中
- 图片、音频、字体等资源如确需使用，必须转为 `data:` URI 内嵌；如果文件过大，先征得用户同意再改为同目录相对本地文件
- 数学/化学公式优先使用 MathML、HTML/CSS、Unicode 上下标、内联 SVG 或 Canvas 绘制，不依赖在线公式渲染库
- 若用户明确要求使用 MathJax/KaTeX，只能使用用户提供或项目内已有的本地库，并将所需 JS/CSS/字体完整内嵌或放入同目录本地资源；不得从网络加载

### 3. 公式呈现方案

默认不加载 MathJax 或 KaTeX。公式必须在离线、断网、`file://` 打开时仍能直接显示。

**推荐顺序：**

1. **MathML**：用于分式、根号、矩阵、上下标结构清晰的数学公式。
2. **HTML/CSS 公式组件**：用于简单推导、分数线、向量、步骤高亮等教学展示。
3. **Unicode + `<sup>/<sub>`**：用于简单上标、下标、化学式和短公式。
4. **内联 SVG/Canvas**：用于复杂排版或需要动画演示的公式结构。

MathML 示例：

```html
<math display="block">
  <mi>x</mi>
  <mo>=</mo>
  <mfrac>
    <mrow><mo>-</mo><mi>b</mi><mo>&plusmn;</mo><msqrt><mrow><msup><mi>b</mi><mn>2</mn></msup><mo>-</mo><mn>4</mn><mi>a</mi><mi>c</mi></mrow></msqrt></mrow>
    <mrow><mn>2</mn><mi>a</mi></mrow>
  </mfrac>
</math>
```

HTML/CSS 分式示例：

```html
<span class="formula">
  x =
  <span class="frac">
    <span class="num">-b &plusmn; &radic;(b<sup>2</sup> - 4ac)</span>
    <span class="den">2a</span>
  </span>
</span>
```

```css
.formula { font-family: "Times New Roman", "Cambria Math", serif; font-size: 1.2em; }
.frac { display: inline-flex; flex-direction: column; vertical-align: middle; text-align: center; }
.frac .num { border-bottom: 1px solid currentColor; padding: 0 0.25em 0.1em; }
.frac .den { padding-top: 0.1em; }
```

**关键：** 不要把 LaTeX 源码直接暴露给浏览器（如 `\frac{a}{b}`、`\ce{H2O}`）。除非同时内嵌了本地公式渲染器，否则 LaTeX 源码不会自动渲染。

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

公式应写成浏览器可直接显示的结构化 HTML，而不是依赖外部渲染器识别定界符。

| 公式类型 | 推荐写法 | 效果 |
|----------|----------|------|
| 块级公式（独立一行居中） | `<div class="formula-block"><math display="block">...</math></div>` | 公式独立成行、居中 |
| 行内公式（嵌在段落中） | `当 <span class="formula">a &ne; 0</span> 时，方程有解。` | 公式与文字同行 |
| 表格中的公式 | `<td><span class="formula">F = ma</span></td>` | 单元格内公式正常显示 |
| 列表中的公式 | `<li>牛顿第二定律：<span class="formula">F = ma</span></li>` | 列表项内正常显示 |
| 化学方程式 | `<div class="formula-block"><span class="formula">HCl + NaOH &rarr; NaCl + H<sub>2</sub>O</span></div>` | 断网也能显示 |

**编写规则很简单：** 无论公式在哪（`<div>`、`<td>`、`<li>`、`<p>` 还是其他标签内），都必须使用 MathML、HTML/CSS、Unicode、`<sup>`、`<sub>` 或内联 SVG 直接表达。不要把 `$$...$$`、`$...$`、`\frac`、`\ce` 等 LaTeX 语法当作最终页面内容。

#### 渲染优化

几点让公式渲染更快、更稳定的做法：

1. **公式结构直接写入 DOM**。生成后的页面首次打开就应看到排版后的公式，而不是等待远程库加载或二次渲染。

2. **`<meta charset="UTF-8">` 必须在 `<head>` 第一个子元素**。浏览器读到编码声明之前可能用错误编码预解析，导致公式乱码。这是渲染问题的头号来源。

3. **减少复杂行内公式数量，合并成块级公式**。一段话中如果有多个复杂公式，尽量改成一段文字 + 一个块级公式区域，降低阅读和维护成本。

4. **切换步骤时保持布局稳定**。如果公式区域会显示/隐藏，给容器设置稳定的 `min-height` 或固定布局，避免页面跳动。

5. **步骤切换只改可见状态，不依赖公式重渲染**。所有公式在 HTML 中已经是最终显示结构，切换步骤时只负责展示对应内容：

```javascript
function showStep(n) {
  document.querySelectorAll(".step-content").forEach(function(section, index) {
    section.classList.toggle("active", index === n - 1);
  });
}
```

6. **公式区域内避免嵌套交互元素**。`<div class="formula-block">...</div>` 中不要混入 `<button>`、`<input>` 等交互元素，放在公式区域外。

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
- 使用 Unicode、`<sub>`、`<sup>` 或 MathML 表达化学式，不使用 `\ce{...}` 作为最终页面内容
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
- **步骤切换稳定显示**：每次切换步骤后确认公式区域仍然可见且布局不跳动

### 8. 中文与排版

- `<html lang="zh-CN">`
- `<meta charset="UTF-8">`
- 中文字体：`font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif;`
- 公式字体大小 ≥ 正文 1.2 倍
- 正文行高 ≥ 1.8

### 9. 输出后验证（固定步骤）

**生成 HTML 文件后，验证以下项目确保公式能正确渲染。** 如有未通过项，修复后重新输出。详细技巧参考子 skill `teaching-html-formula-encoding`（位于 `teaching-html-formula-encoding/SKILL.md`）。

1. **无 LaTeX 源码残留**：用正则 `\\[a-zA-Z]+` 搜索文件，确认没有裸露的 `\frac`、`\ce`、`\sqrt`、`\begin` 等 LaTeX 命令作为最终页面内容
2. **编码声明**：确认 `<meta charset="UTF-8">` 在 `<head>` 第一行；文件以 UTF-8 without BOM 保存
3. **零网络依赖**：搜索 `http://`、`https://`、`//cdn`、`<script src=`、`<link rel="stylesheet"`、`@import`、`fetch(`，确认没有网络资源或运行时网络请求
4. **资源内嵌**：确认 CSS 在 `<style>` 中、JS 在 `<script>` 中；图片/字体/音频如有必须为 `data:` URI 或经用户确认的同目录本地文件
5. **公式显示检查**：用浏览器断网打开 HTML，确认公式结构、上下标、分式、根号、化学式均能直接显示

## 踩坑点

| 问题 | 原因 | 解决 |
|------|------|------|
|| 公式显示为 LaTeX 源码（`\frac`、`\displaystyle`、`\oint`、`\nabla`、`\mathbf`、`\partial` 等任何 `\<cmd>` 直接可见） | 页面没有内嵌公式渲染器，浏览器不会自动识别 LaTeX | 改写为 MathML、HTML/CSS、Unicode 上下标或内联 SVG |
| 断网后样式或公式消失 | 使用了 CDN、在线字体或远程脚本 | 删除所有网络资源，将 CSS/JS/字体/图片内嵌到 HTML |
| 中文变为乱码 | 文件用 GBK 编码保存 | 必须保证 `<meta charset="UTF-8">` 在 `<head>` 第一行，且文件 UTF-8 编码 |
| 化学式不显示下标/电荷 | 直接写普通文本，未使用上下标 | 用 `<sub>`、`<sup>`、Unicode 或 MathML 表达 |
| 加载缓慢 | 内嵌资源过大或脚本初始化复杂 | 精简样式与脚本；大型媒体先询问用户是否改为同目录本地文件 |
| 步骤切换时公式丢失 | 切换逻辑误删 DOM 或容器高度塌陷 | 只切换 class/display，给公式区域设置稳定布局 |

## 子 Skill

本 skill 包含一个子 skill，用于深度诊断公式渲染问题：

- **`teaching-html-formula-encoding`** — 位于 `skills/teaching-html-formula-encoding/SKILL.md`。当公式格式检查发现问题时，使用子 skill 中的五层排查体系（编码层→本地资源层→公式结构层→字体层→特殊符号层）逐层定位和修复。
