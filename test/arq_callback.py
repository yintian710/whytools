# -*- coding: utf-8 -*-
"""
@File    : arq_callback.py
@Author  : yintian
@Date    : 2025/11/5 11:25
@Software: PyCharm
@Desc    : 
"""
import asyncio

import loguru

from ytools.arq.client.agent import Agent
from ytools.arq.task.task import Task


async def consumer(task: Task):
    loguru.logger.debug(task.task_id)
    return task.data


async def p():
    print(1)


def p2():
    print(2)


async def main():
    client = Agent(worker=consumer, redis={"host": "10.238.60.107", "port": 6379, "db": 15, "password": "123456"})

    task1 = Task(1, client, callback=p)
    if task1.callback:
        await client.callback(task1, "")
    task2 = Task(2, client, callback=p2)
    if task2.callback:
        await client.callback(task2, "")
    # await client.run()


if __name__ == '__main__':
    asyncio.run(main())
