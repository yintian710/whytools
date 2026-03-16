# -*- coding: utf-8 -*-
"""
@File    : base.py
@Author  : yintian
@Date    : 2025/10/21 10:07
@Software: PyCharm
@Desc    : 
"""
import asyncio
import json

from ytools import logger as default_logger
from ytools.utils.counter import FastWriteCounter
from ytools.utils.host_ip import get_local_ip
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
            redis=None,
            logger=None,
            level="info",
    ):
        self.task_count = FastWriteCounter()
        self.extra = {}
        self.logger = logger or default_logger
        self.level = (level or "info").lower()
        self._host_ip = None
        self.set_queue(queue_name)
        if isinstance(redis, dict):
            self.redis = self.make_redis(**redis)
        elif isinstance(redis, str):
            self.redis = Redis.from_url(redis)
        elif redis:
            self.redis = redis
        asyncio.create_task(self.heartbeat())

    @property
    def info(self):
        return {
            "host_ip": self.get_host_ip(),
            "task_count": self.task_count.value,
            **self.extra
        }

    def set_queue(self, queue_name):
        self.queue_name = queue_name or setting.DEFAULT_QUEUE_NAME
        self.tasks_queue = self.get_queue("tasks")
        self.data_queue = self.get_queue("data")
        self.result_queue = self.get_queue("result")
        self.status_queue = self.get_queue("status")

    def get_queue(self, *queue: str, base=None):
        return self.split.join([base or self.queue_name, *queue])

    def log(self, message, level=None, *args, **kwargs):
        level = (level or self.level or "info").lower()
        logger_func = getattr(self.logger, level, None)
        if callable(logger_func):
            return logger_func(message, *args, **kwargs)
        logger_func = getattr(self.logger, "info", None)
        if callable(logger_func):
            return logger_func(message, *args, **kwargs)

    def get_host_ip(self):
        if self._host_ip:
            return self._host_ip
        try:
            self._host_ip = get_local_ip()
        except Exception as e:
            self.log(f"获取内网IP失败: {e}", level="error")
            self._host_ip = "unknown"
        return self._host_ip

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

    async def set_status(self, status_id, data=None, expire_time=None):
        status_queue = self.get_queue(status_id, base=self.status_queue)
        expire_time = expire_time or setting.EXPIRE_TIME
        if data is not None:
            await self.redis.set(status_queue, data, ex=expire_time)
        if await self.redis.exists(status_id):
            await self.redis.expire(status_queue, expire_time)

    async def get_status(self, status_id):
        status_queue = self.get_queue(status_id, base=self.status_queue)
        return await self.redis.get(status_queue)

    async def del_status(self, status_id):
        status_queue = self.get_queue(status_id, base=self.status_queue)
        return await self.redis.delete(status_queue)

    async def heartbeat(self):
        interval = 5
        while True:
            h_key = self.get_queue(self.__class__.__name__.lower(), self.get_host_ip(), base=self.queue_name)
            await self.redis.set(h_key, value=json.dumps(self.info), ex=interval + 1)
            await asyncio.sleep(interval)


if __name__ == '__main__':
    pass
