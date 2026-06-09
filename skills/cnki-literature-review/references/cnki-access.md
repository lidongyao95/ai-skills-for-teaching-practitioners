# 知网机构访问与 PDF 下载说明

## 机构 IP 识别

高校购买知网后，校园网出口 IP 会被自动识别。典型表现：

1. 打开 https://www.cnki.net 右上角显示机构名（如「XX大学图书馆」）
2. 文献详情页出现「PDF 下载」「CAJ 下载」按钮
3. 下载时不弹出个人账号登录框

**不在机构 IP 时**：仅能看到摘要，PDF 按钮灰色或跳转付费页。需连接校园网或学校 VPN 后重试。

## 常用入口

| 入口 | URL | 用途 |
|------|-----|------|
| 知网首页 | https://www.cnki.net | 确认机构登录状态 |
| 高级检索 | https://kns.cnki.net/kns8s/advsearch | 组合检索式 |
| 默认结果页 | https://kns.cnki.net/kns8s/defaultresult/index | 快速检索 |

## PDF 下载路径

```
检索结果列表
  → 点击题名进入详情页
    → 「下载」区域
      → 「PDF 下载」（优先）
      → 或「整本下载」→ 选择 PDF
```

## 首次运行：人工认证窗口

`cnki_download.py` 默认 `--headless false`，首次运行会：

1. 打开 Chromium 窗口
2. 等待 `--manual-wait` 秒
3. 期间用户可：确认机构名、完成验证码、关闭弹窗

## 常见问题

### 1. 出现滑动验证码
- 保持 `--headless false`
- 人工完成验证
- 增大 `--delay` 至 5-8 秒

### 2. 下载的是 HTML 而非 PDF
- 原因：会话失效或未走机构通道
- 处理：检查文件头是否 `%PDF`；不是则删除后重下载

### 3. 超出单日下载上限
- 机构可能对单 IP 限流
- 暂停 24h 或联系图书馆

### 4. 下载按钮找不到
- 知网页面会改版，按钮文案可能变化
- 更新 `cnki_download.py` 中 `PDF_BUTTON_TEXTS` 列表
- 或改用手动下载 + 手动放入 `papers/pdf/`
