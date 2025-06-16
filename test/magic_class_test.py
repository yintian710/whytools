# -*- coding: utf-8 -*-
"""
@File    : magic_class_test.py
@Author  : yintian
@Date    : 2025/6/16 17:20
@Software: PyCharm
@Desc    : 
"""
import functools
import inspect

from ytools.utils.magic_for_class import CustomMeta


class When(metaclass=CustomMeta, singleton='all'):
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def get_name(self):
        return self.name

    def _when_get_name(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            raw_name = self.name
            self.name = 'when_' + raw_name
            try:
                return func(*args, **kwargs)
            finally:
                self.name = raw_name

        return wrapper


def name_match(ins, attr_name: str):
    if not attr_name.startswith('get_e'):
        return False

    attr_value = getattr(ins, attr_name)
    sig = inspect.signature(attr_value)
    if 'name' in sig.parameters:
        return True
    sig.bind()


def name_fix(ins, attr_name: str):
    def process(_ins, func):
        @functools.wraps(func)
        def method(*args, **kwargs):
            sig = inspect.signature(func)
            bind = sig.bind(*args, **kwargs)
            real_args = bind.arguments
            if not real_args.get('name'):
                kwargs.setdefault('name', _ins.name)
            return func(*args, **kwargs)

        return method

    attr_value = getattr(ins, attr_name)
    setattr(ins, attr_name, process(ins, attr_value))


class Fix(metaclass=CustomMeta, fix={"name": {'match': name_match, 'fix': name_fix}}):
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def get_name(self):
        return self.name

    def get_e_name(self, name=None):
        print(self.name, '-', name)
        return name

    def _when_get_name(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            raw_name = self.name
            self.name = 'when_' + raw_name
            try:
                return func(*args, **kwargs)
            finally:
                self.name = raw_name

        return wrapper


if __name__ == '__main__':
    w = When('a', b=3)
    e = Fix('b', c=4, b=2, e=w)
    print(w.get_name())
    print(e.get_name())
    print(e.get_e_name('c'))
    print(e.get_e_name())
