# qoj-submit

面向 [QOJ](https://qoj.ac) Virtual Participation 的命令行提交工具。用法接近现场 XCPC：绑定比赛后，在当前目录执行：

```bash
./submit a.cpp
./submit b.py
```

只依赖 **Python 3.8+** 标准库即可交题。弹出浏览器登录需要再装 `selenium`。

## 安装

Debian / Ubuntu 不要使用 `sudo pip`。如果目录在 VirtualBox 共享文件夹里，也不要把虚拟环境建在该目录（无法创建 symlink）。

```bash
chmod +x submit install.sh
./install.sh
python3 submit login
```

`install.sh` 会把虚拟环境放到 `~/.local/share/qoj-xcpc/venv`。

也可以直接：

```bash
python3 submit login
```

未安装 selenium 时，用 `python3 submit login --manual` 粘贴 Cookie。

## 使用

### 1. 登录（做一次）

```bash
python3 submit login
python3 submit whoami
```

会弹出 Firefox / Chrome 窗口，在里面正常登录 QOJ（含 Cloudflare）。成功后窗口关闭，Cookie 和 User-Agent 保存在：

```
~/.config/qoj-xcpc/config.json
```

不要把这个文件提交到 git。Cookie 过期后重新执行 `login`。

换账号时再跑一次 `python3 submit login`：会先退出本地登录和浏览器里的旧会话，再弹出登录窗口。也可以先 `python3 submit logout`。

### 2. 绑定比赛

用比赛 UID，不必贴完整 URL：

```bash
python3 submit 1234
```

或：

```bash
python3 submit init 1234
```

会写入当前目录的 `.qoj.json`，并尝试 Start VP。之后在该目录交题即可。

### 3. 提交

```bash
./submit a.cpp
./submit b.cpp --lang C++23
./submit sol.cpp -p D
./submit a.cpp -y
```

题号取文件名第一个字母：`a.cpp` → A，`c.py` → C。

确认前提示：

- 比赛、题目、文件
- 文件上次修改距现在多久
- 若文件修改时间早于上次提交，会警告可能交的是旧代码

`.cpp` / `.cc` 默认 **C++20**，`.py` 默认 **PyPy3**。

提交成功后给出比赛提交列表，例如：

```
https://qoj.ac/contest/<id>/submissions
```

不再在命令行里轮询评测详情。

### 其它命令

```bash
./submit problems     # 题目列表
./submit status       # 最近提交
./submit start        # 开始 VP
./submit whoami       # 当前登录账号
```

## 目录

```
your-vp/
  submit          # 本脚本（绑定比赛时会复制一份到当前目录）
  .qoj.json       # 本场配置（本地生成，不要上传）
  a.cpp
  b.cpp
```

## 注意

- 被 Cloudflare 拦截时，重新 `python3 submit login`。Cookie 必须和当时的 User-Agent 来自同一次浏览器会话。
- 交互题（Anna / Bruno）请用网页提交。
- `training.qoj.ac` 同样支持，init 时用完整比赛 URL。
- 登录配置在 `~/.config/qoj-xcpc/config.json`，比赛配置在 `.qoj.json`，都不要提交到 git。
