import requests
import os
import time

# --- 配置 ---

# 您的 API 端点基础 URL
api_base_url = "https://blueskyxn-imagemagickapi-hfs.hf.space"

# 转换参数: 格式/模式/设置
target_format = "avif"  # avif, webp, jpeg, png, gif, heif
mode = "lossy"          # lossy, lossless
setting = 80            # 0-100 (有损模式为质量, 无损模式为压缩速度)

# 构建完整的 API URL
api_url = f"{api_base_url}/convert/{target_format}/{mode}/{setting}"

# 您要测试的本地图片路径
input_image_path = r"/Volumes/TP4000PRO/582434E54A64FCB0285EFABF390AC3DB.jpg"

# 转换后的文件保存路径 (自动替换扩展名)
output_image_path = os.path.splitext(input_image_path)[0] + f".{target_format}"

# ----------------

# 检查输入文件是否存在
if not os.path.exists(input_image_path):
    print(f"错误: 输入文件未找到: {input_image_path}")
    exit()

print(f"开始处理文件: {input_image_path}")
try:
    print(f"文件大小: {os.path.getsize(input_image_path)/1024/1024:.2f} MB")
except OSError as e:
    print(f"无法访问文件: {e}")
    exit()
    
start_time = time.time()

# 准备上传的文件
# 键 "file" 必须与您 main.py 中 FastAPI 的参数名一致
# (file: UploadFile = File(...))
file_handle = open(input_image_path, "rb")
files = {
    "file": (
        os.path.basename(input_image_path),  # 发送原始文件名
        file_handle,                         # 文件句柄
        "image/jpeg"                         # 文件的 MIME 类型
    )
}

try:
    # 发送 POST 请求
    print(f"正在发送请求到 Magick API: {api_url}")
    # 注意：这个端点不需要 "data" 参数，只需要 "files"
    response = requests.post(api_url, files=files)
    
    # --- 处理响应 ---
    if response.status_code == 200:
        # 检查返回的是否是目标格式的图像
        expected_content_type = f'image/{target_format}'
        if target_format == 'jpeg':
            expected_content_type = 'image/jpeg'

        actual_content_type = response.headers.get('content-type')
        if actual_content_type == expected_content_type or actual_content_type.startswith('image/'):
            # 保存处理后的图像
            with open(output_image_path, "wb") as f:
                f.write(response.content)

            end_time = time.time()
            print("\n--- 转换成功! ---")
            print(f"总耗时: {end_time - start_time:.2f} 秒")
            print(f"结果已保存到: {output_image_path}")
            print(f"输出文件大小: {os.path.getsize(output_image_path)/1024/1024:.2f} MB")
        else:
            print(f"处理失败! 服务器返回了 200 OK，但内容类型不匹配。")
            print(f"期望的内容类型: {expected_content_type}")
            print(f"返回的内容类型: {actual_content_type}")
            print(f"响应内容 (前500字节): {response.text[:500]}...")

    else:
        # --- 处理错误 ---
        print(f"\n--- 处理失败! ---")
        print(f"状态码: {response.status_code}")
        try:
            # 尝试解析 FastAPI 返回的 JSON 错误详情
            error_details = response.json()
            print(f"错误详情: {error_details.get('detail', '无详情')}")
        except requests.exceptions.JSONDecodeError:
            # 如果返回的不是 JSON (例如 502 Bad Gateway)
            print(f"响应内容 (前500字节): {response.text[:500]}...")

finally:
    # 确保关闭文件句柄
    file_handle.close()
    print("\n测试完成。")