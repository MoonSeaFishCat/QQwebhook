import os
import sys


def create_config_if_not_exists():
    # 获取当前执行文件所在目录
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    # 拼接配置文件路径
    config_path = os.path.join(current_dir, 'setconfig.yaml')

    # 检查配置文件是否存在，存在则直接返回
    if os.path.exists(config_path):
        return

    # 定义配置文件内容，包含注释
    config_content = '''# 服务端启动配置
服务端信息:
  ip: "127.0.0.1"
  port: "8085"

#日志等级
日志等级:
  leave: "INFO"
'''
    try:
        # 写入文件，使用utf-8编码
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
    except Exception as e:
        print(f"创建配置文件时发生错误：{e}")

