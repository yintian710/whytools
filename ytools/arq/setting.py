# -*- coding: utf-8 -*-
"""
@File    : setting.py
@Author  : yintian
@Date    : 2025/10/21 10:30
@Software: PyCharm
@Desc    : 
"""
# 默认队列名
DEFAULT_QUEUE_NAME = "ytools:arq"
# 是否启用加密, 若传入方法则使用传入方法
ENCRYPT = False
# 默认编码
DEFAULT_ENCODING = "utf-8"
# 轮询休眠
INTERVAL = 0.01
# 传入的是否是可序列化数据
OBJ_DATA = False
# key 超时删除时间
EXPIRE_TIME = 300

if __name__ == '__main__':
    pass
