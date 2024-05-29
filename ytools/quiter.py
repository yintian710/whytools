# -*- coding: utf-8 -*-
"""
@File    : quiter.py
@Date    : 2024/5/23 上午9:47
@Author  : yintian
@Desc    : 
"""
import os
import signal
import time
from typing import Callable

from ytools.log import logger


class Quiter:
    events = []

    @classmethod
    def run(cls, a, b):  # NOQA
        try:
            cls.run_ev()
        finally:
            logger.debug('收到退出信号, 准备退出程序')
            os._exit(0)  # noqa

    @classmethod
    def run_ev(cls):
        while cls.events:
            ev = cls.events.pop()
            try:
                ev['func'](*ev['args'], **ev['kwargs'])
            except:  # noqa
                pass


try:
    signal.signal(signalnum=signal.SIGTERM, handler=Quiter.run)
    signal.signal(signalnum=signal.SIGINT, handler=Quiter.run)
    signal.signal(signalnum=signal.SIGKILL, handler=Quiter.run)
except:  # noqa
    pass


def at_exit(func: Callable, *args, **kwargs):
    if kwargs.pop('__always', None):
        import atexit
        atexit.register(func, *args, **kwargs)
    Quiter.events.append({
        'func': func,
        'args': args,
        'kwargs': kwargs
    })


if __name__ == '__main__':
    at_exit(func=lambda: print(111))
    while True:
        logger.debug(os.getpid())
        time.sleep(5)
