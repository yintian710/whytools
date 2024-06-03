# -*- coding: utf-8 -*-
"""
@File    : error.py
@Date    : 2024-06-03 15:35
@Author  : yintian
@Desc    : 
"""


class ResultError(Exception):

    def __init__(self, error, stack, f, a=None, k=None):
        super().__init__()
        self.error = error
        self.stack = stack
        self.func = f
        self.args = a or tuple()
        self.kwargs = k or dict()

    def __str__(self):
        return f'<{self.error.__class__.__name__}: func:{self.func}, args:{self.args}, kwargs:{self.kwargs}>'

    def __bool__(self):
        return False


if __name__ == '__main__':
    pass
