# 配置签名计算函数
from cryptography.hazmat.primitives.asymmetric import ed25519
import logging
import sys
from logging import Formatter, StreamHandler
import os
from colorama import init, Fore, Style

def generate_signature(bot_secret, event_ts, plain_token):
    if len(bot_secret) < 32:
        bot_secret = (bot_secret * (32 // len(bot_secret) + 1))[:32]

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bot_secret.encode())
    message = f"{event_ts}{plain_token}".encode()
    signature = private_key.sign(message).hex()

    return {
        "plain_token": plain_token,
        "signature": signature
    }


# 初始化colorama（自动处理Windows ANSI颜色支持）
init(autoreset=True)


class ColorFormatter(Formatter):
    """智能终端颜色格式化器（自动检测输出环境）"""
    COLOR_MAP = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.is_tty = sys.stdout.isatty()

    def format(self, record):
        # 动态颜色注入
        if self.is_tty:
            color = self.COLOR_MAP.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
            record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


def configure_logger(name='QQwebhook', level=logging.DEBUG):
    """配置全局日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复配置
    if logger.handlers:
        return logger

    # 控制台处理器
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # 高级日志格式
    fmt = (
        f"{Style.DIM}%(asctime)s{Style.RESET_ALL} "
        f"| %(name)-15s "
        f"| %(levelname)-8s "
        f"| {Style.BRIGHT}%(message)s{Style.RESET_ALL}"
    )

    formatter = ColorFormatter(
        fmt=fmt,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 抑制第三方日志
    for lib in ['urllib3', 'asyncio', 'fastapi']:
        logging.getLogger(lib).setLevel(logging.WARNING)

    return logger

