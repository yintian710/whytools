# -*- coding: utf-8 -*-
"""
@File    : always.py
@Date    : 2024-06-03 15:17
@Author  : yintian
@Desc    : 
"""


class A:
    _h = {}

    @property
    def h(self):
        return self._h

    @h.setter
    def h(self, val):
        print()


if __name__ == '__main__':
    a = A()
    print(a.h)
    a.h['a'] = 3
