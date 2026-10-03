# qoj-submit

给算法竞赛选手用的命令行交题插件。绑定本场比赛后，在当前目录：

```bash
./submit a.cpp
./submit b.py
```

用法接近现场 XCPC：文件名就是题号，确认语言后提交。目前支持 [Codeforces](https://codeforces.com) 和 [QOJ](https://qoj.ac)。

只依赖 **Python 3.8+** 标准库即可交题。弹出浏览器登录需要再装 `selenium`。QOJ 和 Codeforces 都建议安装 `curl_cffi`，以使用浏览器兼容的 TLS 连接。

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

默认会弹出**你平时的 Firefox**，直接打开对应 OJ 首页。窗口里已经登录则立刻读取当前账号；否则请在窗口里登录（含 Cloudflare）。Codeforces 过验证后点右上角 Enter。

Cookie 和 User-Agent 保存在 `~/.config/qoj-xcpc/config.json`，各 OJ 分开存，不要提交到 git。Cookie 过期后重新 `login`。

换账号：在浏览器里退出后，再 `python3 submit login`。`python3 submit logout` 只删除当前账号的本地记录，保留其它已保存账号，不清理浏览器 Cookie。

指定站点登录：`python3 submit login cf`。

### 多账号登录和切换

同一个 OJ 可以保存多个账号。指定 `--account` 时，会使用该站点、该用户名
独立的浏览器配置，避免为了换号退出网页而使另一个账号的会话失效。
首次登录请在弹出的窗口完成验证，并登录对应用户名；脚本会核对实际账号。

```bash
./submit login qoj --account alice
./submit login qoj --account team_account
./submit accounts qoj                         # * 标记当前账号
./submit account alice --site qoj              # 切换保存的会话
./submit whoami --check                        # 联网验证
./submit a.cpp                                # 使用当前账号提交

./submit login cf --account cf_handle
./submit account cf_handle --site cf
```

`accounts` 和 `account` 默认使用当前选择的 OJ。切换账号会同时切换 Cookie
和 User-Agent，不改变比赛绑定；提交、`status` 和 `watch` 使用比赛所属站点
当前选中的账号。默认 `login` 仍读取日常 Firefox 的当前账号。
也可通过 `login --manual --account 用户名` 导入浏览器 Cookie。

旧的单账号配置会在保存或切换时保留。`accounts[站点]` 继续保存当前账号，
新增 `saved_accounts[站点][用户名]` 保存其它会话。`logout [qoj|cf]` 只删除
该站点当前账号的本地记录，其它账号仍可切换；网页退出或服务器会话过期
后，需要重新登录该账号。

QOJ 登录同时支持旧版 Cookie 和 `__Host-UOJSESSID` / `__Host-UOJREMEMBER`。
Firefox 会话 Cookie 从最新的 sessionstore/recovery 文件读取，Mozilla LZ4
解压无需额外依赖；新版 Cookie 必须经过网页登录状态确认。

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

提交成功后默认自动查询本次提交的评测状态，状态变化时输出 `PENDING`、`JUDGING`、`AC`、`WA`、`TLE` 等，得到最终结果后退出。默认最多等待 300 秒；查询暂时失败会继续尝试，按 Ctrl+C 只停止等待，不取消提交。

```bash
./submit a.cpp                 # 提交并等待评测结果
./submit a.cpp --no-wait       # 确认交上去后退出
./submit a.cpp --wait 600      # 最多等待 10 分钟
./submit watch 123456          # 继续跟踪指定提交
```

轮询只跟踪确定的提交 ID，不会重复发送代码。若服务器只返回接收确认，且提交前记录无法读取，脚本无法安全确定本次 ID，会提示先用 `status` 核对，再用 `watch <ID>` 跟踪。

### 其它命令

```bash
./submit oj           # 当前 OJ
./submit qoj          # 选择 QOJ
./submit cf           # 选择 Codeforces
./submit problems     # 题目列表
./submit status       # 自己在本场的全部提交（自动翻页）
./submit status -n 20 # 只显示最近 20 条
./submit whoami       # 立即显示本地账号（不联网）
./submit whoami --check # 联网检查登录是否有效
```

`status` 仅显示当前账号在本场比赛中的提交，默认抓取所有分页，按提交号从新到旧排列。每条输出提交 ID、题号、状态、提交时间四列。提交时间保留网页所显示的时间，不转换时区，无法解析时显示 `-`。不显示题目名字、失败测试点、运行耗时或内存。支持 QOJ 和 Codeforces；`-n 0` 表示全部。登录失效、页面被拦截或抓取失败会报错，不会误报为“没有提交”。

提交前会尝试读取当前账号的已有记录；读取失败不会阻止发送代码，但此时不会根据旧提交列表猜测本次提交号。读取成功时，核对列表只把更大的提交号视为新记录。POST 响应超时或断连时不会自动重复发送代码，而是核对提交列表；无法确认时请先用 `status` 或网页核对。

`whoami` 默认只读取本地账号，不代表 Cookie 仍然有效；`whoami --check` 才会联网验证（默认 15 秒总请求预算，最多重试一次；可用 `--timeout 30` 调整）。网络错误和验证拦截不会被误报为 Cookie 过期。公共 HTTP 请求的重试和跳转共用超时预算，慢速响应读取也会检查剩余时间；系统 DNS 解析耗时仍受操作系统控制。

## 开发验证

```bash
QOJ_SUBMIT_NOVENV=1 python3 -m unittest discover -p 'test_*.py'
```

回归测试使用模拟页面和网络，不会向 OJ 发送真实提交。

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

### Firefox 能访问，但命令行报网络异常

QOJ 和 Codeforces 均优先使用 `curl_cffi`，未安装时退回标准库连接。运行 `./install.sh` 更新依赖。命令行读取 `https_proxy` / `http_proxy` / `all_proxy` 和 `no_proxy`；Firefox 内部单独设置的代理不会自动导入，需在终端设置相同的代理。标准库支持 HTTP CONNECT 代理，SOCKS / HTTPS 代理需安装 `curl_cffi`。

使用 `./submit --debug whoami --check --timeout 30` 查看脚本路径、版本、连接后端及错误。比赛目录里的 `submit` 是独立副本，更新仓库不会自动更新旧副本；请把新版脚本复制过去。新版 `whoami` 不带 `--check` 时不会联网。

### 提交时出现 request deadline

这是某个 HTTP 阶段耗尽时间预算。新版会显示“打开提交页”“读取提交前记录”“正在提交”“核对新提交记录”等阶段，便于区分请求尚未发送还是响应丢失。

GET 会为重试保留预算；QOJ 获取表单失败可在 30 秒总预算内尝试下一候选页面。提交只使用表单 action、token 和隐藏字段，POST 最多等待 30 秒，不猜测其他地址重复发送。服务器直接返回提交号或跳转到本场提交列表即确认接收；其他响应会在有提交前记录时核对最多 20 秒。暂时无法确认不等于没有交上去，请先查看网页或 `status`。

状态解析兼容纯文本、嵌套标签及状态提示属性：`Pending` / `Waiting` 显示为 `PENDING`，`Accept` / `Accepted` 显示为 `AC`，评测中显示为 `JUDGING`，其他结果使用 `WA`、`TLE`、`MLE`、`RE`、`CE` 等简写。无法识别的状态保留 `UNKNOWN`，不会用题名或耗时猜测结果。
