# qoj-submit

给算法竞赛选手用的命令行交题插件。绑定本场比赛后，在当前目录：

```bash
./submit a.cpp
./submit b.py
```

用法接近现场 XCPC：文件名就是题号，确认语言后提交。目前支持 [Codeforces](https://codeforces.com) 和 [QOJ](https://qoj.ac)。

只依赖 **Python 3.8+** 标准库即可交题。弹出浏览器登录需要再装 `selenium`。Codeforces 建议再装 `curl_cffi` 以通过 Cloudflare。

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

### 1. 选择 OJ 并登录（做一次）

```bash
./submit cf            # 或 ./submit qoj
python3 submit login
python3 submit whoami
```

会弹出浏览器窗口，在里面正常登录（含 Cloudflare）。Codeforces 会打开**你平时的 Firefox**，过验证后点右上角 Enter。

Cookie 和 User-Agent 保存在 `~/.config/qoj-xcpc/config.json`，各 OJ 分开存，不要提交到 git。Cookie 过期后重新 `login`。

换账号：先在浏览器里退出，再 `python3 submit login`。也可以 `python3 submit logout`，或 `python3 submit logout cf` 只清某一个 OJ。

指定站点登录：`python3 submit login cf`。

### 2. 绑定比赛

用比赛 UID（或完整 URL）：

```bash
./submit cf
./submit 2044              # Codeforces 场次
./submit gym 105505        # Gym

./submit qoj
./submit 1234              # QOJ 场次
```

也可以一次写完：`./submit cf 2044`。查看当前 OJ：`./submit oj`。

会写入当前目录的 `.qoj.json`。之后在该目录交题即可。

### 3. 提交

```bash
./submit a.cpp
./submit b.cpp --lang C++23
./submit sol.cpp -p D
./submit a.cpp -y
```

题号取文件名前缀：`a.cpp` → A，`c.py` → C。Codeforces 的 easy/hard 分题：`c1.cpp` 交 **C1**（没有 C1 时交 C），`c2.cpp` 同理。

确认前提示比赛名、题目、文件、语言，以及文件是否可能是旧代码。

`.cpp` / `.cc` 默认 **C++20**（Codeforces 对应 GNU G++20，不会误选 GNU GCC C），`.py` 默认 **PyPy3**。换语言用 `--lang`。

提交成功后给出本场提交列表地址，不再在命令行里轮询评测详情。

### 其它命令

```bash
./submit oj           # 当前 OJ
./submit qoj          # 选择 QOJ
./submit cf           # 选择 Codeforces
./submit problems     # 题目列表
./submit status       # 最近提交
./submit whoami       # 当前登录账号
```

## 目录

```
contest/
  submit          # 本脚本（绑定比赛时会复制一份到当前目录）
  .qoj.json       # 本场配置（本地生成，不要上传）
  a.cpp
  b.cpp
```

## 注意

- 被 Cloudflare 拦截时，重新 `python3 submit login`。Codeforces 请用 `./install.sh` 装好 `curl_cffi`，并在弹出的日常 Firefox 里过验证。
- QOJ 交互题（Anna / Bruno）请用网页提交。`training.qoj.ac` 绑定比赛时用完整 URL。
- 登录配置在 `~/.config/qoj-xcpc/config.json`，比赛配置在 `.qoj.json`，都不要提交到 git。
