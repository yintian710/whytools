# -*- coding: utf-8 -*-
"""
@File    : base.py
@Author  : yintian
@Date    : 2025/10/21 10:07
@Software: PyCharm
@Desc    : 
"""
from ytools.utils.magic import require

require("redis")
from redis.asyncio import Redis  # noqa
from ytools.arq import setting


class BaseClient:
    redis: Redis
    split = ':'
    queue_name: str
    tasks_queue: str
    data_queue: str
    result_queue: str
    status_queue: str

    def __init__(
            self,
            queue_name=None,
            redis=None
    ):
        self.set_queue(queue_name)
        if isinstance(redis, dict):
            self.redis = self.make_redis(**redis)
        elif redis:
            self.redis = redis

    def set_queue(self, queue_name):
        self.queue_name = queue_name or setting.DEFAULT_QUEUE_NAME
        self.tasks_queue = self.get_queue("tasks")
        self.data_queue = self.get_queue("data")
        self.result_queue = self.get_queue("result")
        self.status_queue = self.get_queue("status")

    def get_queue(self, *queue: str, base=None):
        return self.split.join([base or self.queue_name, *queue])

    @classmethod
    def make_redis(
            cls,
            host: str,
            port: int,
            db=0,
            password=None,
            **kwargs
    ):
        return Redis(host=host, port=port, db=db, password=password, **kwargs)

    @classmethod
    def from_redis(cls, queue_name=None, **redis_config):
        return cls(queue_name, redis=redis_config)


if __name__ == '__main__':
    pass
