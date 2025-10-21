# -*- coding: utf-8 -*-
"""
@File    : arq_get.py
@Author  : yintian
@Date    : 2025/10/21 14:01
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


async def main():
    client = Agent(worker=consumer, redis={"host": "10.238.60.107", "port": 6379, "db": 15, "password": "123456"})
    await client.run()


if __name__ == '__main__':
    asyncio.run(main())
