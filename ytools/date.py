# -*- coding: utf-8 -*-
"""
@File    : date.py
@Date    : 2024/4/16 下午8:19
@Author  : yintian
@Desc    : 
"""
from typing import Literal

from ytools.utils import require

require("arrow==1.3.0", action="fix")

from arrow import Arrow as _Arrow, get as arrow_get

T_FRAMES = Literal[
    "year",
    "years",
    "month",
    "months",
    "day",
    "days",
    "hour",
    "hours",
    "minute",
    "minutes",
    "second",
    "seconds",
    "microsecond",
    "microseconds",
    "week",
    "weeks",
    "quarter",
    "quarters",
]


class Arrow(_Arrow):

    @classmethod
    def get(
            cls,
            *args,
            **kwargs
    ) -> 'Arrow':
        """
        获取 Arrow 对象
        :param args:
        :param kwargs:
        :return:
        """
        return cls.fromdatetime(arrow_get(*args, **kwargs).datetime)

    def ts(self, length=10, fmt=int):
        """
        获取时间戳

        :param length: 长度为几位
        :param fmt: 返回什么类型
        :return:
        """
        return fmt(self.timestamp() * 10 ** (length - 10))

    def start(
            self,
            frame: T_FRAMES
    ) -> 'Arrow':
        """
        获取当天开始时间
        :return:
        """
        return self.get(self.floor(frame))

    def end(
            self,
            frame: T_FRAMES
    ) -> 'Arrow':
        """
        获取结束的时间
        :return:
        """
        return self.get(self.ceil(frame))


if __name__ == '__main__':
    a = Arrow.now()
    print(a.start("days").start("quarters"))
