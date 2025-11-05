# -*- coding: utf-8 -*-
"""
@File    : host_ip.py
@Author  : yintian
@Date    : 2025/11/5 14:21
@Software: PyCharm
@Desc    : 
"""
import socket
from functools import lru_cache


@lru_cache()
def get_local_ip():
    try:
        # 创建一个socket对象并连接到外部地址
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 使用Google的DNS服务器地址，无需实际发送数据
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        raise RuntimeError(f"无法获取内网IP: {str(e)}")


if __name__ == '__main__':
    pass
