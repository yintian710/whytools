# -*- coding: utf-8 -*-
"""
@File    : nodes.py
@Author  : yintian
@Date    : 2025/6/24 11:38
@Software: PyCharm
@Desc    : 
"""
import dataclasses
from collections.abc import Callable
from types import NoneType
from typing import Self


@dataclasses.dataclass
class LinkNode:
    root: Callable = None
    parent: Self = None
    next: Self = None
    callback: Callable = None

    def __setattr__(self, key, value):
        if key == 'next' and type(value) not in (LinkNode, NoneType):
            value = LinkNode(value, self)
        elif isinstance(value, LinkNode):
            value.parent = self

        return super().__setattr__(key, value)

    def __str__(self):
        return f"<LinkNode({self.root})>"

    __repr__ = __str__


if __name__ == '__main__':
    pass
