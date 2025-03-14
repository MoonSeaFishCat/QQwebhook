# 配置签名计算函数
import logging
import re
import shutil
from logging import *
from colorama import Fore, Style, init
from cryptography.hazmat.primitives.asymmetric import ed25519
import sys
import os

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


# 初始化colorama
init(autoreset=True)
class DynamicWidthFormatter(Formatter):
    """动态宽度计算日志格式化器（修复版）"""
    COLOR_MAP = {
        'DEBUG': Fore.LIGHTCYAN_EX,
        'INFO': Fore.LIGHTGREEN_EX,
        'WARNING': Fore.LIGHTYELLOW_EX,
        'ERROR': Fore.LIGHTRED_EX,
        'CRITICAL': Fore.LIGHTMAGENTA_EX + Style.BRIGHT
    }

    def __init__(self):
        super().__init__()
        self.max_name_len = 10
        self.terminal_width = self._get_terminal_width()

    def _get_terminal_width(self):
        """安全获取终端宽度"""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80  # 默认宽度

    def _visible_length(self, text):
        """计算去除颜色码后的可见文本长度"""
        return len(re.sub(r'\x1b\[[0-9;]*m', '', str(text)))

    def format(self, record):
        # 动态更新终端宽度
        self.terminal_width = self._get_terminal_width()

        # 颜色处理
        color = self.COLOR_MAP.get(record.levelname, Fore.WHITE)
        reset = Style.RESET_ALL

        # 构建基础信息块
        time_str = f"{Style.DIM}{self.formatTime(record, '%H:%M:%S')}{reset}"
        name_str = f"{Fore.LIGHTBLUE_EX}{record.name}{reset}"
        level_str = f"[{color}{record.levelname}{reset}]"

        # 动态计算各部分宽度
        time_width = self._visible_length(time_str)
        name_width = self._visible_length(record.name)
        level_width = self._visible_length(level_str) - 4  # 去除颜色码影响

        # 消息可用宽度计算
        msg_max_width = max(20, self.terminal_width - (time_width + name_width + level_width + 3))

        # 智能消息换行
        msg_lines = []
        current_line = []
        current_len = 0
        for word in str(record.msg).split():
            word_len = self._visible_length(word)
            if current_len + word_len + 1 > msg_max_width:
                msg_lines.append(' '.join(current_line))
                current_line = [word]
                current_len = word_len
            else:
                current_line.append(word)
                current_len += word_len + 1
        msg_lines.append(' '.join(current_line))

        # 构建输出格式
        formatted = []
        for i, line in enumerate(msg_lines):
            if i == 0:
                prefix = f"{time_str} {name_str} {level_str}"
            else:
                prefix = ' ' * (time_width + name_width + level_width + 2)

            formatted.append(f"{prefix} {color}{line}{reset}")

        return '\n'.join(formatted)


def configure_logger(name='QQwebhook', level=logging.INFO):
    """安全配置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = StreamHandler(sys.stdout)
        handler.setFormatter(DynamicWidthFormatter())
        logger.addHandler(handler)

    # 禁用传播以避免重复日志
    logger.propagate = False
    return logger