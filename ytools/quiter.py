# -*- coding: utf-8 -*-
"""
@File    : quiter.py
@Date    : 2024/5/23 上午9:47
@Author  : yintian
@Desc    : 
"""
import atexit
import os
import random
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
        atexit.register(func, *args, **kwargs)
    key = hash(f'{id(func)}-{time.time()}-{random.Random}')
    func_dict = {
        'func': func,
        'args': args,
        'kwargs': kwargs,
        'key': key
    }
    Quiter.events.append(func_dict)
    return key


def un_exit(key):
    events = Quiter.events.copy()
    for ev in events:
        if ev['key'] == key:
            func = ev['func']
            Quiter.events.remove(ev)
            atexit.unregister(func)
            break
