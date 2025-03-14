# QQ Webhook 转发服务

基于 FastAPI 构建的 Webhook 转发服务，专为 QQ 机器人消息推送设计，支持实时消息转发和双向通信。

## 功能特性

- 🚀 **实时消息推送**：通过 WebSocket 实现毫秒级消息转发
- 🔒 **双重认证**：Secret 参数 + X-Bot-AppID 标头认证机制
- ⚙️ **动态配置**：
  - 热加载 YAML 配置文件
  - 支持多环境配置 (开发/生产)
- 🌐 **跨平台支持**：
  - 兼容 HTTP/WebSocket 协议
  - 完善的 CORS 配置
- 📊 **可观测性**：
  - 分级日志记录 (DEBUG/INFO/WARNING/ERROR)
  - 请求追踪与异常监控

## 快速开始

### 前置要求

- Python 3.8+
- pip 包管理工具

### 安装依赖

```bash
pip install pip install -r requirements.txt
```

### 配置文件

在可执行文件同级目录创建 `config.yaml`：

```yaml
服务端信息:
  ip: "0.0.0.0"  # 监听地址
  port: 8000      # 服务端口

日志等级:
  leave: "DEBUG"  # [DEBUG|INFO|WARNING|ERROR]
```

### 启动服务

```bash
uvicorn main:app --reload --ws-ping-timeout 300
```

## API 文档

### Webhook 端点

**POST** `/webhook?secret=<your_secret>`

**请求头**：
- `X-Bot-AppID`: 机器人应用ID
- `User-Agent`: 客户端标识

**请求体**：
```json
{
  "d": {
    "event_ts": "时间戳",
    "plain_token": "验证令牌",
    // 其他消息字段...
  }
}
```

### WebSocket 端点

**连接地址**：
```
ws://your-domain:port/ws/{secret}
```

**消息协议**：
```typescript
interface Message {
  type: "text" | "image" | "event";
  content: string;
  timestamp: number;
}
```

## 使用示例

### 消息推送测试

```bash
curl -X POST "http://localhost:8000/webhook?secret=test123" \
     -H "X-Bot-AppID: your_appid" \
     -d '{"d":{"content":"测试消息"}}'
```

### Python 客户端

```python
import websockets
import asyncio

async def receive_messages():
    async with websockets.connect('ws://localhost:8000/ws/test123') as ws:
        while True:
            msg = await ws.recv()
            print(f"收到消息: {msg}")

asyncio.run(receive_messages())
```

## 高级配置

### 性能调优参数

在 `uvicorn.run()` 中调整：
```python
uvicorn.run(
    app,
    host=config_host,
    port=config_port,
    ws_ping_timeout=300,      # WebSocket 心跳间隔
    timeout_keep_alive=300    # 连接保持时间
)
```

### 安全建议

1. 生产环境建议：
   - 将日志等级调整为 INFO
   - 使用 HTTPS 加密通信
   - 定期轮换 Secret

2. 访问控制：
   ```yaml
   # config.yaml
   访问控制:
     ip_whitelist: ["192.168.1.0/24"]
     rate_limit: 1000/分钟
   ```

## 架构设计

```mermaid
graph TD
    A[QQ 机器人] --> B[Webhook 推送]
    B --> C{认证校验}
    C -->|成功| D[消息处理器]
    D --> E[WebSocket 分发]
    E --> F[客户端1]
    E --> G[客户端2]
    C -->|失败| H[错误日志]
```

## 贡献指南

欢迎通过 Issue 或 PR 参与贡献，请遵循以下规范：
1. 新功能开发需包含单元测试
2. 提交前执行代码格式化 (`black`)
3. 更新相关文档

## 许可证

MIT License © 2024 [Your Name]
```

## 关键要点说明

1. **消息处理流程**：
   • 支持回调验证请求自动响应
   • 消息体原始数据透传
   • WebSocket 连接健康检查机制

2. **异常处理**：
   • 自动清理无效连接
   • 错误上下文日志记录
   • 分级错误响应 (400/500)

3. **性能优化**：
   • 异步锁保护连接字典
   • 连接复用机制
   • 心跳保活设置

4. **可维护性**：
   • 模块化配置管理
   • 日志标识追踪
   • 类型注解全覆盖

5. **扩展能力**：
   • 支持自定义中间件
   • 易于集成消息队列
   • 可扩展的认证模块
