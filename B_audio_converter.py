import os
import subprocess
import shutil
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ============ 配置区 ============
# 自动获取当前脚本所在目录，并拼接文件夹名称
INPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "A_已整理音乐")
OUTPUT_FOLDER = None  # 设为 None 则自动在输入文件夹下创建 output
FFMPEG_PATH = "ffmpeg"  # 如果 ffmpeg 不在环境变量，改成完整路径如 r"C:\ffmpeg\bin\ffmpeg.exe"

# 音频参数
BITRATE = "320k"  # 比特率：320k, 256k, 192k, 128k
USE_VBR = False    # True=使用VBR变比特率, False=固定比特率
VBR_QUALITY = 0   # VBR质量 0-9, 0最高, 9最低

# 并发数（同时转换的文件数，根据CPU核心数调整）
MAX_WORKERS = 2

# =====================================================
# 支持的输入格式（尽可能全）
# 说明：这些格式都会被转换成 MP3，如果是 MP3 则直接复制
# =====================================================
SUPPORTED_FORMATS = {
    # ===== 无损/常见格式 =====
    '.wav', '.flac', '.m4a', '.aac',
    
    # ===== Apple无损 =====
    '.alac',
    
    # ===== 无损压缩 =====
    '.ape', '.tta',
    
    # ===== WavPack =====
    '.wv',
    
    # ===== OGG系列 =====
    '.ogg', '.opus',
    
    # ===== 环绕声 =====
    '.ac3', '.dts',
    
    # ===== 语音 =====
    '.amr',
    
    # ===== MPEG系列 =====
    '.mp2', '.mp1',
    
    # ===== 有声书 =====
    '.m4b',
    
    # ===== RealAudio =====
    '.ra', '.rm',
    
    # ===== 旧式格式 =====
    '.aiff', '.aif', '.au', '.snd',
    
    # ===== Creative Voice =====
    '.voc',
    
    # ===== Windows Media =====
    '.wma',
    
    # ===== WebM（含音频） =====
    '.webm',
    
    # ===== 手机视频（含音频） =====
    '.3gp', '.3g2',
    
    # ===== 其他视频格式（提取音频） =====
    '.mp4', '.m4v', '.mov', '.avi', '.mkv'
}

# ================================

# 统计数据（线程安全）
stats = {
    'total': 0,
    'converted': 0,
    'copied': 0,
    'failed': 0,
    'skipped': 0
}
stats_lock = threading.Lock()


def setup_output_folder():
    """设置输出文件夹"""
    if OUTPUT_FOLDER is None:
        output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "B_output_mp3")
    else:
        output_folder = OUTPUT_FOLDER
    
    os.makedirs(output_folder, exist_ok=True)
    print(f"📁 输出目录: {output_folder}")
    return output_folder


def get_ffmpeg_params():
    """构建 FFmpeg 参数"""
    params = []
    if USE_VBR:
        params.extend(['-b:a', BITRATE, '-q:a', str(VBR_QUALITY)])
    else:
        params.extend(['-b:a', BITRATE])
    return params


def process_file(file_path, input_folder, output_folder, ffmpeg_params):
    """处理单个文件"""
    global stats
    
    # 计算相对路径，保持目录结构
    rel_path = os.path.relpath(file_path, input_folder)
    output_path = os.path.join(output_folder, rel_path)
    output_dir = os.path.dirname(output_path)
    
    # 检查文件扩展名
    ext = os.path.splitext(file_path)[1].lower()
    
    # ===== 如果是 MP3，直接复制 =====
    if ext == '.mp3':
        try:
            os.makedirs(output_dir, exist_ok=True)
            shutil.copy2(file_path, output_path)
            with stats_lock:
                stats['copied'] += 1
            print(f"📋 [复制] {rel_path}")
            return 'copied'
        except Exception as e:
            with stats_lock:
                stats['failed'] += 1
            print(f"❌ [复制失败] {rel_path}: {e}")
            return 'failed'
    
    # ===== 检查是否为支持的格式 =====
    if ext not in SUPPORTED_FORMATS:
        with stats_lock:
            stats['skipped'] += 1
        print(f"⏭️ [跳过] {rel_path} (不支持的格式)")
        return 'skipped'
    
    # ===== 转换为 MP3 =====
    mp3_output = os.path.splitext(output_path)[0] + '.mp3'
    
    # ===== 如果目标文件已存在，跳过 =====
    if os.path.exists(mp3_output):
        with stats_lock:
            stats['skipped'] += 1
        print(f"⏭️ [跳过] {rel_path} -> 目标已存在")
        return 'skipped'
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # ===== 构建 FFmpeg 命令 =====
        # -i: 输入文件
        # -vn: 不处理视频流（如果有）
        # -acodec libmp3lame: 使用 LAME MP3 编码器
        # -b:a: 音频比特率
        # -q:a: VBR 质量（0最高，9最低）
        # -y: 覆盖输出文件
        cmd = [
            FFMPEG_PATH,
            '-i', file_path,
            '-vn',
            '-acodec', 'libmp3lame',
            *ffmpeg_params,
            '-y',
            mp3_output
        ]
        
        # ===== 执行转换（静默模式，只捕获错误） =====
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            with stats_lock:
                stats['converted'] += 1
            print(f"🎵 [转换] {rel_path} -> {os.path.basename(mp3_output)}")
            return 'converted'
        else:
            with stats_lock:
                stats['failed'] += 1
            # 输出错误信息（只显示关键部分）
            error_msg = result.stderr.split('\n')[-3:] if result.stderr else "未知错误"
            print(f"❌ [转换失败] {rel_path}: {' '.join(error_msg)}")
            return 'failed'
            
    except Exception as e:
        with stats_lock:
            stats['failed'] += 1
        print(f"💥 [异常] {rel_path}: {e}")
        return 'failed'


def main():
    """主函数"""
    global stats
    
    print("=" * 60)
    print("🎧 批量音频转换工具 (FFmpeg + Python)")
    print("=" * 60)
    
    # ===== 检查输入文件夹 =====
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ 错误：输入文件夹不存在: {INPUT_FOLDER}")
        return
    
    # ===== 设置输出文件夹 =====
    output_folder = setup_output_folder()
    
    # ===== 检查 FFmpeg =====
    try:
        subprocess.run([FFMPEG_PATH, '-version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：找不到 FFmpeg，请检查路径: {FFMPEG_PATH}")
        print("   如果 FFmpeg 在环境变量中，请将 FFMPEG_PATH 设置为 'ffmpeg'")
        return
    
    # ===== 收集所有需要处理的文件 =====
    print("\n🔍 正在扫描文件...")
    files_to_process = []
    
    for root, dirs, files in os.walk(INPUT_FOLDER):
        # ===== 跳过 output 文件夹（避免重复处理自己的输出） =====
        if 'output' in dirs:
            dirs.remove('output')
        
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            # ===== 只处理支持的格式 =====
            if ext in SUPPORTED_FORMATS or ext == '.mp3':
                files_to_process.append(file_path)
    
    stats['total'] = len(files_to_process)
    
    if stats['total'] == 0:
        print("⚠️ 没有找到支持的音频文件")
        return
    
    print(f"📊 共找到 {stats['total']} 个文件")
    print(f"⚡ 并发数: {MAX_WORKERS}")
    print(f"🎛️  比特率: {BITRATE}" + (f" (VBR 质量 {VBR_QUALITY})" if USE_VBR else ""))
    print("\n开始处理...\n")
    
    # ===== 准备 FFmpeg 参数 =====
    ffmpeg_params = get_ffmpeg_params()
    
    # ===== 多线程处理 =====
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                process_file, 
                file_path, 
                INPUT_FOLDER, 
                output_folder, 
                ffmpeg_params
            ): file_path 
            for file_path in files_to_process
        }
        
        for future in as_completed(futures):
            # 等待所有任务完成
            pass
    
    # ===== 输出统计结果 =====
    print("\n" + "=" * 60)
    print("✅ 处理完成！")
    print("=" * 60)
    print(f"📊 总文件数: {stats['total']}")
    print(f"🎵 已转换: {stats['converted']}")
    print(f"📋 已复制(MP3): {stats['copied']}")
    print(f"⏭️ 已跳过: {stats['skipped']}")
    print(f"❌ 失败: {stats['failed']}")
    print(f"📁 输出目录: {output_folder}")

if __name__ == "__main__":
    # 1. 先解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitrate", default="320k")
    parser.add_argument("--cbr", action="store_true")
    parser.add_argument("--vbr", action="store_true")
    parser.add_argument("--vbr-quality", default="0")
    parser.add_argument("--workers", default="2")
    args = parser.parse_args()
    
    # 2. 然后用解析后的参数调用 main() 或直接执行代码
    # 如果您的代码有 main() 函数，就传参调用
    # main(bitrate=args.bitrate, use_vbr=args.vbr, ...)
    
    # 或者直接用 args 替换原来的硬编码配置
    BITRATE = args.bitrate
    USE_VBR = args.vbr
    VBR_QUALITY = int(args.vbr_quality)
    MAX_WORKERS = int(args.workers)
    
    # 3. 调用 main() 函数
    main()
