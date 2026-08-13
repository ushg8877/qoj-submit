#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null; then
  echo "需要 python3，请先执行:"
  echo "  sudo apt install python3 python3-venv python3-pip python3-full"
  exit 1
fi

# VirtualBox 共享盘不能创建 symlink（lib -> lib64）。
# 虚拟环境放到家目录所在的本地磁盘，不要放在 ~/public 共享文件夹里。
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV_DIR="${QOJ_SUBMIT_VENV:-$DATA_HOME/qoj-xcpc/venv}"

venv_ok() {
  local py="$1"
  [ -x "$py" ] || return 1
  "$py" -m pip --version >/dev/null 2>&1
}

# 清掉共享盘上失败的 .venv，避免之后再踩坑
if [ -d .venv ] && ! venv_ok .venv/bin/python && ! venv_ok .venv/bin/python3; then
  echo "删除共享盘上不完整的 .venv ..."
  rm -rf .venv || true
fi

PY=""
if venv_ok "$VENV_DIR/bin/python"; then
  PY="$VENV_DIR/bin/python"
elif venv_ok "$VENV_DIR/bin/python3"; then
  PY="$VENV_DIR/bin/python3"
fi

if [ -z "$PY" ]; then
  echo "正在创建虚拟环境: $VENV_DIR"
  rm -rf "$VENV_DIR"
  mkdir -p "$(dirname "$VENV_DIR")"
  if python3 -m venv --copies "$VENV_DIR" 2>/tmp/qoj-venv.err; then
    :
  elif python3 -m venv "$VENV_DIR" 2>/tmp/qoj-venv.err; then
    :
  else
    echo
    echo "创建 venv 失败:"
    cat /tmp/qoj-venv.err 2>/dev/null || true
    echo
    echo "若路径在 VirtualBox 共享文件夹里，这是正常现象。"
    echo "请确认 VENV 建在家目录，例如:"
    echo "  python3 -m venv --copies \$HOME/.local/share/qoj-xcpc/venv"
    exit 1
  fi
  if venv_ok "$VENV_DIR/bin/python"; then
    PY="$VENV_DIR/bin/python"
  elif venv_ok "$VENV_DIR/bin/python3"; then
    PY="$VENV_DIR/bin/python3"
  else
    PY="$VENV_DIR/bin/python"
    [ -x "$PY" ] || PY="$VENV_DIR/bin/python3"
    echo "venv 里没有 pip，尝试 ensurepip ..."
    if [ ! -x "$PY" ] || ! "$PY" -m ensurepip --upgrade; then
      echo "请执行: sudo apt install python3-venv python3-pip python3-full"
      exit 1
    fi
  fi
fi

echo "使用: $PY"
"$PY" -m pip install -U pip
"$PY" -m pip install -r requirements.txt

echo
echo "安装完成。登录:"
echo "  $PY \"$(pwd)/submit\" login"
echo "或:"
echo "  python3 submit login"
echo "（会自动使用 \$HOME/.local/share/qoj-xcpc/venv）"
