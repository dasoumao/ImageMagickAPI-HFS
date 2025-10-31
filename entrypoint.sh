#!/bin/sh

# 打印环境信息用于调试
echo "Starting Magick API Service"
echo "Environment: PORT=$PORT"

# 验证Magick是否可用
echo "Checking ImageMagick installation..."
magick --version | head -n 1
echo "Checking AVIF encoder (heif-enc) installation..."
which heif-enc

# 验证exiftool是否可用
echo "Checking exiftool installation..."
exiftool --version

# 确保使用正确的端口变量
PORT="${PORT:-8000}"
echo "Using port: $PORT"

# 执行 uvicorn 服务器 (同您的 OCR-HFS)
exec uvicorn main:app --host 0.0.0.0 --port $PORT