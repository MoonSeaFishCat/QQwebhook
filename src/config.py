import os
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union
import logging

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML

from src.function import configure_logger


logger = configure_logger("QQwebhook","DEBUG")
class YAMLHandlerException(Exception):
    """自定义YAML操作异常基类"""
    pass


class YAMLHandler:
    def __init__(self, preserve_comments: bool = False):
        """
        YAML处理器类，支持YAML文件的加载、保存和更新。

        :param preserve_comments: 是否保留注释（需安装ruamel.yaml ）
        """
        self.parser = YAML()
        if preserve_comments and 'ruamel' not in str(type(self.parser)):
            raise YAMLHandlerException("Comment preservation requires ruamel.yaml")

    def load(self, file_path: str) -> dict:
        """从文件加载YAML内容"""
        self._validate_file(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.parser.load(f) or {}
        except Exception as e:
            raise YAMLHandlerException(f"YAML解析失败: {str(e)}")

    def loads(self, yaml_str: str) -> dict:
        """从字符串加载YAML内容"""
        try:
            return self.parser.load(yaml_str) or {}
        except Exception as e:
            raise YAMLHandlerException(f"YAML解析失败: {str(e)}")

    def dump(self, data: dict, file_path: str, **kwargs):
        """将数据写入YAML文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            self.parser.dump(data, f, **kwargs)

    def dumps(self, data: dict) -> str:
        """将数据转换为YAML字符串"""
        from io import StringIO
        stream = StringIO()
        self.parser.dump(data, stream)
        return stream.getvalue()

    def update_value(self, file_path: str, key_path: str, value: Any):
        """更新嵌套值（支持点分隔路径）"""
        data = self.load(file_path)
        keys = key_path.split('.')
        current = data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value
        self.dump(data, file_path)

    def validate_structure(self, data: dict, schema: BaseModel) -> bool:
        """使用Pydantic模型验证数据结构"""
        try:
            schema.model_validate(data)
            return True
        except ValidationError as e:
            raise YAMLHandlerException(f"结构验证失败: {e.errors()}")

    @staticmethod
    def _validate_file(file_path: str):
        """验证文件是否存在且为YAML格式"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not file_path.lower().endswith(('.yaml', '.yml')):
            raise YAMLHandlerException("仅支持YAML格式文件")


class ConfigManager:
    _instance = None
    _config_cache = None
    _last_modified = 0
    _config_path = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._yaml_handler = YAMLHandler(preserve_comments=True)
            cls._instance._config_path = cls._instance._find_config_file()
            logger.info(f"配置文件路径: {cls._instance._config_path}")
        return cls._instance

    def _find_config_file(self) -> str:
        """定位exe同级目录的配置文件"""
        try:
            # 获取可执行文件所在目录
            exe_dir = Path(sys.argv[0]).parent.resolve()
            config_files = ['config.yaml', 'setconfig.yaml']

            for file_name in config_files:
                config_path = exe_dir / file_name
                if config_path.exists():
                    return str(config_path)

            # 兼容开发环境调试
            dev_path = Path.cwd() / 'config.yaml'
            if dev_path.exists():
                return str(dev_path)

        except Exception as e:
            logger.error(f"配置文件查找失败: {str(e)}")

        raise YAMLHandlerException(f"未找到配置文件，请确认以下文件存在: {', '.join(config_files)}")

    def _load_config(self) -> dict:
        """带缓存验证的配置加载"""
        try:
            current_mtime = os.path.getmtime(self._config_path)
            if current_mtime > self._last_modified or not self._config_cache:
                logger.debug(f"正在重新加载配置文件: {self._config_path}")
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = self._yaml_handler.parser.load(f) or {}
                    self._last_modified = current_mtime
            return self._config_cache
        except Exception as e:
            logger.critical(f"配置加载失败: {str(e)}")
            raise YAMLHandlerException(f"配置加载失败: {str(e)}")

    def get_config(self, key_path: str, default: Any = None, expected_type: type = None) -> Any:
        """改进的类型转换逻辑"""
        try:
            config_data = self._load_config()
            keys = key_path.split('.')
            current = config_data

            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return self._handle_missing_key(default, expected_type, key_path)

            return self._cast_value(current, expected_type) if expected_type else current
        except Exception as e:
            logger.error(f"配置获取失败 [{key_path}]: {str(e)}")
            return self._handle_missing_key(default, expected_type, key_path)

    def _handle_missing_key(self, default: Any, expected_type: type, key_path: str) -> Any:
        """改进的默认值处理"""
        if default is None:
            raise YAMLHandlerException(f"必需配置项缺失: {key_path}")

        logger.warning(f"使用默认配置 [{key_path}]")
        return self._cast_value(default, expected_type) if expected_type else default

    def _cast_value(self, value: Any, target_type: type) -> Any:
        """增强的类型转换"""
        try:
            # 处理布尔型字符串
            if target_type == bool and isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')

            # 处理路径类型
            if target_type == Path and isinstance(value, str):
                return Path(value).resolve()

            return target_type(value)
        except (ValueError, TypeError) as e:
            raise YAMLHandlerException(f"类型转换失败 ({type(value).__name__} -> {target_type.__name__}): {value}")


def get_config(key_path: str, default: Any = None, expected_type: type = None) -> Any:
    """线程安全的配置获取入口"""
    return ConfigManager().get_config(key_path, default, expected_type)


def hot_update(key_path: str, value: Any):
    """改进的热更新方法"""
    try:
        manager = ConfigManager()
        current_value = manager.get_config(key_path)

        # 类型校验
        if not isinstance(value, type(current_value)):
            raise YAMLHandlerException(f"类型不匹配: 需要 {type(current_value).__name__} 类型")

        # 更新文件
        yaml_handler = YAMLHandler()
        data = yaml_handler.load(manager._config_path)
        keys = key_path.split('.')
        current = data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value

        # 写入前备份
        backup_path = f"{manager._config_path}.bak"
        yaml_handler.dump(data, backup_path)

        # 原子操作替换文件
        os.replace(backup_path, manager._config_path)

        # 强制刷新缓存
        manager._config_cache = None
        manager._last_modified = 0

        logger.info(f"配置热更新成功: {key_path} = {value}")
    except Exception as e:
        logger.error(f"热更新失败: {str(e)}")
        raise