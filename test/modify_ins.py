# -*- coding: utf-8 -*-
"""
@File    : modify_ins.py
@Date    : 2025/1/21 14:29
@Author  : yintian
@Desc    : 
"""
import functools
from typing import Callable


def ttt(func):
    @functools.wraps(func)
    def tttt(*args, **kwargs):
        try:
            print('start')
            __res = func(*args, **kwargs)
            print('end')
            return __res
        except Exception as e:
            print(e)

    return tttt


class Mi:

    def __init__(self, name, age):
        self.name = name
        self.age = age
        self._modify()

    def _modify(self):
        for attr in dir(self):
            obj = getattr(self, attr)
            if isinstance(obj, Callable):
                if "tag:try" in (obj.__doc__ or ""):
                    setattr(self, attr, ttt(obj))

    def xxx(self):
        """tag:try"""
        print(self.name)

    def yyy(self):
        """tag:try"""
        print(self.age)


class Mi1(Mi):

    def xxx(self):
        print(self.name)

    def yyy(self):
        """tag:try"""
        print(self.age + 1)


if __name__ == '__main__':
    mi = Mi1("yintian", 18)
    mi.xxx()
    mi.yyy()
