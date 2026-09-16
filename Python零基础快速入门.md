# Python 零基础快速入门

> 目标：用最短时间看懂并写出简单 Python 程序。
>
> 学习方法：先运行示例，再看解释。练习可以不独立完成，但至少要先猜一下运行结果，然后再看答案。

---

## 目录

1. 准备运行环境
2. 输出、注释和变量
3. 数据类型与类型转换
4. 运算符
5. 条件判断
6. 循环
7. 字符串
8. 列表、元组、字典和集合
9. 函数
10. 模块和第三方库
11. 文件读写
12. 异常处理
13. 面向对象入门
14. 常见错误与调试
15. 综合项目：记账程序
16. 下一步学习路线

---

# 1. 准备运行环境

安装 Python 3 后，在终端检查：

```bash
python --version
```

部分电脑需要使用：

```bash
python3 --version
```

创建文件 `hello.py`：

```python
print("Hello, Python!")
```

运行：

```bash
python hello.py
```

也可以暂时使用在线 Python 编辑器。初学阶段推荐使用 VS Code，并安装 Python 扩展。

## 问题 1

Python 源代码文件通常使用什么后缀？

### 答案

使用 `.py` 后缀，例如 `hello.py`。

---

# 2. 输出、注释和变量

## 2.1 输出

```python
print("你好，Python")
print(100)
print(10 + 20)
```

`print()` 用于把内容输出到屏幕。

## 2.2 注释

```python
# 这一行是注释，不会执行
print("程序开始")  # 也可以写在代码后面
```

注释用于解释代码。

## 2.3 变量

```python
name = "小明"
age = 18
height = 1.75

print(name)
print(age)
print(height)
```

可以把变量理解为一个有名字的盒子。`=` 表示把右边的值保存到左边的变量中。

变量名建议：

- 使用英文、数字和下划线；
- 不能以数字开头；
- 区分大小写，`age` 和 `Age` 是两个变量；
- 使用有意义的名字，例如 `user_name`。

## 2.4 用户输入

```python
name = input("请输入你的名字：")
print("你好，" + name)
```

`input()` 得到的结果永远是字符串。

## 问题 2

下面程序输出什么？

```python
price = 10
count = 3
print(price * count)
```

### 答案

```text
30
```

## 问题 3

写一个程序，输入姓名和城市，然后介绍自己。

### 答案

```python
name = input("请输入姓名：")
city = input("请输入城市：")
print(f"你好，我叫{name}，来自{city}。")
```

`f"..."` 叫作 f-string，可以把变量直接放进字符串的 `{}` 中。

---

# 3. 数据类型与类型转换

## 3.1 常用数据类型

```python
name = "小明"       # str，字符串
age = 18             # int，整数
height = 1.75        # float，小数
is_student = True    # bool，布尔值
nothing = None       # NoneType，空值
```

查看类型：

```python
print(type(name))
print(type(age))
```

## 3.2 类型转换

```python
text = "18"
age = int(text)
print(age + 1)

price = float("12.5")
message = str(100)
```

常用转换函数：

- `int()`：转换成整数；
- `float()`：转换成小数；
- `str()`：转换成字符串；
- `bool()`：转换成布尔值。

用户输入数字时必须转换：

```python
age = int(input("请输入年龄："))
print(f"明年你将是 {age + 1} 岁")
```

## 问题 4

为什么下面代码会报错？怎样修改？

```python
age = input("请输入年龄：")
print(age + 1)
```

### 答案

`input()` 返回字符串，字符串不能直接与整数相加。应先转换类型：

```python
age = int(input("请输入年龄："))
print(age + 1)
```

---

# 4. 运算符

## 4.1 算术运算符

```python
print(10 + 3)   # 13，加法
print(10 - 3)   # 7，减法
print(10 * 3)   # 30，乘法
print(10 / 3)   # 3.333...，除法
print(10 // 3)  # 3，整除
print(10 % 3)   # 1，余数
print(10 ** 3)  # 1000，乘方
```

## 4.2 比较运算符

比较的结果是 `True` 或 `False`：

```python
print(10 > 3)   # True
print(10 < 3)   # False
print(10 == 10) # True
print(10 != 3)  # True
print(10 >= 10) # True
print(10 <= 9)  # False
```

注意：

- `=` 是赋值；
- `==` 是判断是否相等。

## 4.3 逻辑运算符

```python
age = 20
has_ticket = True

print(age >= 18 and has_ticket)  # 两个条件都成立
print(age < 18 or has_ticket)    # 至少一个条件成立
print(not has_ticket)            # 条件取反
```

## 问题 5

判断一个整数是不是偶数。

### 答案

```python
number = int(input("请输入整数："))
print(number % 2 == 0)
```

偶数除以 2 的余数为 0。

---

# 5. 条件判断

## 5.1 if

```python
age = int(input("请输入年龄："))

if age >= 18:
    print("你已经成年")
else:
    print("你还未成年")
```

Python 使用缩进表示代码所属范围，通常使用 4 个空格。

## 5.2 多个条件

```python
score = int(input("请输入成绩："))

if score >= 90:
    print("优秀")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

程序从上向下判断，遇到第一个成立的条件后就不再继续。

## 问题 6

输入一个数字，判断它是正数、负数还是零。

### 答案

```python
number = float(input("请输入数字："))

if number > 0:
    print("正数")
elif number < 0:
    print("负数")
else:
    print("零")
```

## 问题 7

输入用户名和密码，当用户名是 `admin` 且密码是 `123456` 时显示登录成功。

### 答案

```python
username = input("用户名：")
password = input("密码：")

if username == "admin" and password == "123456":
    print("登录成功")
else:
    print("用户名或密码错误")
```

> 这只是语法练习。真实项目绝不能用明文保存密码。

---

# 6. 循环

## 6.1 for 循环

```python
for number in range(1, 6):
    print(number)
```

输出 1 到 5。`range(1, 6)` 包含 1，但不包含 6。

累计求和：

```python
total = 0

for number in range(1, 101):
    total += number

print(total)
```

`total += number` 等价于：

```python
total = total + number
```

## 6.2 while 循环

```python
count = 1

while count <= 5:
    print(count)
    count += 1
```

只要条件成立，`while` 就会继续运行。忘记改变条件可能产生无限循环。

## 6.3 break 和 continue

```python
for number in range(1, 11):
    if number == 6:
        break
    print(number)
```

`break` 立即结束整个循环。

```python
for number in range(1, 6):
    if number == 3:
        continue
    print(number)
```

`continue` 跳过本轮，继续下一轮。

## 问题 8

输出 1 到 20 中的所有偶数。

### 答案

```python
for number in range(1, 21):
    if number % 2 == 0:
        print(number)
```

也可以写成：

```python
for number in range(2, 21, 2):
    print(number)
```

## 问题 9

打印九九乘法表。

### 答案

```python
for row in range(1, 10):
    for column in range(1, row + 1):
        print(f"{column}×{row}={column * row}", end="\t")
    print()
```

---

# 7. 字符串

字符串是一段文本：

```python
message = "Hello, Python"
```

## 7.1 索引与切片

```python
text = "Python"

print(text[0])      # P，第一个字符
print(text[-1])     # n，最后一个字符
print(text[0:3])    # Pyt
print(text[:2])     # Py
print(text[2:])     # thon
```

索引从 0 开始，切片包含起点但不包含终点。

## 7.2 常用字符串方法

```python
text = "  Hello Python  "

print(text.strip())                # 去掉两端空白
print(text.lower())                # 转为小写
print(text.upper())                # 转为大写
print(text.replace("Python", "Go"))
print("a,b,c".split(","))         # 分割字符串
print("-".join(["a", "b", "c"])) # 连接字符串
```

其他常用操作：

```python
name = "Python"

print(len(name))          # 长度
print("Py" in name)      # 是否包含指定内容
print(name.startswith("P"))
print(name.endswith("on"))
```

## 问题 10

输入一句话，统计它包含多少个字符，忽略两端空格。

### 答案

```python
text = input("请输入一句话：").strip()
print(f"共有 {len(text)} 个字符")
```

---

# 8. 列表、元组、字典和集合

## 8.1 列表 list

列表用于保存一组有顺序、可以修改的数据：

```python
fruits = ["苹果", "香蕉", "橙子"]

print(fruits[0])
fruits.append("西瓜")
fruits.remove("香蕉")
print(fruits)
```

常用操作：

```python
numbers = [3, 1, 5, 2]

numbers.append(9)       # 末尾添加
numbers.insert(0, 8)    # 指定位置添加
last = numbers.pop()    # 删除并返回最后一个元素
numbers.sort()          # 排序
numbers.reverse()       # 反转

print(len(numbers))
print(3 in numbers)
```

遍历列表：

```python
names = ["小明", "小红", "小刚"]

for name in names:
    print(name)
```

同时获得序号：

```python
for index, name in enumerate(names, start=1):
    print(index, name)
```

## 8.2 元组 tuple

元组与列表相似，但创建后不能修改：

```python
point = (10, 20)
print(point[0])
```

## 8.3 字典 dict

字典使用“键: 值”保存数据：

```python
user = {
    "name": "小明",
    "age": 18,
    "city": "上海",
}

print(user["name"])
print(user.get("phone", "未填写"))

user["age"] = 19
user["job"] = "工程师"
```

遍历字典：

```python
for key, value in user.items():
    print(key, value)
```

## 8.4 集合 set

集合中的元素不会重复：

```python
numbers = {1, 2, 2, 3, 3}
print(numbers)  # {1, 2, 3}

numbers.add(4)
numbers.discard(2)
```

列表快速去重：

```python
values = [1, 1, 2, 3, 3]
unique_values = list(set(values))
print(unique_values)
```

## 问题 11

计算列表中所有数字的总和与平均值。

```python
scores = [80, 95, 76, 88, 91]
```

### 答案

```python
scores = [80, 95, 76, 88, 91]
total = sum(scores)
average = total / len(scores)

print(f"总分：{total}")
print(f"平均分：{average:.2f}")
```

`:.2f` 表示小数保留两位。

## 问题 12

统计一句话中每个字符出现的次数。

### 答案

```python
text = input("请输入文字：")
counts = {}

for char in text:
    counts[char] = counts.get(char, 0) + 1

for char, count in counts.items():
    print(f"{char}: {count}")
```

---

# 9. 函数

函数用于封装可以重复使用的代码。

```python
def greet(name):
    print(f"你好，{name}！")


greet("小明")
greet("小红")
```

## 9.1 返回值

```python
def add(number1, number2):
    result = number1 + number2
    return result


answer = add(10, 20)
print(answer)
```

`return` 把结果返回给调用函数的位置，同时结束函数。

## 9.2 默认参数

```python
def greet(name, message="你好"):
    print(f"{message}，{name}")


greet("小明")
greet("小红", "早上好")
```

## 9.3 变量作用域

```python
name = "外部变量"


def show():
    message = "局部变量"
    print(name)
    print(message)


show()
```

函数内部创建的局部变量，一般只能在函数内部使用。

## 问题 13

编写函数，判断一个数字是不是偶数，并返回布尔值。

### 答案

```python
def is_even(number):
    return number % 2 == 0


print(is_even(10))  # True
print(is_even(7))   # False
```

## 问题 14

编写一个函数，返回列表中的最大值。先使用内置函数即可。

### 答案

```python
def find_max(numbers):
    return max(numbers)


print(find_max([5, 2, 9, 1]))
```

---

# 10. 模块和第三方库

模块就是保存 Python 代码的文件。

## 10.1 使用标准库

```python
import random

number = random.randint(1, 10)
print(number)
```

```python
from datetime import datetime

now = datetime.now()
print(now)
```

标准库随 Python 一起安装，不需要额外下载。

## 10.2 安装第三方库

```bash
python -m pip install requests
```

使用示例：

```python
import requests

response = requests.get("https://example.com", timeout=10)
print(response.status_code)
```

第三方库来自外部。实际项目建议使用虚拟环境隔离依赖。

## 10.3 虚拟环境

创建：

```bash
python -m venv .venv
```

Windows PowerShell 激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux 激活：

```bash
source .venv/bin/activate
```

退出虚拟环境：

```bash
deactivate
```

## 问题 15

`import random` 有什么作用？

### 答案

导入 Python 标准库中的 `random` 模块，之后可以使用它提供的随机数等功能。

---

# 11. 文件读写

## 11.1 写入文件

```python
with open("note.txt", "w", encoding="utf-8") as file:
    file.write("第一行笔记\n")
    file.write("第二行笔记\n")
```

`w` 表示覆盖写入。如果文件已存在，原内容会被清空。

追加内容使用 `a`：

```python
with open("note.txt", "a", encoding="utf-8") as file:
    file.write("追加的新内容\n")
```

## 11.2 读取文件

```python
with open("note.txt", "r", encoding="utf-8") as file:
    content = file.read()

print(content)
```

逐行读取：

```python
with open("note.txt", "r", encoding="utf-8") as file:
    for line in file:
        print(line.strip())
```

`with` 代码块结束后会自动关闭文件。

## 问题 16

把用户输入的一句话追加到 `diary.txt`。

### 答案

```python
content = input("今天发生了什么？")

with open("diary.txt", "a", encoding="utf-8") as file:
    file.write(content + "\n")

print("保存成功")
```

---

# 12. 异常处理

程序运行时出现的问题叫异常。

```python
try:
    number = int(input("请输入整数："))
    print(10 / number)
except ValueError:
    print("输入的不是整数")
except ZeroDivisionError:
    print("除数不能是零")
```

完整结构：

```python
try:
    print("执行可能出错的代码")
except Exception as error:
    print(f"发生错误：{error}")
else:
    print("没有发生错误")
finally:
    print("无论是否出错都会执行")
```

学习阶段可以查看 `Exception`，正式代码应尽量捕获明确的异常类型。

## 问题 17

反复要求用户输入整数，直到输入正确为止。

### 答案

```python
while True:
    try:
        number = int(input("请输入整数："))
        break
    except ValueError:
        print("格式错误，请重新输入")

print(f"你输入的是 {number}")
```

---

# 13. 面向对象入门

类是创建对象的模板。刚入门时只需理解基本形式。

```python
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        print(f"我叫{self.name}，今年{self.age}岁")


dog = Dog("旺财", 3)
dog.introduce()
```

解释：

- `class Dog`：定义一个类；
- `__init__`：创建对象时自动执行；
- `self`：表示当前对象；
- `dog`：根据 `Dog` 类创建的对象；
- `introduce()`：对象可以执行的方法。

## 问题 18

定义一个 `Rectangle` 类，保存宽和高，并计算面积。

### 答案

```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


rectangle = Rectangle(5, 3)
print(rectangle.area())
```

---

# 14. 常见错误与调试

## 14.1 SyntaxError

语法错误，例如遗漏冒号：

```python
# 错误
if age >= 18
    print("成年")
```

正确写法：

```python
if age >= 18:
    print("成年")
```

## 14.2 IndentationError

缩进错误：

```python
# 错误
if age >= 18:
print("成年")
```

正确写法：

```python
if age >= 18:
    print("成年")
```

## 14.3 NameError

使用了没有定义的变量，或者变量名拼错。

## 14.4 TypeError

对不兼容的数据类型进行了操作，例如：

```python
print("年龄：" + 18)
```

可以改成：

```python
print("年龄：" + str(18))
```

或者：

```python
print(f"年龄：{18}")
```

## 14.5 调试步骤

1. 从报错信息的最后一行看错误类型；
2. 找到提示的文件和行号；
3. 使用 `print()` 输出变量的值与类型；
4. 缩小问题范围；
5. 修改后重新运行。

示例：

```python
age = input("年龄：")
print(age)
print(type(age))
```

---

# 15. 综合项目：命令行记账程序

这个项目会练习变量、循环、条件、列表、字典、函数、文件和异常处理。

数据保存在 `records.json` 中。程序支持：

- 添加收入或支出；
- 查看全部记录；
- 查看余额；
- 自动保存数据。

## 完整代码

创建 `accounting.py`：

```python
import json
from pathlib import Path


DATA_FILE = Path("records.json")


def load_records():
    """从文件加载记录。"""
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        print("数据文件读取失败，将使用空记录。")
        return []


def save_records(records):
    """把记录保存到文件。"""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


def read_amount():
    """读取一个大于零的金额。"""
    while True:
        try:
            amount = float(input("金额："))
            if amount <= 0:
                print("金额必须大于零。")
                continue
            return amount
        except ValueError:
            print("请输入正确的数字。")


def add_record(records):
    """添加收入或支出记录。"""
    record_type = input("类型（收入/支出）：").strip()
    if record_type not in ("收入", "支出"):
        print("类型只能是收入或支出。")
        return

    amount = read_amount()
    note = input("说明：").strip()

    record = {
        "type": record_type,
        "amount": amount,
        "note": note,
    }
    records.append(record)
    save_records(records)
    print("记录已保存。")


def show_records(records):
    """显示所有记录。"""
    if not records:
        print("暂无记录。")
        return

    for index, record in enumerate(records, start=1):
        print(
            f"{index}. {record['type']} "
            f"{record['amount']:.2f} 元，说明：{record['note']}"
        )


def show_balance(records):
    """计算并显示总收入、总支出和余额。"""
    income = sum(
        record["amount"]
        for record in records
        if record["type"] == "收入"
    )
    expense = sum(
        record["amount"]
        for record in records
        if record["type"] == "支出"
    )

    print(f"总收入：{income:.2f} 元")
    print(f"总支出：{expense:.2f} 元")
    print(f"余额：{income - expense:.2f} 元")


def main():
    records = load_records()

    while True:
        print("\n===== 记账程序 =====")
        print("1. 添加记录")
        print("2. 查看记录")
        print("3. 查看余额")
        print("0. 退出")

        choice = input("请选择：").strip()

        if choice == "1":
            add_record(records)
        elif choice == "2":
            show_records(records)
        elif choice == "3":
            show_balance(records)
        elif choice == "0":
            print("再见！")
            break
        else:
            print("无效选择，请重新输入。")


if __name__ == "__main__":
    main()
```

运行：

```bash
python accounting.py
```

## 项目问题 1

为什么使用 `json`？

### 答案

JSON 可以保存列表、字典、字符串和数字等结构化数据，而且便于人阅读。程序关闭后，记录仍保存在文件中。

## 项目问题 2

为什么程序被拆分成多个函数？

### 答案

每个函数只负责一个明确任务，代码更容易阅读、测试、修改和重复使用。

## 项目问题 3

`if __name__ == "__main__":` 是什么意思？

### 答案

当这个文件被直接运行时，条件成立并调用 `main()`；当它被其他文件导入时，不会自动启动菜单程序。

## 项目升级答案示例：删除记录

增加函数：

```python
def delete_record(records):
    show_records(records)
    if not records:
        return

    try:
        index = int(input("请输入要删除的记录编号：")) - 1
        if index < 0 or index >= len(records):
            print("记录编号不存在。")
            return
    except ValueError:
        print("请输入整数编号。")
        return

    deleted = records.pop(index)
    save_records(records)
    print(f"已删除：{deleted['note']}")
```

然后在菜单中增加：

```python
print("4. 删除记录")
```

在条件判断中增加：

```python
elif choice == "4":
    delete_record(records)
```

---

# 16. 七天快速学习安排

## 第 1 天

- 阅读第 1～4 章；
- 运行输出、变量、输入、类型转换示例；
- 理解 `=` 与 `==` 的区别。

## 第 2 天

- 阅读第 5～6 章；
- 运行成绩判断、偶数循环和九九乘法表；
- 理解缩进、`if`、`for` 和 `while`。

## 第 3 天

- 阅读第 7～8 章；
- 掌握字符串、列表和字典；
- 运行字符计数程序。

## 第 4 天

- 阅读第 9 章；
- 理解参数、返回值和变量作用域；
- 把重复代码整理成函数。

## 第 5 天

- 阅读第 10～12 章；
- 掌握模块、文件读写和异常处理；
- 运行日记程序。

## 第 6 天

- 快速阅读第 13～14 章；
- 面向对象只需理解，不必急着熟练；
- 学会根据报错类型和行号查问题。

## 第 7 天

- 完整运行记账项目；
- 对照代码理解每个函数；
- 增加删除记录功能。

---

# 17. 必须记住的核心语法

```python
# 输出与输入
print("hello")
name = input("姓名：")

# 类型转换
age = int("18")
price = float("9.9")

# 条件判断
if age >= 18:
    print("成年")
else:
    print("未成年")

# 循环
for number in range(5):
    print(number)

while age < 20:
    age += 1

# 列表
items = ["a", "b"]
items.append("c")

# 字典
user = {"name": "小明", "age": 18}
print(user["name"])

# 函数
def add(a, b):
    return a + b

# 异常处理
try:
    number = int(input("数字："))
except ValueError:
    print("输入错误")

# 文件
with open("data.txt", "r", encoding="utf-8") as file:
    content = file.read()
```

---

# 18. 常见问答

## 问：需要背下所有语法吗？

答：不需要。先知道某个功能存在，需要时再查。经常使用的语法会自然记住。

## 问：只看教程能学会吗？

答：不能完全学会。至少要复制并运行示例，修改其中的变量和条件，观察结果变化。编程是一项操作技能。

## 问：遇到报错怎么办？

答：先看错误信息最后一行，再看它指向的代码行。不要一次修改很多地方，每次只验证一个猜测。

## 问：什么时候算入门？

答：当你能看懂条件、循环、列表、字典和函数，并能在查资料的帮助下写出一个小程序，就已经入门。

## 问：学完以后学什么？

答：根据目标选择方向：

- Web 后端：HTTP、SQL、FastAPI 或 Django；
- 数据分析：NumPy、pandas、Matplotlib；
- 自动化：文件处理、Excel、HTTP API、定时任务；
- AI：NumPy、pandas、机器学习基础、PyTorch；
- 测试开发：pytest、HTTP API、浏览器自动化。

---

# 19. 学习检查表

完成后确认自己能解释这些问题：

- [ ] `print()` 与 `input()` 分别做什么？
- [ ] 为什么 `input()` 后经常需要 `int()`？
- [ ] `=` 与 `==` 有什么区别？
- [ ] `if`、`elif`、`else` 怎样工作？
- [ ] `for` 和 `while` 有什么区别？
- [ ] 列表和字典分别适合保存什么数据？
- [ ] 函数的参数与返回值是什么？
- [ ] 怎样读取和写入文件？
- [ ] 怎样使用 `try/except` 处理异常？
- [ ] 怎样根据报错信息找到出错位置？

如果以上大部分问题都能回答，就可以开始做真实的小项目了。
