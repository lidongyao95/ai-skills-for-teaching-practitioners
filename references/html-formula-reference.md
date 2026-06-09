# HTML 显示数学公式：开源方案与技巧参考

在 HTML 中**原生不支持直接渲染数学公式**，必须借助**成熟的开源 JavaScript 库**实现。

---

## 一、MathJax（行业标准，功能最强）

MathJax 是全球最主流的开源公式渲染库，支持 LaTeX、MathML 语法，兼容所有浏览器。

### 核心优势
- 完全开源免费（Apache 2.0 协议）
- 无需安装插件，纯前端 JS 渲染
- 公式高清矢量显示（缩放不失真）
- 支持行内公式、块级公式、自动编号
- 功能最全，支持所有复杂 LaTeX 宏

### 基础用法

```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  行内公式：勾股定理 $a^2 + b^2 = c^2$
  块级公式：
  $$E=mc^2$$
  $$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$
  $$
  \begin{bmatrix}
  1 & 2 & 3 \\
  4 & 5 & 6 \\
  7 & 8 & 9
  \end{bmatrix}
  $$
</body>
</html>
```

## 二、KaTeX（速度最快，适合大量公式）

如果页面**公式非常多**（题库、论文、笔记），KaTeX 比 MathJax 更快、体积更小。

### 基础用法

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css">
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/contrib/auto-render.min.js"></script>
</head>
<body>
  行内公式：$f(x) = x^2 + 2x + 1$
  块级公式：
  $$\lim_{x \to 0} \frac{\sin x}{x} = 1$$

  <script>
    renderMathInElement(document.body, {
      delimiters: [
        {left: "$$", right: "$$", display: true},
        {left: "$", right: "$", display: false}
      ]
    });
  </script>
</body>
</html>
```

## 三、选型指南

| 库 | 优点 | 缺点 | 适用场景 |
|----|------|------|----------|
| **MathJax** | 功能最全，支持所有复杂公式，无需 `auto-render` 配置 | 加载稍慢 | 论文、学术网站、复杂公式（**首选**） |
| **KaTeX** | 极快、轻量、渲染秒开 | 极少数极复杂公式不支持，需手动配置 `auto-render` + `mhchem` | 题库、博客、大量公式页面 |

**90% 场景 MathJax 即可胜任。** 它的配置最简单（一行 `<script>` 引入即生效），不需要手动调用 `renderMathInElement` 或配置 delimiters。

## 四、常用 LaTeX 语法速查

所有公式库都支持 LaTeX 语法：

| 效果 | LaTeX | 渲染结果 |
|------|-------|----------|
| 上标 | `a^2` | $a^2$ |
| 下标 | `a_1` | $a_1$ |
| 分数 | `\frac{a}{b}` | $\frac{a}{b}$ |
| 根号 | `\sqrt{2}` | $\sqrt{2}$ |
| n 次根号 | `\sqrt[n]{x}` | $\sqrt[n]{x}$ |
| 积分 | `\int_0^1 x dx` | $\int_0^1 x dx$ |
| 求和 | `\sum_{i=1}^n i` | $\sum_{i=1}^n i$ |
| 极限 | `\lim_{x \to 0}` | $\lim_{x \to 0}$ |
| 导数 | `\frac{df}{dx}` | $\frac{df}{dx}$ |
| 偏导 | `\frac{\partial f}{\partial x}` | $\frac{\partial f}{\partial x}$ |
| 希腊字母 | `\alpha \beta \gamma \theta \lambda \mu \pi \sigma \phi \omega` | $\alpha \beta \gamma \theta \lambda \mu \pi \sigma \phi \omega$ |
| 矢量 | `\vec{F}` `\mathbf{E}` | $\vec{F}$ $\mathbf{E}$ |
| 点乘/叉乘 | `\cdot` `\times` | $\cdot$ $\times$ |
| 矩阵 | `\begin{bmatrix} a & b \\ c & d \end{bmatrix}` | $\begin{bmatrix} a & b \\ c & d \end{bmatrix}$ |
| 多行对齐 | `\begin{aligned} ... \end{aligned}` | — |
