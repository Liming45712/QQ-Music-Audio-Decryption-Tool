# -*- coding: utf-8 -*-
"""
OGG 转 FLAC 转换工具
独立脚本，用于将 OGG 音频文件批量转换为 FLAC 格式
"""

import os
import sys
import argparse
import logging
import csv
import subprocess
import shutil
from datetime import datetime

try:
    from source_finder import guess_song_url
except Exception:
    def guess_song_url(_):
        return None


def check_ffmpeg() -> bool:
    """
    检查 ffmpeg 是否可用
    
    Returns:
        bool: ffmpeg 是否可用
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def append_csv(song_name: str, src_url: str = ""):
    """
    将转换记录追加到 CSV 文件
    
    Args:
        song_name: 歌曲文件名
        src_url: 来源链接（可选）
    """
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversion_log.csv")
    exists = os.path.exists(csv_path)
    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["转换时间", "歌曲", "来源链接"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), song_name, src_url])


def convert_ogg_to_flac(ogg_path: str, flac_path: str) -> bool:
    """
    使用 ffmpeg 将 OGG 文件转换为 FLAC 格式
    
    Args:
        ogg_path: OGG 文件路径
        flac_path: 输出 FLAC 文件路径
        
    Returns:
        bool: 转换是否成功
    """
    if not os.path.exists(ogg_path):
        logging.error(f"OGG 文件不存在: {ogg_path}")
        return False
    
    try:
        logging.info(f"开始转换 OGG 到 FLAC: {os.path.basename(ogg_path)}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(flac_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 使用 ffmpeg 进行转换
        # -i: 输入文件
        # -c:a flac: 音频编码器使用 flac
        # -y: 自动覆盖已存在的文件（我们已经检查过了，这里只是保险）
        # -loglevel error: 只显示错误信息，减少输出
        cmd = [
            "ffmpeg",
            "-i", ogg_path,
            "-c:a", "flac",
            "-y",
            "-loglevel", "error",
            flac_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0 and os.path.exists(flac_path):
            logging.info(f"转换成功: {os.path.basename(flac_path)}")
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "未知错误"
            logging.error(f"转换失败: {ogg_path} -> {error_msg}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error(f"转换超时: {ogg_path}")
        return False
    except Exception as e:
        logging.error(f"转换失败: {ogg_path} -> {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False


def run_convert_ogg(input_dir: str, output_dir: str, record_csv: bool = True):
    """
    直接将目录中的 OGG 文件转换为 FLAC
    
    Args:
        input_dir: 包含 OGG 文件的输入目录
        output_dir: FLAC 文件的输出目录
        record_csv: 是否记录到 CSV 文件
    """
    if not check_ffmpeg():
        logging.error("ffmpeg 未安装或不在 PATH 中，无法转换 OGG 到 FLAC")
        logging.error("请安装 ffmpeg:")
        logging.error("  Windows: 从 https://ffmpeg.org/download.html 下载，或使用 choco install ffmpeg")
        logging.error("  安装后请确保 ffmpeg 在系统 PATH 环境变量中")
        return
    
    if not os.path.exists(input_dir):
        logging.error(f"输入目录不存在: {input_dir}")
        return
    
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"创建输出目录: {output_dir}")
    
    ogg_count = 0
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    logging.info(f"开始扫描目录: {input_dir}")
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            base, ext = os.path.splitext(file)
            if ext.lower() != ".ogg":
                continue
            
            ogg_count += 1
            logging.info(f"[{ogg_count}] 找到 OGG 文件: {file}")
            
            flac_filename = base + ".flac"
            flac_file_path = os.path.join(output_dir, flac_filename)
            
            if os.path.exists(flac_file_path):
                logging.info(f"  FLAC 文件已存在，跳过: {flac_filename}")
                skip_count += 1
                continue
            
            ogg_file_path = os.path.join(root, file)
            
            try:
                if convert_ogg_to_flac(ogg_file_path, flac_file_path):
                    success_count += 1
                    # 记录到 CSV
                    if record_csv:
                        src_url = guess_song_url(file) or guess_song_url(flac_filename)
                        append_csv(flac_filename, src_url or "")
            except Exception as e:
                logging.error(f"  处理文件失败: {file} -> {e}")
                fail_count += 1
                continue
    
    logging.info("=" * 60)
    logging.info(f"转换完成统计:")
    logging.info(f"  共找到 OGG 文件: {ogg_count} 个")
    logging.info(f"  成功转换: {success_count} 个")
    logging.info(f"  跳过（已存在）: {skip_count} 个")
    logging.info(f"  转换失败: {fail_count} 个")
    logging.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    parser = argparse.ArgumentParser(
        description="OGG 转 FLAC 转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换指定目录的 OGG 文件
  python convert_ogg_to_flac.py -i "C:\\Music\\OGG" -o "C:\\Music\\FLAC"
  
  # 不记录到 CSV 文件
  python convert_ogg_to_flac.py -i input -o output --no-csv
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="包含 OGG 文件的输入目录"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="FLAC 文件的输出目录"
    )
    
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="不记录转换信息到 CSV 文件"
    )
    
    args = parser.parse_args()
    
    if not check_ffmpeg():
        logging.error("ffmpeg 未安装或不在 PATH 中，无法使用转换功能")
        logging.error("请安装 ffmpeg:")
        logging.error("  Windows: 从 https://ffmpeg.org/download.html 下载，或使用 choco install ffmpeg")
        logging.error("  安装后请确保 ffmpeg 在系统 PATH 环境变量中")
        sys.exit(1)
    
    run_convert_ogg(args.input, args.output, record_csv=not args.no_csv)
