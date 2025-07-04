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
from itertools import count
from types import NoneType
from typing import Self, List


@dataclasses.dataclass
class LinkNode:
    root: Callable = None
    parent: Self = None
    next: Self = None
    callback: Callable = None

    def __setattr__(self, key, value):
        if key == 'next' and type(value) not in (LinkNode, NoneType):
            value = LinkNode(value, self)
        elif key == 'next' and isinstance(value, LinkNode):
            value.parent = self

        return super().__setattr__(key, value)

    def __str__(self):
        return f"<LinkNode({self.root})>"

    __repr__ = __str__


tour_id = count()


@dataclasses.dataclass
class TourTree:
    root: Callable = None
    parent: Self = None
    child: List[Self] = dataclasses.field(default_factory=list)
    is_done: bool = False
    callback: Callable = None
    id: int = dataclasses.field(default_factory=lambda: next(tour_id))
    __used: count = dataclasses.field(default_factory=lambda: count(1))
    _used = 0

    def __setattr__(self, key, value):
        if key == 'child' and value is None:
            self.child.clear()
            return
        return super().__setattr__(key, value)

    def add(self, child):
        if child is None:
            return
        if isinstance(child, TourTree):
            child.parent = self
        else:
            child = TourTree(child, self)
        self.child.append(child)

    def done(self):
        self.is_done = True

    def tour_one(self):
        for one in self.child:
            if not one.is_done:
                return one
        if not self.parent and not self.is_done:
            return self
        if self.parent and (one := self.parent.tour_one()) and not one.is_done:
            return one

    def tour(self):
        one = self
        while one:
            yield one
            one.done()
            one = one.tour_one()

    def use(self):
        self._used = next(self.__used)

    @property
    def used(self):
        return self._used

    def print_tree(self, level=0, is_last=False, prefix='', node_info_func=None):
        """可视化打印当前节点及其子树结构"""
        # 当前节点信息
        info = f"Node {self.id} (used={self.used}, done={self.is_done})" if not node_info_func else node_info_func(self)

        # 根节点特殊处理
        if level == 0:
            print(info)
        else:
            # 根据是否最后一个子节点选择连接符
            connector = '└── ' if is_last else '├── '
            print(f"{prefix}{connector}{info}")

        # 递归打印子节点
        for i, child in enumerate(self.child):
            is_last_child = i == len(self.child) - 1
            new_prefix = prefix + ('    ' if is_last else '│   ')
            child.print_tree(level + 1, is_last_child, new_prefix)

    def __len__(self):
        return len(self.child)

    def __bool__(self):
        return bool(self.root or self.child)

    def __call__(self, *args, **kwargs):
        self.use()
        return self.root(*args, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__} id:{self.id} used:{self.used} parent:{self.parent.id if self.parent else None} root:{self.root}>"


if __name__ == '__main__':
    # 根节点（id=0）
    rt = lambda x: print(x)
    root = TourTree(root=rt)

    # 第一层子节点（直接挂在根节点下）
    root.add(TourTree(root=rt))  # id=1
    root.add(TourTree(root=rt))  # id=2
    root.add(TourTree(root=rt))  # id=5

    # 第二层子节点（挂在 id=1 的节点下）
    root.child[0].add(TourTree(root=rt))  # id=3
    root.child[0].add(TourTree(root=rt))  # id=4

    # 第二层子节点（挂在 id=5 的节点下）
    root.child[2].add(TourTree(root=rt))  # id=6
    root.child[2].add(TourTree(root=rt))  # id=7
    # 第三层子节点（挂在 id=7 的节点下）
    root.child[2].child[1].add(TourTree(root=rt))  # id=8
    r9 = TourTree(root=rt)
    root.child[2].child[1].add(r9)  # id=9


    def print_tree(node: TourTree, level=0):
        print(f"{'  ' * level}Node {node.id}-{node.used}-{node.is_done}")
        for child in node.child:
            print_tree(child, level + 1)

    for i in r9.tour():
        i(i)
        if i.id == 5:
            for _ in range(3):
                i.add(TourTree(root=rt))
    root.print_tree()
