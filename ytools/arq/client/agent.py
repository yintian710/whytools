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
import inspect
from asyncio import Event
from typing import Callable, Any

from ytools.arq import setting
from ytools.arq.client.base import BaseClient
from ytools.arq.task.task import Task
from ytools.utils import magic
from ytools.utils.counter import FastWriteCounter


class Agent(BaseClient):
    def __init__(self, worker: Callable[[Task], Any] | None = None, max_concurrency=None, **kwargs):
        super().__init__(**kwargs)
        self.worker = worker or self.run_task
        self.success_tasks = FastWriteCounter()
        self.extra = {
            "success_tasks": self.success_tasks.value,
        }
        if max_concurrency:
            self.context = asyncio.Semaphore(max_concurrency)
        else:
            self.context = contextlib.nullcontext()

    async def do(self, task):
        async with self.context:
            try:
                res = self.worker(task)
                if inspect.isawaitable(res):
                    res = await res
            except Exception as e:
                self.log(f"执行任务失败 task_id={task.task_id}: {type(e).__name__}: {e}", level="error")
                res = f"ERROR::{type(e)}|{str(e)}"
            await self.put_result(res, task)
            self.success_tasks.increment()
            self.extra["success_tasks"] = self.success_tasks.value
            if task.callback:
                asyncio.create_task(self.callback(task, res))

    async def run_task(self, task: Task):
        payload = task.data
        if isinstance(payload, (str, bytes)):
            with contextlib.suppress(Exception):
                payload = task.decode_data()
        self.log(f"收到任务 task_id={task.task_id}: {payload}")
        result = await self.execute_task(task, payload)
        self.log(f"任务结果 task_id={task.task_id}: {result}")
        return result

    @staticmethod
    def normalize_task_payload(payload):
        if not isinstance(payload, dict):
            return None
        func = payload.get("func")
        if func is None:
            return None
        args = payload.get("args", ())
        kwargs = payload.get("kwargs", {})
        if not isinstance(args, (list, tuple)):
            args = (args,)
        if kwargs is None:
            kwargs = {}
        if not isinstance(kwargs, dict):
            raise TypeError("task kwargs 必须为 dict")
        return func, tuple(args), kwargs

    async def execute_task(self, task: Task, payload):
        normalized = self.normalize_task_payload(payload)
        if normalized is None:
            return payload
        func, args, kwargs = normalized
        return await magic.async_result(
            func,
            args=args,
            kwargs=kwargs,
            namespace={"task": task},
        )

    async def callback(self, task: Task, res):
        try:
            pre = magic.prepare(task.callback, task=task, res=res, result=res)
            if pre.is_async:
                await pre()
            else:
                pre()

        except Exception as e:
            self.log(f"执行 callback 报错: {e}", level="error")

    async def run(self, event: Event = None):
        while True:
            try:
                if event and event.is_set():
                    await asyncio.sleep(setting.INTERVAL)
                    continue
                task: Task = await self.get_task()
                if not task:
                    continue
                self.task_count.increment()
                asyncio.create_task(self.do(task))
            finally:
                await asyncio.sleep(setting.INTERVAL)

    async def get_task(self):
        task_id = await self.zpop(self.tasks_queue)
        if not task_id:
            return None
        data = await self.redis.get(self.get_queue(task_id, base=self.data_queue))
        if data is None:
            self.log(f"task_id:{task_id} 未获取到数据", level="error")
            return None
        return Task(
            data=data,
            client=self,
            task_id=task_id,
            fmt=True
        )

    async def zpop(self, key: str):
        result = None
        if (await self.redis.info("server")).get("redis_version", "0.0.0") >= "5.0.0":
            result = await self.redis.zpopmin(self.tasks_queue, count=1)
            result = result and result[0]
        else:
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
