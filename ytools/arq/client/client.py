# -*- coding: utf-8 -*-
"""
@File    : Client.py
@Author  : yintian
@Date    : 2025/10/21 10:20
@Software: PyCharm
@Desc    : 
"""
import asyncio
from uuid import uuid4

from ytools.arq import setting
from ytools.arq.client.base import BaseClient
from ytools.arq.task.task import Task


class Client(BaseClient):

    async def put(self, data, task_id=None, **kwargs):
        task_id = task_id or str(uuid4())
        task = Task(data=data, client=self, task_id=task_id, result_queue=self.get_queue(task_id, base=self.result_queue), **kwargs)
        await self.put_task(task, kwargs.get('auto_ensure', False))
        return task

    async def put_task(self, task: Task, auto_ensure=False):
        data_queue = self.get_queue(task.task_id, base=self.data_queue)

        auto_ensure and await task.ensure()
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.zadd(self.tasks_queue, {task.task_id: task.score})
            await pipe.set(data_queue, task.encode_data(), ex=setting.EXPIRE_TIME)
            results = await pipe.execute()
            if not all(results):  # 检查是否有命令失败
                raise ValueError(f"投放任务至队列失败: {results}")
            self.task_count.increment()
        # add_res = await self.redis.zadd(self.tasks_queue, {task.task_id: task.score})
        # data_res = await self.redis.set(data_queue, task.encode_data(), ex=setting.EXPIRE_TIME)
        # results = {
        #     "add": add_res,
        #     "data": data_res
        # }
        # if not all(results.values()):  # 检查是否有命令失败
        #     raise ValueError(f"投放任务至队列失败: {results}")

    @staticmethod
    async def get_result(task: Task, timeout=None):
        res = await task.get_result(timeout=timeout)
        return res

    async def get_result_by_id(self, task_id, timeout=None):
        result_queue = self.get_queue(task_id, base=self.result_queue)
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(result_queue)

        async def get_result():
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    return msg["data"]

        try:
            done_future = asyncio.ensure_future(get_result())
            try:
                res = await asyncio.wait_for(done_future, timeout=timeout)
                return res
            finally:
                done_future.cancel()
        finally:
            await pubsub.unsubscribe(result_queue)
            await pubsub.close()


if __name__ == '__main__':
    pass
