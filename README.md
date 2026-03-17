# ytools

一个偏“脚手架 / 内部工具箱”风格的 Python 工具集合，面向脚本开发、自动化、爬虫/RPA、异步任务分发和一些常见的胶水代码场景。

这个项目不是单一职责库，而是把一批作者常用能力放进了同一个包里，按需导入即可。

> 代码中的发布名是 `why-tools`，实际导入名是 `ytools`
>  
> 代码要求 Python `>=3.8`

## 这个项目有什么功能

- 动态依赖与反射工具：按字符串加载对象、自动补齐函数参数、统一调用同步/异步函数
- 变量容器：提供全局级、线程级、协程级变量空间，并支持类型约束、过期次数和过期时间
- HTTP 数据模型：封装 `Request`、`Response`、`Header`、`Cookies`，便于保存、转换和解析请求/响应数据
- 数据提取：支持 `xpath`、`json/jmespath`、`jsonpath`、`regex` 多种提取方式
- Redis 异步任务队列：提供生产者 `Client`、消费者 `Agent`、任务对象 `Task`
- 浏览器自动化辅助：基于 `DrissionPage` 封装页面流转、元素查找、点击输入、网络拦截和响应改写
- 轨迹录制与回放：录制 PC / Android 的滑轨轨迹，并按距离生成可复用轨迹
- 通知能力：发送企业微信机器人消息
- 其他常用工具：日志、时间、加密、退出回调、版本号处理、链表/树节点、计数器、本机 IP 等

## 项目结构

| 模块 | 作用 | 入口对象 |
| --- | --- | --- |
| `ytools.utils.magic` | 动态加载对象、自动安装依赖、智能调用函数 | `require` `load_object` `prepare` `result` |
| `ytools.utils.variable` | 全局 / 线程 / 协程变量容器 | `VariableG` `VariableT` `VariableC` |
| `ytools.network` | 请求/响应数据模型与解析 | `Request` `Response` `Header` `Cookies` |
| `ytools.utils.extractors` | xpath / json / jsonpath / regex 提取器 | `Rule` `Group` `XpathExtractor` 等 |
| `ytools.arq` | 基于 Redis 的轻量任务队列 | `Client` `Agent` `Task` |
| `ytools.auto_driver.dp` | DrissionPage 自动化与请求拦截 | `DpRpaBase` `Route` |
| `ytools.alert.wechat` | 企业微信机器人通知 | `send_wechat` `send_msg` |
| `ytools.utils.track` / `ytools.auto_driver.track` | 轨迹录制、轨迹生成 | `listener` `get_track` |

## 安装

### 本地开发安装

推荐直接在项目目录安装：

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 关于可选依赖

这个项目大量使用 `ytools.utils.magic.require()` 按需加载依赖。也就是说：

- 某些模块第一次导入时，会自动检查依赖是否已安装
- 如果机器上有 `uv`，默认优先走 `uv add`
- 否则会退回 `pip install`

常见的可选依赖包括：

```bash
python -m pip install packaging redis arrow jmespath jsonpath lxml w3lib requests httpx pynput DrissionPage
```

如果你不希望运行时自动修改环境，建议提前手动装好这些包。

### 安装注意事项

- 不要直接执行 `python setup.py`
- 这个仓库里的 `setup.py` 在“无参数启动”时会进入打包上传逻辑
- 正常使用请走 `pip install -e .`、`pip install .` 或构建工具链

## 快速开始

### 1) 常用胶水工具

`ytools.utils.magic` 是整个项目里复用最广的基础模块。

```python
from ytools.utils.magic import load_object, result, json_or_eval

pow_func = load_object("math.pow")
print(pow_func(2, 10))  # 1024.0

# 自动补参数、统一执行
value = result("math.pow", args=[2, 8])
print(value)  # 256.0

print(json_or_eval('{"name": "ytools", "ok": true}'))
```

适合这些场景：

- 配置里写函数路径，运行时再加载
- 同步 / 异步函数统一调度
- 给回调函数自动补 `kwargs`
- 快速把 JSON / 类 JSON 字符串还原成对象

### 2) 变量空间

根包里预留了 3 类变量容器：

- `G`：全局共享
- `T`：线程隔离
- `C`：协程隔离

使用前先初始化：

```python
import ytools

ytools.init_var("G")
ytools.init_var("T")
ytools.init_var("C")
```

#### 基础用法

```python
import ytools

ytools.init_var("G")

ytools.G.user = {"name": "zz"}
ytools.G["count"] = 1

print(ytools.G.user)      # {'name': 'zz'}
print(ytools.G["count"])  # 1
```

#### 类型化变量

`VariableG` 支持把变量和类型绑定在一起。

```python
import ytools

ytools.init_var("G")

ytools.G["int:retry"] = 1
ytools.G["int:retry"] += 1
print(ytools.G["int:retry"])  # 2

# _list.todos 会自动按 list 类型创建默认值
ytools.G._list.todos.append("write readme")
print(ytools.G._list.todos)   # ['write readme']
```

#### 过期控制

```python
import ytools

ytools.init_var("G")
ytools.G.set("token", "abc", max_count=3, expire_ts=60)
```

其中：

- `max_count`：最多可使用次数
- `expire_ts`：相对秒数

### 3) Request / Response 模型

`ytools.network` 提供的是“请求/响应对象模型”，不是直接发请求的下载器。

你可以把它当成：

- curl 和结构化请求之间的转换工具
- 下载器结果的统一封装对象
- 后续提取、调试、保存的中间层

```python
from ytools.network import Request, Response

req = Request(
    url="https://example.com/api",
    params={"page": 1},
    method="POST",
    json_data={"name": "demo"},
    headers={"Content-Type": "application/json"},
)

print(req.real_url)
print(req.curl)

res = Response(
    content='{"items": [{"name": "A"}]}',
    headers={"Content-Type": "application/json"},
    url=req.real_url,
    request=req,
)

print(res.json())
print(res.get("items[0].name"))
```

#### 从 curl 导入

```python
from ytools.network import Request

req = Request.from_curl(
    "curl 'https://example.com?a=1' -H 'User-Agent: demo' --data 'x=1'"
)
print(req.method)
print(req.headers)
print(req.curl)
```

#### 响应提取

```python
from ytools.network import Response

res = Response(
    content="""
    <html><body><h1>Hello</h1></body></html>
    """,
    headers={"Content-Type": "text/html; charset=utf-8"},
)

print(res.xpath_first("//h1/text()"))     # Hello
print(res.re_first(r"<h1>(.*?)</h1>"))    # Hello
```

常用方法：

- `res.json()`：反序列化 JSON / JSONP
- `res.get(rule)`：用 `jmespath` 取值
- `res.jsonpath(expr)`：用 `jsonpath` 取值
- `res.xpath(expr)`：用 xpath 取值
- `res.re(regex)`：用正则提取

## 数据提取规则

`ytools.utils.extractors` 提供一层更灵活的规则表达。

```python
from ytools.utils.extractors import Rule
from ytools.network import Response

res = Response(content='{"name": "demo", "items": [{"id": 1}]}')

rules = {
    "name": Rule("name"),
    "first_id": Rule("items[0].id"),
}

print(res.extract("JSON", rules))
```

你可以用它做：

- 多字段批量抽取
- 字段兜底
- 条件命中
- 前置 / 后置处理
- 将嵌套结构展开成行数据

## Redis 异步任务队列

`ytools.arq` 是项目内置的一套轻量任务队列，不是外部那个同名框架。

### 核心角色

- `Client`：投递任务、等待结果
- `Agent`：消费任务、执行函数、回写结果
- `Task`：任务体，负责编码、解码、状态管理

### 生产者

```python
import asyncio

from ytools.arq import setting
from ytools.arq.client.client import Client

setting.OBJ_DATA = True


async def main():
    client = Client(redis={"host": "127.0.0.1", "port": 6379, "db": 0})

    task = await client.put(
        {
            "func": "math.pow",
            "args": [2, 10],
        },
        auto_ensure=True,
    )

    raw = await client.get_result(task, timeout=5)
    print(task.decode_data(raw))


asyncio.run(main())
```

### 消费者

```python
import asyncio

from ytools.arq.client.agent import Agent
from ytools.arq.task.task import Task


async def worker(task: Task):
    payload = task.decode_data() if isinstance(task.data, (str, bytes)) else task.data
    return {"ok": True, "payload": payload}


async def main():
    agent = Agent(
        worker=worker,
        redis={"host": "127.0.0.1", "port": 6379, "db": 0},
        max_concurrency=10,
    )
    await agent.run()


asyncio.run(main())
```

### 队列特性

- 任务按 `score` 进入 Redis 有序集合
- 可选加密：通过 `ytools.arq.setting.ENCRYPT` 控制
- 结果通过 Redis pub/sub 回传
- 内置心跳：客户端和消费者会定期上报自身信息
- 支持任务状态读写：`set_status` / `get_status` / `del_status`

## 浏览器自动化与请求拦截

这一部分依赖 `DrissionPage`，主要分两类：

- `DpRpaBase`：页面流转、元素查找、点击输入、标签页管理
- `Route` / `route_by_fetch.Route`：在浏览器里拦截请求或响应，并动态改写内容

### RPA 基类

`DpRpaBase` 在 `RPAControl` 基础上抽象了“当前页面在哪、下一步去哪里、处于某个页面时做什么”这套流程控制方式。

你可以继承它，实现：

- `where()`：当前页面状态识别
- `where_in_xxx()`：当处于某页面时执行什么动作
- `a_to_b()`：从页面 A 导航到页面 B

同时直接复用这些现成能力：

- `find()`：按定位表达式找元素
- `click()`：点击元素
- `input()`：输入文本
- `goto()`：打开页面
- `re_tab()` / `close_other_tab()`：整理标签页
- `run_slider()`：按轨迹拖动滑块

### 拦截响应并改写

```python
from DrissionPage._configs.chromium_options import ChromiumOptions
from DrissionPage._pages.chromium_page import ChromiumPage

from ytools.auto_driver.dp.route_by_fetch import Route, RouteResponse


def mock_res(response: RouteResponse):
    response.text = response.text.replace("old-version", "new-version")
    response.full_headers = {
        **response.headers,
        "content-length": str(len(response.full_content)),
    }


opt = ChromiumOptions()
browser = ChromiumPage(opt)

Route.start_by_driver(browser.driver)
Route.on("response", "main.js", mock_res)

browser.get("https://example.com")
```

适合这些场景：

- 调试前端接口
- 本地 mock 某个 JS / JSON 响应
- 修改请求头、请求体
- 观察关键接口流量

## 轨迹录制与滑块轨迹

`ytools.utils.track` 和 `ytools.auto_driver.track` 用来录制轨迹、保存轨迹、按目标距离生成一段“看起来更像人工”的滑动轨迹。

典型用途：

- 滑块验证码
- 鼠标轨迹采样
- Android 触摸轨迹采样

示例：

```python
from ytools.auto_driver.track import get_track

track = get_track(distance=180, file_name="fast.json")
print(track[:5])
```

## 企业微信通知

```python
from ytools.alert.wechat import send_msg

send_msg(
    {"service": "demo", "status": "ok"},
    to=["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"],
    title="部署通知",
)
```

支持：

- 纯文本消息 `send_wechat(..., msg_type="text")`
- Markdown 消息 `send_msg(...)`
- 异步发送 `async_send_wechat()` / `async_send_msg()`

## 其他常用工具

### 时间

```python
from ytools.utils.date import Arrow

now = Arrow.now()
print(now.format())
print(now.start("day"))
print(now.end("day"))
print(now.ts(13))
```

### 加密与编码

```python
from ytools.utils.encrypt import md5, to_b64, from_b64

print(md5({"a": 1}))
token = to_b64("hello")
print(from_b64(token))
```

### 退出回调

```python
from ytools.utils.quiter import at_exit

at_exit(lambda: print("program exit"))
```

### 计数器

```python
from ytools.utils.counter import FastWriteCounter

counter = FastWriteCounter()
counter.increment()
counter.increment()
print(counter.value)
```

## 建议的使用方式

如果你第一次接触这个项目，建议按下面顺序理解：

1. 先看 `test/test_var.py`，了解变量容器怎么用
2. 再看 `test/arq_put.py`、`test/arq_get.py`，了解任务队列
3. 如果你做浏览器自动化，再看 `test/route_test.py`
4. 最后按需读 `ytools/utils/magic.py`，它是整个项目的基础胶水层

## 当前更适合什么场景

这个项目更适合：

- 内部工具脚本
- 自动化任务
- 爬虫 / 抓包辅助
- Redis 分发型任务系统
- 基于浏览器驱动的 RPA 场景

如果你需要的是：

- 成熟统一的 Web 框架
- 标准化 HTTP 客户端
- 强约束、强稳定性的公共 SDK

那这个项目更像一个“工具箱”，而不是完整框架。

## 已知注意点

- 很多模块是“按需依赖”，首次使用可能触发自动安装
- `network` 模块是请求/响应模型，不负责真正发 HTTP 请求
- `auto_driver` 强依赖浏览器环境和 `DrissionPage`
- `cache_utils.py` / `cache.py` 里有一部分缓存装饰器接口仍偏实验状态，更适合按源码理解后再使用
- `setup.py` 无参数执行会进入上传逻辑，日常开发不要直接跑

## 版本

当前仓库内版本文件为：

```text
0.2.24
```

