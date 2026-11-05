#!/bin/bash
# 编译抠图工具（只需一次，产物缓存在技能目录的 bin/）
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$DIR/bin"
mkdir -p "$BIN"

if [ ! -x "$BIN/cutout" ] || [ "$DIR/cutout.swift" -nt "$BIN/cutout" ]; then
  echo "building cutout..."
  swiftc -O "$DIR/cutout.swift" -o "$BIN/cutout"
fi
echo "ready: $BIN/cutout"
