# -*- coding: utf-8 -*-
"""
@File    : agent.py
@Author  : yintian
@Date    : 2025/10/21 11:33
@Software: PyCharm
@Desc    : 
"""
import asyncio
import contextlib
from typing import Callable, Any

from ytools import logger
from ytools.arq import setting
from ytools.arq.client.base import BaseClient
from ytools.arq.task.task import Task
class AsyncNullContext:
    async def __aenter__(self):
        return None
    async def __aexit__(self, exc_type, exc, tb):
        return False

class Agent(BaseClient):
    def __init__(self, worker: Callable[[Task], Any], max_concurrency=None, **kwargs):
        self.worker = worker
        super().__init__(**kwargs)
        if max_concurrency:
            self.context = asyncio.Semaphore(max_concurrency)
        else:
            self.context = contextlib.nullcontext()

    async def do(self, task):
        async with self.context:
            try:
                res = await self.worker(task)
            except Exception as e:
                res = f"ERROR::{type(e)}|{str(e)}"
            await self.put_result(res, task)

    async def run(self):
        while True:
            try:
                task: Task = await self.get_task()
                if not task:
                    continue
                asyncio.create_task(self.do(task))
            finally:
                await asyncio.sleep(setting.INTERVAL)

    async def get_task(self):
        task_id = await self.zpop(self.tasks_queue)
        if not task_id:
            return None
        data = await self.redis.get(self.get_queue(task_id, base=self.data_queue))
        if data is None:
            logger.error(f"task_id 未获取到数据")
            return None
        return Task(
            data=data,
            client=self,
            task_id=task_id
        )

    async def zpop(self, key: str):
        async with self.redis.pipeline(transaction=True) as pipe:
            # 取出最小分数的任务
            await pipe.zrange(key, 0, 0, withscores=False)
            # 删除它
            await pipe.zremrangebyrank(key, 0, 0)
            result, _ = await pipe.execute()

        if result:
            return result[0].decode() if isinstance(result[0], bytes) else result[0]
        return None

    async def put_result(self, result, task):
        result_queue = self.get_queue(task.task_id, base=self.result_queue)
        data = task.encode_data(result)
        await self.redis.publish(result_queue, data)


if __name__ == '__main__':
    pass
