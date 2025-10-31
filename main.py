import fastapi
from fastapi import FastAPI, File, UploadFile, HTTPException, Response, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import subprocess
import asyncio # 使用 asyncio 来进行非阻塞的 subprocess 调用
import tempfile
import os
import shutil
import logging
import uuid
from typing import Literal, Optional, List

# --- 配置  ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 200  # 最大文件大小
TIMEOUT_SECONDS = 300   # 转换超时 (5分钟)
TEMP_DIR = "/app/temp"  # 临时文件目录
# ----------------

# 初始化 FastAPI 应用
app = FastAPI(
    title="Magick AVIF Converter",
    description="API to convert images to lossless AVIF, preserving metadata.",
    version="1.0.0"
)

# 确保临时目录存在 
os.makedirs(TEMP_DIR, exist_ok=True)

# --- 健康检查 (适配 Magick) ---
@app.get("/health", summary="Health Check")
async def health_check():
    """提供详细的API和依赖健康状态检查"""
    try:
        # 检查 Magick 是否可用
        proc_magick = await asyncio.subprocess.create_subprocess_exec(
            'magick', '--version', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout_m, stderr_m = await proc_magick.communicate()
        magick_version = stdout_m.decode().split('\n')[0] if proc_magick.returncode == 0 else "Not available"
        
        # 检查 AVIF 编码器 (heif-enc) 是否可用
        proc_heif = await asyncio.subprocess.create_subprocess_exec(
            'which', 'heif-enc', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout_h, stderr_h = await proc_heif.communicate()
        heif_encoder_path = stdout_h.decode().strip() if proc_heif.returncode == 0 else "Not available (AVIF conversion will fail)"

        # 检查磁盘空间 
        disk_info = os.statvfs(TEMP_DIR)
        free_space_mb = (disk_info.f_bavail * disk_info.f_frsize) / (1024 * 1024)
        
        return {
            "status": "healthy",
            "imagemagick": magick_version,
            "avif_encoder": heif_encoder_path,
            "disk_space": {"free_mb": round(free_space_mb, 2), "temp_dir": TEMP_DIR},
            "resource_limits": {
                "max_file_size_mb": MAX_FILE_SIZE_MB,
                "timeout_seconds": TIMEOUT_SECONDS
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

# --- 根路径 API 端点 (实现您的需求) ---
@app.post("/",
          summary="Convert Image to Lossless AVIF",
          response_class=FileResponse,
          responses={
              200: {"content": {"image/avif": {}}, "description": "Successfully converted image to lossless AVIF."},
              400: {"description": "Bad Request (e.g., file too large)"},
              500: {"description": "Internal Server Error (Magick conversion failed)"},
              504: {"description": "Gateway Timeout (Conversion took too long)"}
          })
async def convert_to_avif_lossless(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The image file to be converted (PNG, JPEG, WebP, etc.).")
):
    """
    接收图像文件，将其无损转换为 AVIF，并保留元信息。
    """
    logger.info(f"Received request: filename={file.filename}")

    # --- 文件大小检查  ---
    file_size_mb = await get_upload_file_size(file) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        logger.warning(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB. Your file is {file_size_mb:.2f}MB."
        )

    # --- 临时目录和路径  ---
    session_id = str(uuid.uuid4())
    temp_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 获取原始文件扩展名
    _, file_extension = os.path.splitext(file.filename)
    input_path = os.path.join(temp_dir, f"input{file_extension}")
    output_path = os.path.join(temp_dir, f"output.avif")

    logger.info(f"Processing in temporary directory: {temp_dir}")

    try:
        # --- 保存上传的文件  ---
        logger.info(f"Saving uploaded file '{file.filename}' to '{input_path}'")
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info("File saved successfully.")

        # --- 构建 Magick 命令 (您的核心需求) ---
        cmd = [
            'magick',
            input_path,
            '-define', 'avif:lossless=true',  # 无损
            '-define', 'avif:speed=0',        # 最佳压缩率
            output_path                      # (无 -strip，保留元信息)
        ]
        
        command_str = ' '.join(cmd)
        logger.info(f"Executing command: {command_str}")

        # --- 执行 Magick 命令 (异步) ---
        process = await asyncio.wait_for(
            asyncio.subprocess.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=TIMEOUT_SECONDS
        )
        stdout, stderr = await process.communicate()

        # --- 检查命令执行结果 ---
        if process.returncode != 0:
            error_message = f"Magick failed with exit code {process.returncode}."
            logger.error(f"{error_message}\nStderr: {stderr.decode()[:1000]}")
            raise HTTPException(status_code=500, detail=f"ImageMagick conversion failed. Error: {stderr.decode()}")
        
        if not os.path.exists(output_path):
            error_message = "Magick command succeeded but output file was not found."
            logger.error(error_message)
            raise HTTPException(status_code=500, detail=error_message)
        
        # --- 成功  ---
        logger.info(f"Conversion successful. Output file: '{output_path}'")
        
        # 生成下载文件名
        original_filename_base = os.path.splitext(file.filename)[0]
        download_filename = f"{original_filename_base}_lossless.avif"

        # 注册后台清理 
        background_tasks.add_task(cleanup_temp_dir, temp_dir)

        # 返回文件 
        return FileResponse(
            path=output_path,
            media_type='image/avif',
            filename=download_filename,
            background=background_tasks
        )

    except asyncio.TimeoutError:
        logger.error(f"Magick processing timed out after {TIMEOUT_SECONDS}s for file '{file.filename}'.")
        raise HTTPException(status_code=504, detail=f"Conversion timed out after {TIMEOUT_SECONDS} seconds.")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred.")
    finally:
        # 确保关闭文件句柄
        await file.close()
        # 如果没有成功注册后台任务，也尝试清理 (备用)
        if not 'background_tasks' in locals() and os.path.exists(temp_dir):
             cleanup_temp_dir(temp_dir)

# --- 清理函数  ---
def cleanup_temp_dir(temp_dir: str):
    """清理临时目录及其内容的辅助函数"""
    try:
        if os.path.exists(temp_dir):
            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
            logger.info("Temporary directory cleaned up successfully.")
    except Exception as cleanup_error:
        logger.error(f"Error cleaning up temporary directory {temp_dir}: {cleanup_error}", exc_info=True)

# --- 文件大小检查  ---
async def get_upload_file_size(upload_file: UploadFile) -> int:
    """获取上传文件的大小（以字节为单位）"""
    current_position = upload_file.file.tell()
    upload_file.file.seek(0, 2)  # 2 表示从文件末尾
    size = upload_file.file.tell()
    upload_file.file.seek(current_position)
    return size