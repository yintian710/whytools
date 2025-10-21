# -*- coding: utf-8 -*-
"""
@File    : arq_put.py
@Author  : yintian
@Date    : 2025/10/21 14:01
@Software: PyCharm
@Desc    : 
"""
import asyncio

from ytools.arq.client.client import Client


async def main():
    client = Client(redis={"host": "10.238.60.107", "port": 6379, "db": 15, "password": "123456"})
    task = await client.put({"1": 2})
    res = await client.result(task, timeout=5)
    print(res)


if __name__ == '__main__':
    asyncio.run(main())
