---
title: Magick 图像转换器
emoji: 🖼️
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 8000
---

# 🧙‍♂️ Magick 图像转换 API

本项目提供一个基于 FastAPI 和 ImageMagick 的 REST API，用于：

* **POST /**: 将上传的图像转换为**无损 AVIF** 格式，并**保留所有元信息**。
* **GET /health**: 检查 ImageMagick 和 AVIF 编码器 (heif) 的可用状态。