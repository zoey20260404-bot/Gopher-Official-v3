# Python 学习笔记（面向 Agent/RAG 项目｜有Go后端背景）
> 目标：用于个人Agent项目开发、面试广深自研小公司；剔除无关内容，只保留刚需知识点

## 一、环境准备（venv虚拟环境）
```bash
# 创建虚拟环境
python -m venv agent-env
# Windows激活
agent-env\Scripts\activate
# Mac/Linux激活
source agent-env/bin/activate
# 退出虚拟环境
deactivate
```

## 二、基础语法
### 1. 变量与打印
```python
# 打印
print("hello")

# 变量，无需声明类型
name = "test"
age = 20
flag = True  # 布尔首字母大写 True / False
num = 3.14

# f-string字符串插值
s = f"名字：{name}, 年龄：{age}"
print(s)
```

### 2. 容器类型（对标Go slice、map）
#### list 列表（可变，对应slice）
```python
arr = [1,2,3,"abc"]
print(arr[0])       # 索引取值
arr.append(4)       # 追加元素
arr.pop()           # 删除末尾元素
arr[1] = 99         # 修改元素
print(arr[1:3])     # 切片，左闭右开 [1,3)
```

#### dict 字典（对应map）
```python
d = {"name":"zhangsan", "age":20}
print(d["name"])
d["age"] = 21        # 修改key
d["city"] = "gz"     # 新增key
del d["city"]        # 删除key

# 安全获取key，不存在返回默认值，不抛异常
val = d.get("city", "默认值")
```

### 3. 条件判断（Python依靠缩进，无大括号）
```python
score = 80
if score >= 90:
    print("A")
elif score >= 60:
    print("B")
else:
    print("C")
```

### 4. 循环 for / while
```python
# for遍历列表
nums = [10,20,30]
for n in nums:
    print(n)

# range生成序列 range(5) → 0,1,2,3,4
for i in range(5):
    print(i)

# while循环
i = 0
while i < 3:
    print(i)
    i += 1

# break / continue 用法同Go
```

### 5. 函数 def
```python
# 定义函数
def add(a, b):
    return a + b

res = add(2,3)
print(res)

# 默认参数
def say(msg="hi"):
    print(msg)
say()
say("hello")
```

### 6. 模块导入 import
```python
# 导入整个模块
import json
data = {"a":1}
s = json.dumps(data) # 对象转json字符串
obj = json.loads(s)  # json字符串转回对象

# 导入模块内指定函数
from json import dumps
s = dumps(data)
```

### 7. 文件读写
```python
# 读文本
with open("test.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 写文本
with open("out.txt", "w", encoding="utf-8") as f:
    f.write("写入内容")
```

### 8. 类 class（对标Go struct + 方法）
```python
class User:
    # 构造函数，实例化自动执行
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def hello(self):
        print(f"我是{self.name}")

# 创建实例
u = User("张三", 20)
u.hello()
print(u.name)
```

### 9. 异常捕获 try except
```python
try:
    num = 1 / 0
except Exception as e:
    print("出错：", e)
```

### 10. 同步HTTP请求 requests
```bash
pip install requests
```
```python
import requests

url = "https://xxx"
resp = requests.get(url, timeout=10)
print(resp.text)

# post json
payload = {"msg":"hi"}
resp = requests.post(url, json=payload)
```

## 三、异步 asyncio（重点，Agent并发调用LLM核心）
> Python asyncio：单线程事件驱动协程；适合IO密集场景，和Go goroutine M:N调度不同。
> 禁止在async函数内直接使用`time.sleep()`、`requests`（阻塞事件循环）

### 1. async / await 基础语法
- `async def`：定义异步函数，调用返回协程对象，不会直接执行
- `await`：只能写在async函数内部，交出事件循环，等待IO完成
```python
import asyncio

async def hello(name):
    print(f"start {name}")
    await asyncio.sleep(2) # 异步休眠，非阻塞
    print(f"end {name}")
    return f"ret:{name}"

async def main():
    # 串行执行
    res1 = await hello("A")
    res2 = await hello("B")
    print(res1, res2)

asyncio.run(main())
```

### 2. create_task 创建协程任务（并发）
```python
import asyncio

async def hello(name):
    print(f"start {name}")
    await asyncio.sleep(2)
    print(f"end {name}")
    return f"ret:{name}"

async def main():
    task1 = asyncio.create_task(hello("A"))
    task2 = asyncio.create_task(hello("B"))
    res1 = await task1
    res2 = await task2
    print(res1, res2)

asyncio.run(main())
```

### 3. asyncio.gather 批量等待多个任务
```python
import asyncio

async def hello(name):
    await asyncio.sleep(2)
    return f"ret:{name}"

async def main():
    # return_exceptions=True：单个任务异常不中断全部任务
    results = await asyncio.gather(
        hello("A"),
        hello("B"),
        hello("C"),
        return_exceptions=True
    )
    print(results)

asyncio.run(main())
```

### 4. 任务控制：取消、超时
#### 任务 cancel
```python
import asyncio

async def work():
    await asyncio.sleep(5)
    return "done"

async def main():
    task = asyncio.create_task(work())
    await asyncio.sleep(1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("任务被取消")

asyncio.run(main())
```
#### wait_for 超时控制
```python
import asyncio

async def slow():
    await asyncio.sleep(5)
    return "ok"

async def main():
    try:
        res = await asyncio.wait_for(slow(), timeout=3)
    except asyncio.TimeoutError:
        print("超时")

asyncio.run(main())
```

### 5. asyncio.Queue 协程安全队列（对标Go channel，生产者消费者）
```python
import asyncio

async def producer(q: asyncio.Queue):
    for i in range(3):
        await q.put(f"item{i}")
        print(f"生产 item{i}")
        await asyncio.sleep(0.5)

async def consumer(q: asyncio.Queue):
    while True:
        item = await q.get()
        print(f"消费 {item}")
        await asyncio.sleep(1)
        q.task_done() # 标记任务完成

async def main():
    q = asyncio.Queue(maxsize=5)
    consumer_task = asyncio.create_task(consumer(q))
    await producer(q)
    await q.join()
    consumer_task.cancel()

asyncio.run(main())
```

### 6. asyncio.Lock 协程锁（对标sync.Mutex）
```python
import asyncio

lock = asyncio.Lock()
cnt = 0

async def inc():
    global cnt
    async with lock:
        tmp = cnt
        await asyncio.sleep(0.01)
        cnt = tmp + 1

async def main():
    tasks = [asyncio.create_task(inc()) for _ in range(100)]
    await asyncio.gather(*tasks)
    print(cnt)

asyncio.run(main())
```

### 7. Semaphore 信号量（接口限流，Agent调用LLM必备）
```python
import asyncio

# 最大并发数2
sem = asyncio.Semaphore(2)

async def request_api(name):
    async with sem:
        print(f"开始请求 {name}")
        await asyncio.sleep(2)
        print(f"结束请求 {name}")

async def main():
    tasks = [asyncio.create_task(request_api(i)) for i in range(5)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

### 8. aiohttp 异步HTTP客户端（替换同步requests）
```bash
pip install aiohttp
```
```python
import aiohttp
import asyncio

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            return await resp.text()

async def main():
    res = await fetch("https://httpbin.org/get")
    print(res)

asyncio.run(main())
```

### 9. aiofiles 异步文件读写
```bash
pip install aiofiles
```
```python
import aiofiles
import asyncio

async def read_file(path):
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return await f.read()

async def write_file(path, content):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)
```
> 知识点：`async with` 是**异步上下文管理器**，对象实现`__aenter__` / `__aexit__`；普通`with`只支持同步`__enter__` / `__exit__`。异步对象必须用`async with`，内部异步方法需要`await`。

### 10. asyncio.to_thread() 将同步代码丢入线程池（防止阻塞事件循环）
```python
import asyncio
import time

def sync_work():
    time.sleep(2)
    return "同步结果"

async def main():
    res = await asyncio.to_thread(sync_work)
    print(res)

asyncio.run(main())
```

### 11. asyncio异常处理
```python
import asyncio

async def err_func():
    raise Exception("出错了")

async def main():
    try:
        await err_func()
    except Exception as e:
        print("捕获异常：", e)

asyncio.run(main())
```

### 12. asyncio vs Go goroutine 关键差异
1. Go：M:N调度，可多核并行；asyncio单线程事件循环，CPU密集任务无法并行，只适合IO密集
2. Go：goroutine轻量；asyncio task同样轻量，但受GIL限制
3. Go：chan原生通信；Python使用`asyncio.Queue`
4. ❌ 禁止async函数内直接调用同步阻塞代码，会卡死事件循环

## 四、Python语言进阶（Agent、LangGraph高频）
### 1. 生成器 yield / yield from（LLM流式输出核心）
```python
def stream_resp():
    yield "片段1"
    yield "片段2"
    yield "片段3"

for chunk in stream_resp():
    print(chunk)

# 异步生成器（async yield）
async def async_stream():
    yield "chunk1"
    yield "chunk2"
```

### 2. 装饰器 decorator + *args / **kwargs
```python
def log(func):
    def wrapper(*args, **kwargs):
        print("调用前")
        res = func(*args, **kwargs)
        print("调用后")
        return res
    return wrapper

@log
def hello():
    print("hello")
```
- `*args`：打包多个位置参数为元组
- `**kwargs`：打包关键字参数为字典
> LangChain `@tool` 本质就是装饰器

### 3. 类型注解 typing
```python
from typing import List, Dict, Optional

def add(a:int, b:int) -> int:
    return a + b

# Optional：可以为类型或者None
def get_val() -> Optional[int]:
    return None
```

### 4. dataclasses 数据类（替代手写class，对标Go struct，LangGraph State常用）
```python
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

msg = Message(role="user", content="hi")
print(msg.role)
```

### 5. 异常进阶 raise / finally
```python
try:
    1/0
except ZeroDivisionError as e:
    print("除零")
except Exception as e:
    print("通用异常")
finally:
    print("一定会执行，释放资源")
```

### 6. 模块与包 `__init__.py`
目录结构示例
```
agent_project/
├── __init__.py
├── main.py
├── tools/
    ├── __init__.py
    └── search.py
```
- `__init__.py` 标识文件夹为Python包
- `from tools.search import xxx` 导入
- `.` 当前包，`..` 上层包，相对导入

### 7. re 正则（RAG文本清洗、提取结构化内容）
```python
import re
text = "答案：123"
res = re.search(r"答案：(\d+)", text)
if res:
    print(res.group(1))
```

## 五、标准库（Agent项目刚需）
1. `uuid`：生成会话ID、文档唯一ID
2. `base64`：多模态图片处理可选
3. `re`：正则文本处理

## 六、包管理 & 工程化
### requirements.txt
```txt
langchain
langgraph
aiohttp
chromadb
pydantic
```
```bash
# 导出依赖
pip freeze > requirements.txt
# 批量安装
pip install -r requirements.txt
```
核心概念：虚拟环境隔离，解决包版本冲突。

## 七、Agent生态库（项目核心）
### Pydantic 数据校验（工具调用参数校验）
```bash
pip install pydantic
```
```python
from pydantic import BaseModel
class SearchInput(BaseModel):
    query: str
```
> LangChain @tool底层依赖Pydantic做参数校验

### LangChain 组件
- Document、RecursiveCharacterTextSplitter 文档切分
- PromptTemplate、ChatPromptTemplate
- Embeddings 向量嵌入
- Chroma 本地向量库

### LangGraph（Agent核心）
- StateGraph 状态图
- Node节点、Edge边、条件分支
- 异步调用、流式输出

## 八、面试知识点（Python底层）
### GIL 全局解释器锁
> 同一时刻，一个线程只能执行一段Python字节码；多线程无法并行CPU密集任务；IO密集、asyncio协程不受GIL的性能影响。

### 内存管理
引用计数 + 垃圾回收，简单了解概念即可。

## 九、可直接跳过的内容（不用学习）
- numpy / pandas 数据分析
- GUI（tkinter）
- Flask/Django完整web（FastAPI可选简单了解，非必需）
- C扩展、ctypes
- multiprocessing多进程（仅了解概念）
- pytest单元测试（有余力再学）

## 十、学习优先级顺序
1. `*args / **kwargs` + 装饰器
2. 生成器（普通+异步生成器，LLM stream流式输出）
3. typing类型注解 + dataclasses
4. re正则表达式
5. pydantic
6. 包/模块管理，项目目录组织
7. GIL概念（面试背诵）

---

如果你需要，我可以继续往下写：**LangGraph最小Agent完整可运行demo（markdown）**。