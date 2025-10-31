# 1. 使用官方 Python 镜像
FROM python:3.10-slim

# 设置环境变量
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp

# 2. 安装 ImageMagick 和 AVIF/HEIC 依赖
#    libheif-examples 提供了 magick 所需的 heif-enc 编码器
#    exiftool 用于提取和处理图像的 EXIF 数据
RUN apt-get update && apt-get install -y \
    imagemagick \
    libheif-examples \
    exiftool \
    && rm -rf /var/lib/apt/lists/*

# 3. 设置工作目录 (结构同您的 OCR-HFS)
WORKDIR /app

# 4. 复制并安装 Python 依赖 (结构同您的 OCR-HFS)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 复制应用代码 (结构同您的 OCR-HFS)
COPY main.py .
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# 6. 创建临时工作目录 (结构同您的 OCR-HFS)
RUN mkdir -p /app/temp
RUN chmod 777 /app/temp

# 7. 暴露端口 (结构同您的 OCR-HFS)
EXPOSE 8000

# 8. 使用入口脚本启动 (结构同您的 OCR-HFS)
ENTRYPOINT ["/app/entrypoint.sh"]