# OpenClaw 浏览器功能研究
日期：2026-02-02

## 核心发现
OpenClaw = Clawdbot前身，浏览器功能直接适用

## 能做什么
- 自动化网页操作（点击、输入、滚动）
- 截图和数据采集
- 填表、下载文件
- 模拟登录、设置Cookie
- 监控网络请求

## 配置方法
编辑 ~/.openclaw/openclaw.json:
{
  "browser": {
    "enabled": true,
    "defaultProfile": "openclaw"
  }
}

重启: openclaw gateway restart

## 使用示例
openclaw browser start
openclaw browser open https://example.com
openclaw browser snapshot
openclaw browser click 12
openclaw browser screenshot

## 对我们的价值
✅ Polymarket/Kalshi 价格监控
✅ Twitter/Reddit 研究
✅ 自动化交易辅助
✅ 数据采集

## 当前限制
我在 sandbox 里，需要 host 配置浏览器

## 安全验证
✅ 官方文档（144k stars）
✅ loopback-only 设计
✅ 隔离用户数据

建议：小规模测试后再用于生产
