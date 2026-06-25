# HTML 离线显示数学公式：本地化方案参考

`generate-teaching-html` 产物必须支持断网和 `file://` 打开，禁止使用 CDN、在线字体、在线脚本或运行时网络请求。公式应直接写成浏览器可显示的结构，而不是把 LaTeX 源码留给外部库渲染。

---

## 一、首选方案：MathML

现代 Chrome、Edge、Firefox、Safari 均支持基础 MathML。分式、根号、上下标、矩阵等结构化公式优先使用 MathML。

```html
<math display="block">
  <mi>x</mi>
  <mo>=</mo>
  <mfrac>
    <mrow>
      <mo>-</mo><mi>b</mi><mo>&plusmn;</mo>
      <msqrt>
        <mrow><msup><mi>b</mi><mn>2</mn></msup><mo>-</mo><mn>4</mn><mi>a</mi><mi>c</mi></mrow>
      </msqrt>
    </mrow>
    <mrow><mn>2</mn><mi>a</mi></mrow>
  </mfrac>
</math>
```

## 二、轻量方案：HTML/CSS 公式组件

简单公式、分数线、步骤推导可用 HTML/CSS 自定义组件，稳定、可控、无需任何库。

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
.formula {
  font-family: "Times New Roman", "Cambria Math", serif;
  font-size: 1.2em;
}
.frac {
  display: inline-flex;
  flex-direction: column;
  vertical-align: middle;
  text-align: center;
  line-height: 1.25;
}
.frac .num {
  border-bottom: 1px solid currentColor;
  padding: 0 0.25em 0.08em;
}
.frac .den {
  padding-top: 0.08em;
}
```

## 三、化学式：上下标直写

化学式不要写成 `\ce{...}`。离线 HTML 中直接用 `<sub>`、`<sup>` 和实体符号表达。

```html
<span class="formula">HCl + NaOH &rarr; NaCl + H<sub>2</sub>O</span>
<span class="formula">MnO<sub>4</sub><sup>-</sup> + 5Fe<sup>2+</sup> + 8H<sup>+</sup> &rarr; Mn<sup>2+</sup> + 5Fe<sup>3+</sup> + 4H<sub>2</sub>O</span>
```

## 四、复杂公式：内联 SVG 或 Canvas

当公式结构复杂到 MathML/HTML 难以稳定表达时，用内联 SVG 绘制。SVG 必须直接写在 HTML 中，不能引用外部图片。

```html
<svg role="img" aria-label="向量 F 等于质量 m 乘以加速度 a" viewBox="0 0 220 60" width="220" height="60">
  <text x="20" y="38" font-family="Times New Roman, Cambria Math, serif" font-size="28">F = ma</text>
</svg>
```

## 五、禁止清单

- 禁止 CDN、在线脚本、在线样式、在线字体、在线图片
- 禁止 `http://`、`https://`、协议相对 URL
- 禁止外部 `<script src>`、外部 `<link href>`、`@import url(...)`
- 禁止运行时 `fetch`、`XMLHttpRequest`、动态插入远程脚本
- 禁止把 `\frac`、`\sqrt`、`\ce`、`\begin` 等 LaTeX 命令作为最终页面内容

## 六、验证方法

生成 HTML 后必须检查：

1. 断网或 `file://` 打开页面，公式、样式、交互仍可用。
2. 搜索源码，确认没有网络 URL、CDN 域名、外部脚本或外部样式。
3. 搜索 `\\[a-zA-Z]+`，确认没有裸露 LaTeX 命令残留。
4. 检查 `<meta charset="UTF-8">` 位于 `<head>` 第一行，文件保存为 UTF-8 without BOM。
