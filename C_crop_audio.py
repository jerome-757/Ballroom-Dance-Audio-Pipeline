import os
import sys
import pandas as pd
import subprocess
import shutil
import argparse
from pathlib import Path

# ==================== 配置 ====================
os.chdir(os.path.dirname(os.path.abspath(__file__)))
EXCEL_FILE = '舞曲排布_示例.xlsx'
SHEET_NAME = '完整曲序'
AUDIO_FOLDER = 'B_output_mp3'  # 音频文件夹名称（与脚本同级）
OUTPUT_FOLDER = 'C_裁剪输出'
FFMPEG_PATH = 'ffmpeg'

# 淡入淡出配置（单位：秒）
FADE_IN_DURATION = 0.1    # 淡入时长
FADE_OUT_DURATION = 5.0   # 淡出时长

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def shortcut_to_time_info(value):
    """
    将简写数字转换为 (总秒数, 显示文本)
    1.5 -> (90, '1分30秒')
    3.0 -> (180, '3分00秒')
    1.8 -> (108, '1分48秒')
    """
    if pd.isna(value):
        return None, None
    
    # 转换为浮点数
    if isinstance(value, (int, float)):
        minutes = float(value)
    elif isinstance(value, str):
        try:
            minutes = float(value.strip())
        except:
            return None, None
    else:
        return None, None
    
    total_seconds = int(minutes * 60)
    
    # 生成显示文本：X分XX秒（仅用于显示，不再用于文件名）
    mins = total_seconds // 60
    secs = total_seconds % 60
    display_text = f"{mins}分{secs:02d}秒"
    
    return total_seconds, display_text

def find_audio_file(filename):
    """在音频文件夹中查找音频文件"""
    if pd.isna(filename):
        return None
    
    filename = str(filename).strip()
    audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), AUDIO_FOLDER)
    
    # 检查音频文件夹是否存在
    if not os.path.exists(audio_dir):
        return None
    
    # 获取所有MP3文件
    all_mp3_files = [f for f in os.listdir(audio_dir) if f.lower().endswith('.mp3')]
    
    # 1. 精确匹配（包括.mp3）
    target_with_mp3 = filename
    if not target_with_mp3.lower().endswith('.mp3'):
        target_with_mp3 = filename + '.mp3'
    
    for f in all_mp3_files:
        if f == target_with_mp3:
            return os.path.join(audio_dir, f)
    
    # 2. 忽略大小写匹配
    target_lower = filename.lower()
    for f in all_mp3_files:
        f_without_ext = f.lower().replace('.mp3', '')
        if f_without_ext == target_lower:
            return os.path.join(audio_dir, f)
    
    # 3. 包含匹配（文件名包含搜索词）
    for f in all_mp3_files:
        f_without_ext = f.lower().replace('.mp3', '')
        if target_lower in f_without_ext or f_without_ext in target_lower:
            return os.path.join(audio_dir, f)
    
    return None

def build_ffmpeg_command(input_file, start_seconds, duration_seconds, output_file, 
                         fade_in=FADE_IN_DURATION, fade_out=FADE_OUT_DURATION):
    """
    构建带淡入淡出的 ffmpeg 命令
    
    注意：淡入淡出效果只能在音频流上应用，不能和 -t 参数同时使用
    需要先用 -ss 和 -t 裁剪，再用滤镜处理
    """
    # 方法1：使用 filter_complex 一步完成（推荐）
    # 先裁剪，再应用淡入淡出
    cmd = [
        FFMPEG_PATH,
        '-ss', str(start_seconds),  # 开始时间放在 -i 前面可以加速
        '-i', input_file,
        '-t', str(duration_seconds),  # 裁剪时长
        '-filter_complex',
        f'[0:a]afade=t=in:st=0:d={fade_in},afade=t=out:st={duration_seconds - fade_out}:d={fade_out}[a]',
        '-map', '[a]',
        '-c:a', 'libmp3lame',
        '-b:a', '320k',  # VBR 最高质量
        '-y',
        output_file
    ]
    
    return cmd

def build_ffmpeg_command_alt(input_file, start_seconds, duration_seconds, output_file,
                              fade_in=FADE_IN_DURATION, fade_out=FADE_OUT_DURATION):
    """
    方法2：使用两个 afade 滤镜（备用方案）
    适用于某些旧版本的 FFmpeg
    """
    cmd = [
        FFMPEG_PATH,
        '-ss', str(start_seconds),
        '-i', input_file,
        '-t', str(duration_seconds),
        '-af',
        f'afade=t=in:length={fade_in},afade=t=out:start_time={duration_seconds - fade_out}:duration={fade_out}',
        '-c:a', 'libmp3lame',
        '-b:a', '320k',
        '-y',
        output_file
    ]
    
    return cmd

# ==================== 读取 Excel ====================
print("=" * 70)
print("🎵 音频批量裁剪工具 v8（带淡入淡出效果）")
print(f"   淡入: {FADE_IN_DURATION}秒 | 淡出: {FADE_OUT_DURATION}秒")
print("=" * 70)

# # 获取所有音频文件
# audio_files = [f for f in os.listdir('.') if f.endswith('.mp3')] '.'-audio_dir
# print(f"\n📁 找到 {len(audio_files)} 个音频文件")
# 获取所有音频文件（从音频文件夹）
audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), AUDIO_FOLDER)
if not os.path.exists(audio_dir):
    print(f"⚠️ 警告：音频文件夹 '{AUDIO_FOLDER}' 不存在")
    audio_files = []
else:
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
print(f"\n📁 找到 {len(audio_files)} 个音频文件（在 {AUDIO_FOLDER} 文件夹中）")

# 读取 Excel
df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
print(f"📖 读取 Excel: {len(df)} 行数据")

# 自动检测列名
song_col = None
start_col = None
target_col = None

for col in df.columns:
    col_str = str(col)
    if '歌曲名' in col_str:
        song_col = col
    elif '开始时间' in col_str:
        start_col = col
    elif '裁剪后时长' in col_str:
        target_col = col

# 如果没找到，按位置
if song_col is None and len(df.columns) > 4:
    song_col = df.columns[4]  # 第5列
if start_col is None and len(df.columns) > 6:
    start_col = df.columns[6]  # 第7列
if target_col is None and len(df.columns) > 7:
    target_col = df.columns[7]  # 第8列

print(f"\n✅ 列映射：")
print(f"   歌曲名: '{song_col}'")
print(f"   开始时间: '{start_col}'")
print(f"   裁剪后时长: '{target_col}'")

# 显示前几行数据预览
print(f"\n📋 数据预览（前5行）：")
for idx in range(min(5, len(df))):
    row = df.iloc[idx]
    song = row[song_col] if song_col else "N/A"
    target = row[target_col] if target_col else "N/A"
    print(f"   {idx+1}. {song} | 裁剪: {target}")

# ==================== 批量处理 ====================
print(f"\n🎬 开始批量裁剪...")
print("-" * 70)

success_count = 0
fail_count = 0
skip_count = 0
copy_count = 0

for idx, row in df.iterrows():
    # 获取歌曲名
    song_name = row[song_col] if song_col else None
    if pd.isna(song_name):
        continue
    
    song_name = str(song_name).strip()
    if song_name == '' or song_name == 'nan':
        continue
    
    # 查找音频文件
    audio_file = find_audio_file(song_name)
    if not audio_file:
        print(f"❌ [{idx+1:2d}] {song_name[:40]}... - 找不到文件")
        fail_count += 1
        continue
    
    # 获取裁剪时长（数字简写）
    target_value = row[target_col] if target_col else None
    target_seconds, time_display = shortcut_to_time_info(target_value)
    
    if target_seconds is None or target_seconds <= 0:
        # 如果时长为空或无效，直接复制整个文件
        base_name = Path(audio_file).stem
        output_file = os.path.join(OUTPUT_FOLDER, f"{base_name}_原版.mp3")
        
        # 如果输出文件已存在，跳过
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            size_kb = os.path.getsize(output_file) / 1024
            print(f"⏭️  [{idx+1:2d}] {base_name[:35]}... -> 原版 (已存在 {size_kb:.0f} KB)")
            copy_count += 1
            continue
        
        # 复制文件
        try:
            shutil.copy2(audio_file, output_file)
            size_kb = os.path.getsize(output_file) / 1024
            print(f"📋 [{idx+1:2d}] {base_name[:35]}... -> 原版 (复制 {size_kb:.0f} KB)")
            copy_count += 1
            success_count += 1
        except Exception as e:
            print(f"❌ [{idx+1:2d}] {base_name[:35]}... - 复制失败: {str(e)[:50]}")
            fail_count += 1
        continue
    
    # 获取开始时间（支持数字简写）
    start_seconds = 0
    if start_col and not pd.isna(row[start_col]):
        start_value = row[start_col]
        if isinstance(start_value, (int, float)):
            start_seconds = int(start_value * 60) if start_value < 100 else int(start_value)
        elif isinstance(start_value, str) and ':' in start_value:
            parts = start_value.split(':')
            if len(parts) == 3:
                start_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                start_seconds = int(parts[0]) * 60 + int(parts[1])
    
    # 生成输出文件名（使用 "裁剪版" 后缀）
    base_name = Path(audio_file).stem
    output_file = os.path.join(OUTPUT_FOLDER, f"{base_name}_裁剪版.mp3")
    
    # 如果输出文件已存在且大小 > 0，跳过
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
        size_kb = os.path.getsize(output_file) / 1024
        print(f"⏭️  [{idx+1:2d}] {base_name[:35]}... -> 裁剪版 (已存在 {size_kb:.0f} KB)")
        success_count += 1
        continue
    
    print(f"\n🎬 [{idx+1:2d}] {base_name}")
    print(f"   原始文件: {audio_file}")
    print(f"   开始时间: {start_seconds}秒")
    print(f"   裁剪时长: {time_display} ({target_seconds}秒)")
    print(f"   🌊 淡入: {FADE_IN_DURATION}秒 | 淡出: {FADE_OUT_DURATION}秒")
    print(f"   📝 输出文件: {Path(output_file).name}")

    # 构建 ffmpeg 命令（带淡入淡出）
    # 方法1：使用 filter_complex
    cmd = build_ffmpeg_command(audio_file, start_seconds, target_seconds, output_file)
    
    # 如果方法1失败，可以尝试方法2（取消注释）
    # cmd = build_ffmpeg_command_alt(audio_file, start_seconds, target_seconds, output_file)
    
    # 执行命令
    try:
        result = subprocess.run(cmd, capture_output=True, text=False)
        
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            size_kb = os.path.getsize(output_file) / 1024
            print(f"   ✅ 成功: {Path(output_file).name} ({size_kb:.0f} KB)")
            success_count += 1
        else:
            print(f"   ❌ 失败 (返回码: {result.returncode})")
            # 如果失败，尝试使用备用方法
            print(f"   🔄 尝试备用方法...")
            cmd_alt = build_ffmpeg_command_alt(audio_file, start_seconds, target_seconds, output_file)
            try:
                result_alt = subprocess.run(cmd_alt, capture_output=True, text=False)
                if result_alt.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    size_kb = os.path.getsize(output_file) / 1024
                    print(f"   ✅ 备用方法成功: {Path(output_file).name} ({size_kb:.0f} KB)")
                    success_count += 1
                else:
                    print(f"   ❌ 备用方法也失败")
                    fail_count += 1
                    if os.path.exists(output_file) and os.path.getsize(output_file) == 0:
                        os.remove(output_file)
            except Exception as e:
                print(f"   ❌ 备用方法异常: {str(e)[:100]}")
                fail_count += 1
                
    except Exception as e:
        print(f"   ❌ 异常: {str(e)[:100]}")
        fail_count += 1

# ==================== 输出结果 ====================
print("\n" + "=" * 70)
print("📊 处理完成！")
print(f"   ✅ 成功: {success_count} 个")
print(f"   ❌ 失败: {fail_count} 个")
print(f"   📋 复制原版: {copy_count} 个 (无裁剪时长)")
print(f"   📁 输出目录: {os.path.abspath(OUTPUT_FOLDER)}")
print(f"\n🎵 淡入淡出设置:")
print(f"   淡入: {FADE_IN_DURATION}秒")
print(f"   淡出: {FADE_OUT_DURATION}秒")

# 检查输出文件夹
output_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith('.mp3')]
if output_files:
    print(f"\n📋 生成的文件列表:")
    total_size = 0
    for f in sorted(output_files):
        size = os.path.getsize(os.path.join(OUTPUT_FOLDER, f)) / 1024
        total_size += size
        print(f"   - {f} ({size:.0f} KB)")
    print(f"\n   总大小: {total_size/1024:.1f} MB")
else:
    print(f"\n⚠️ 输出文件夹为空，请检查：")
    print(f"   1. Excel 中的'裁剪后时长'列是否有数字（如 1.5, 3.0）")
    print(f"   2. 音频文件是否与脚本在同一目录")

# ==================== 命令行参数支持 ====================
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--fade-in", default="0.1")
    parser.add_argument("--fade-out", default="5.0")
    args = parser.parse_args()
    
    # 用 args 替换硬编码配置
    FADE_IN_DURATION = float(args.fade_in)
    FADE_OUT_DURATION = float(args.fade_out)

print("\n" + "=" * 70)
print("🎵 音频批量裁剪工具 v8（带淡入淡出效果）")
print(f"   淡入: {FADE_IN_DURATION}秒 | 淡出: {FADE_OUT_DURATION}秒")
print("\n" + "=" * 70)