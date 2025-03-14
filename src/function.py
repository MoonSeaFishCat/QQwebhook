# 配置签名计算函数
import json
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


class UltimateJSONFormatter(Formatter):
    """终极JSON日志格式化器（解决空行和换行问题）"""
    COLOR_MAP = {
        'DEBUG': Fore.LIGHTCYAN_EX,
        'INFO': Fore.LIGHTGREEN_EX,
        'WARNING': Fore.LIGHTYELLOW_EX,
        'ERROR': Fore.LIGHTRED_EX,
        'CRITICAL': Fore.LIGHTMAGENTA_EX + Style.BRIGHT
    }

    def __init__(self):
        super().__init__()
        self.terminal_width = 80
        self.compact_threshold = 80  # 紧凑模式阈值
        self.indent_size = 2

    def _get_terminal_width(self):
        """动态获取终端宽度"""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def _visible_length(self, text):
        """计算可见文本长度（排除颜色码）"""
        return len(re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text))

    def _format_json_value(self, value, indent_level, in_list=False):
        """智能JSON格式化核心方法"""
        if isinstance(value, dict):
            return self._format_dict(value, indent_level)
        elif isinstance(value, list):
            return self._format_list(value, indent_level)
        elif isinstance(value, str):
            return self._wrap_string(value, indent_level)
        else:
            return json.dumps(value)

    def _format_dict(self, obj, indent_level):
        """格式化字典（自动紧凑模式）"""
        items = []
        current_len = 2  # 计算 { ... } 的总长度

        for k, v in obj.items():
            key_str = f'"{k}": '
            val_str = self._format_json_value(v, indent_level + 1)
            item_str = f'{key_str}{val_str}'

            # 计算紧凑模式长度
            current_len += len(item_str) + 2  # 逗号和空格

            # 超过紧凑阈值则换行
            if current_len > self.compact_threshold:
                return self._multi_line_dict(obj, indent_level)

            items.append(item_str)

        # 紧凑模式输出
        return f'{{ {", ".join(items)} }}'

    def _multi_line_dict(self, obj, indent_level):
        """多行字典格式化"""
        items = []
        for k, v in obj.items():
            key_str = f'"{k}": '
            val_str = self._format_json_value(v, indent_level + 1)
            indent = ' ' * (indent_level + 1) * self.indent_size
            items.append(f'\n{indent}{key_str}{val_str}')

        closing_indent = ' ' * indent_level * self.indent_size
        return f'{{{",".join(items)}\n{closing_indent}}}'

    def _format_list(self, arr, indent_level):
        """智能列表格式化"""
        items = [self._format_json_value(item, indent_level, in_list=True) for item in arr]
        total_len = sum(len(item) for item in items) + 2 * (len(items) - 1)  # 逗号分隔

        if total_len > self.compact_threshold:
            return self._multi_line_list(arr, indent_level)
        return f'[ {", ".join(items)} ]'

    def _multi_line_list(self, arr, indent_level):
        """多行列表格式化"""
        items = []
        for item in arr:
            indent = ' ' * (indent_level + 1) * self.indent_size
            items.append(f'\n{indent}{self._format_json_value(item, indent_level + 1)}')

        closing_indent = ' ' * indent_level * self.indent_size
        return f'[{",".join(items)}\n{closing_indent}]'

    def _wrap_string(self, s, indent_level):
        """智能字符串换行"""
        max_width = self.terminal_width - (indent_level + 1) * self.indent_size - 4  # 保留引号位置
        if len(s) <= max_width:
            return f'"{s}"'

        # 寻找自然分隔点
        split_chars = ['_', '-', '/', ':', '.']
        parts = []
        current = []

        for char in s:
            current.append(char)
            if char in split_chars and len(current) >= max_width * 0.8:
                parts.append(''.join(current))
                current = []

        if current:
            parts.append(''.join(current))

        indent = '\n' + ' ' * (indent_level + 1) * self.indent_size
        return f'"{indent.join(parts)}"'

    def format(self, record):
        # 动态配置
        self.terminal_width = self._get_terminal_width()
        self.compact_threshold = int(self.terminal_width * 0.8)

        # 处理消息
        raw_message = record.getMessage()
        try:
            parsed = json.loads(raw_message)
            formatted = self._format_json_value(parsed, 0)
        except json.JSONDecodeError:
            formatted = raw_message

        # 颜色配置
        color = self.COLOR_MAP.get(record.levelname, Fore.WHITE)
        reset = Style.RESET_ALL

        # 构建日志头
        time_str = f"{Style.DIM}{self.formatTime(record, '%H:%M:%S')}{reset}"
        name_str = f"{Fore.LIGHTBLUE_EX}{record.name}{reset}"
        level_str = f"[{color}{record.levelname}{reset}]"

        # 计算各部分可见长度
        header = f"{time_str} {name_str} {level_str}"
        header_len = self._visible_length(header)

        # 构建消息体
        lines = []
        for i, line in enumerate(formatted.split('\n')):
            if i == 0:
                prefix = header
            else:
                prefix = ' ' * header_len

            lines.append(f"{prefix} {color}{line}{reset}")

        return '\n'.join(lines)


def configure_logger(name: str = 'QQwebhook', level: int = logging.INFO) -> Logger:
    """配置终极日志记录器"""
    logger = getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = StreamHandler(sys.stdout)
        handler.setFormatter(UltimateJSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# 初始化日志实例
logger = configure_logger()