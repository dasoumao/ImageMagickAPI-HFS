---
title: Magick 图像转换器 # 显示在 Space 页面的标题 (可自定义)
emoji: 🖼️ # Space 图标的 Emoji (可选)
colorFrom: blue # 主题颜色起始 (可选)
colorTo: green # 主题颜色结束 (可选)
sdk: docker # 指定这是一个基于 Docker 的 Space (非常重要)
app_port: 8000 # 你的 FastAPI 应用在容器内部监听的端口 (必须与 Dockerfile CMD 中指定的端口一致)
pinned: false # 是否在你的个人资料页置顶这个 Space (可选)
---

# 🧙‍♂️ Magick 图像转换 API

本项目提供一个基于 FastAPI 和 ImageMagick 的 REST API，用于：

* **POST /**: 将上传的图像转换为**无损 AVIF** 格式，并**保留所有元信息**。
* **GET /health**: 检查 ImageMagick 和 AVIF 编码器 (heif) 的可用状态。