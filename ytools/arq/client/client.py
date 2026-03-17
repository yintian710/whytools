# -*- coding: utf-8 -*-
"""
@File    : Client.py
@Author  : yintian
@Date    : 2025/10/21 10:20
@Software: PyCharm
@Desc    : 
"""
import asyncio
import inspect
from typing import Literal
from uuid import uuid4

from redis.asyncio.client import Pipeline

from ytools.arq import setting
from ytools.arq.client.base import BaseClient
from ytools.arq.task.task import Task


class Client(BaseClient):
    max_sleep_time = 5

    def __init__(self, *args, max_task_num: int = None, max_action: Literal["sleep", "break", "raise"] = "sleep", **kwargs):
        self.max_task_num = max_task_num
        self.max_action = max_action
        super().__init__(*args, **kwargs)

    async def put(self, data, task_id=None, **kwargs):
        task_id = task_id or str(uuid4())
        task = Task(data=data, client=self, task_id=task_id, result_queue=self.get_queue(task_id, base=self.result_queue), **kwargs)
        await self.put_task(task, kwargs.get('auto_ensure', False))
        return task

    async def put_task(self, task: Task, auto_ensure=False):
        data_queue = self.get_queue(task.task_id, base=self.data_queue)

        auto_ensure and await task.ensure()
        async with self.redis.pipeline(transaction=True) as pipe:
            if self.max_task_num and await self.check_max(pipe):
                return
            await pipe.zadd(self.tasks_queue, {task.task_id: task.score})
            await pipe.set(data_queue, task.encode_data(), ex=setting.EXPIRE_TIME)
            results = await pipe.execute()
            if not all(results):  # 检查是否有命令失败
                raise ValueError(f"投放任务至队列失败: {results}")
            self.task_count.increment()

    async def check_max(self, pipe: Pipeline):
        while True:
            now_task_num = await pipe.zcard(self.tasks_queue)
            if now_task_num >= self.max_task_num:
                if self.max_action == "sleep":
                    self.log(f"当前任务数量: {now_task_num} 超出最大任务数: {self.max_task_num}, 等待任务消费, 休眠 {self.max_sleep_time}s...")
                    await asyncio.sleep(self.max_sleep_time)
                elif self.max_action == "break":
                    return True
                else:
                    raise ValueError("超出最大任务数")

    @staticmethod
    async def get_result(task: Task, timeout=None, timeout_back=None):
        res = await task.get_result(timeout=timeout, timeout_back=timeout_back)
        return res

    async def get_result_by_id(self, task_id, timeout=None, timeout_back=None):
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
            except asyncio.TimeoutError:
                if inspect.iscoroutinefunction(timeout_back):
                    await timeout_back()
                elif inspect.isawaitable(timeout_back):
                    await timeout_back
                elif timeout_back:
                    timeout_back()
                raise
            finally:
                done_future.cancel()
        finally:
            await pubsub.unsubscribe(result_queue)
            await pubsub.close()


if __name__ == '__main__':
    pass
