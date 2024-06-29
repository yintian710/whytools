# -*- coding: utf-8 -*-
"""
@File    : quiter.py
@Date    : 2024/5/29 下午5:35
@Author  : yintian
@Desc    : 
"""
import os
import time

from ytools.log import logger
from ytools.utils.quiter import at_exit

k1 = at_exit(func=lambda: print(111), __always=True)
k2 = at_exit(func=lambda: print(222))
k = [k1, k2]
while True:
    logger.debug(os.getpid())
    time.sleep(5)
    # un_exit(k.pop())
