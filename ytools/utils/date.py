# -*- coding: utf-8 -*-
"""
@File    : date.py
@Date    : 2024/4/16 下午8:19
@Author  : yintian
@Desc    : 
"""
import time
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from ytools.utils.magic import require

require("arrow==1.3.0", action="fix")

from arrow.constants import DEFAULT_LOCALE  # noqa
from arrow import Arrow as _Arrow, get as arrow_get  # noqa

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


class Arrow(_Arrow, datetime):

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

    def spend(self, fmt: Callable = None):
        t = time.time() - self.ts(10)
        if fmt:
            t = fmt(t)
        return t

    def format(
            self, fmt: str = "YYYY-MM-DD HH:mm:ss", locale: str = DEFAULT_LOCALE
    ) -> str:
        return super().format(fmt, locale)


if __name__ == '__main__':
    a = Arrow.now()
    print(a.format())
