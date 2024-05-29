# -*- coding: utf-8 -*-
"""
@File    : at_exit.py
@Date    : 2024/5/29 下午5:35
@Author  : yintian
@Desc    : 
"""

import atexit
import os
import time

import loguru


def a():
    loguru.logger.info('atexit')


atexit.register(a)

if __name__ == '__main__':
    loguru.logger.debug(f'程序开始')
    # time.sleep(1)
    loguru.logger.debug(f'程序结束')
    while True:
        loguru.logger.info(os.getpid())
        time.sleep(1)

if __name__ == '__main__':
    pass
