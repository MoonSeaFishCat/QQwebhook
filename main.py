import asyncio
from fastapi import FastAPI, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config import*
from src.envfix import create_config_if_not_exists
from src.function import *
import uvicorn

create_config_if_not_exists()
app = FastAPI()
leave= get_config("日志等级.leave")
logger = configure_logger("QQwebhook",leave)
# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
active_connections = {}
active_connections_lock = asyncio.Lock()


# 数据模型
class Payload(BaseModel):
    d: dict

@app.post("/webhook")
async def handle_webhook(
        request: Request,
        payload: Payload,
        user_agent: str = Header(None),
        x_bot_appid: str = Header(None)
):
    """处理Webhook请求"""
    secret = request.query_params.get('secret')
    if not secret:
        logger.error("缺少secret参数")
        return {"error": "Secret required"}, 400

    try:
        # 处理回调验证请求
        if "event_ts" in payload.d and "plain_token" in payload.d:
            event_ts = payload.d["event_ts"]
            plain_token = payload.d["plain_token"]
            result = generate_signature(secret, event_ts, plain_token)
            logger.info("生成签名: %s", result)
            return result

        # 处理普通消息
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')
        logger.info("收到消息: %s", body_str)

        # 获取对应WebSocket连接
        async with active_connections_lock:
            ws = active_connections.get(secret)

        if ws:
            try:
                await ws.send_text(body_str)
                logger.info("消息推送成功: %s", secret)
            except WebSocketDisconnect:
                logger.warning("连接已断开: %s", secret)
                async with active_connections_lock:
                    if secret in active_connections and active_connections[secret] is ws:
                        del active_connections[secret]
            except Exception as e:
                logger.error("推送失败: %s", e)
            return {"status": "推送成功"}

        logger.warning("未找到活跃连接: %s", secret)
        return {"status": "连接未就绪"}

    except Exception as e:
        logger.error("处理异常: %s", e)
        return {"error": "服务器内部错误"}, 500


@app.websocket("/ws/{secret}")
async def websocket_endpoint(websocket: WebSocket, secret: str):
    """WebSocket连接端点"""
    await websocket.accept()

    # 关闭旧连接并注册新连接
    async with active_connections_lock:
        if secret in active_connections:
            old_ws = active_connections[secret]
            try:
                await old_ws.close()
                logger.info("已关闭旧连接: %s", secret)
            except Exception as e:
                logger.error("关闭旧连接失败: %s", e)
        active_connections[secret] = websocket
        logger.info("新连接建立: %s", secret)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("连接断开: %s", secret)
    except Exception as e:
        logger.error("连接异常: %s - %s", secret, e)
    finally:
        async with active_connections_lock:
            if secret in active_connections and active_connections[secret] is websocket:
                del active_connections[secret]
                logger.info("清理连接: %s", secret)






if __name__ == "__main__":


    host= get_config("服务端信息.ip")
    port = int(get_config("服务端信息.port"))
    uvicorn.run(
        app,
        host=host,
        port=port,
        ws_ping_timeout=300,
        timeout_keep_alive=300
    )
