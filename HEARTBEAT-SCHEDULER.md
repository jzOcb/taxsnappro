# Heartbeat Scheduler 调度系统

## 版本 1.1.0

### 系统目标
- 实现灵活、可配置的作业调度
- 支持不同模型和频率的任务执行
- 提供详细的日志记录和错误处理

### 特性
- 动态作业调度
- 模型基础的任务路由
- 可配置的执行间隔
- 增强的日志记录
- 安全的命令执行机制

### 配置文件结构
- `version`: 版本号
- `last_updated`: 最后更新时间
- `global_config`: 全局配置
  - `log_level`: 日志级别
  - `error_tolerance`: 错误处理策略
  - `default_timeout`: 默认超时时间
- `jobs`: 作业配置
  - `interval`: 执行间隔
  - `action`: 执行操作
  - `model`: 使用的模型
  - `retry_count`: 重试次数
  - `retry_delay`: 重试延迟

### 支持的作业类型
- `check_token_usage`: 监控 Token 使用情况
- `market_scan`: Kalshi 市场扫描
- `sync_kanban`: Kanban 同步
- `register_agent`: Moltbook 代理注册
- `check_arbitrage_status`: 套利状态监控

### 模型策略
- 高频任务使用 Claude Haiku (低成本)
- 复杂任务使用 Claude Sonnet

### 错误处理
- 详细日志记录
- 可配置重试机制
- 命令执行超时控制

### 未来计划
- 支持更多作业类型
- 增加更复杂的重试逻辑
- 提供 Web 管理界面
- 优化性能和可扩展性

### 使用说明
1. 配置 `heartbeat_config.json`
2. 运行 `heartbeat_scheduler.py`
3. 监控 `heartbeat.log` 获取执行详情

### 注意事项
- 定期审查和优化调度策略
- 监控日志文件大小
- 根据实际需求调整配置

*最后更新：2026-02-02*
