import os
import shutil
import mutagen
import sys
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from pathlib import Path

def get_metadata(file_path):
    """
    提取音乐文件的元数据
    支持 MP3, FLAC, M4A 等格式
    """
    try:
        # 尝试加载文件
        audio = mutagen.File(file_path)
        
        if audio is None:
            return None, None, None
        
        title = None
        artist = None
        album = None
        
        # MP3 格式
        if isinstance(audio, mutagen.mp3.MP3):
            try:
                tags = EasyID3(file_path)
                title = tags.get('title', [None])[0]
                artist = tags.get('artist', [None])[0]
                album = tags.get('album', [None])[0]
            except:
                pass
        
        # FLAC 格式
        elif isinstance(audio, FLAC):
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            album = audio.get('album', [None])[0]
        
        # M4A 格式
        elif isinstance(audio, MP4):
            title = audio.get('\xa9nam', [None])[0]
            artist = audio.get('\xa9ART', [None])[0]
            album = audio.get('\xa9alb', [None])[0]
        
        # 如果使用mutagen无法获取，尝试使用EasyID3 (适用于大多数MP3)
        if title is None and artist is None and album is None:
            try:
                audio = EasyID3(file_path)
                title = audio.get('title', [None])[0]
                artist = audio.get('artist', [None])[0]
                album = audio.get('album', [None])[0]
            except:
                pass
        
        return title, artist, album
    
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return None, None, None

def process_music_files(source_dir, target_dir, check_title=True, check_artist=True, check_album=True):
    """
    处理音乐文件
    :param source_dir: 源文件夹路径
    :param target_dir: 目标文件夹路径
    :param check_title: 是否检查标题
    :param check_artist: 是否检查艺术家
    :param check_album: 是否检查专辑
    """
    # 创建目标文件夹（如果不存在）
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    # 支持的音频文件扩展名
    audio_extensions = {'.mp3', '.flac', '.m4a', '.wma', '.ogg', '.wav'}
    
    # 统计信息
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n匹配条件:")
    print(f"  - 检查标题: {check_title}")
    print(f"  - 检查艺术家: {check_artist}")
    print(f"  - 检查专辑: {check_album}")
    print(f"{'='*50}")
    
    # 遍历源文件夹中的所有文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            # 检查是否为音频文件
            if file_ext not in audio_extensions:
                continue
            
            print(f"\n处理文件: {file}")
            
            # 获取元数据
            title, artist, album = get_metadata(file_path)
            
            # ===== 修改这里：根据用户选择的参数进行判断 =====
            # 检查每个字段是否有值
            has_title = title is not None and str(title).strip() != ''
            has_artist = artist is not None and str(artist).strip() != ''
            has_album = album is not None and str(album).strip() != ''
            
            # 构建条件列表
            conditions_met = []
            if check_title and has_title:
                conditions_met.append("标题")
            if check_artist and has_artist:
                conditions_met.append("艺术家")
            if check_album and has_album:
                conditions_met.append("专辑")
            
            # 判断是否所有勾选的条件都满足
            all_conditions_met = len(conditions_met) == sum([check_title, check_artist, check_album])
            
            if all_conditions_met and sum([check_title, check_artist, check_album]) > 0:
                # 清理文件名中的非法字符
                def clean_filename(text):
                    # 替换Windows文件名中的非法字符
                    illegal_chars = '<>:"/\\|?*'
                    for char in illegal_chars:
                        text = text.replace(char, '')
                    # 去除首尾空格
                    return text.strip()
                
                clean_artist = clean_filename(artist) if artist else "未知艺术家"
                clean_title = clean_filename(title) if title else "未知标题"
                
                # 构建新文件名
                new_filename = f"{clean_title}-{clean_artist}{file_ext}"
                new_file_path = os.path.join(target_dir, new_filename)
                
                # 如果文件名已存在，添加数字后缀
                counter = 1
                original_new_path = new_file_path
                while os.path.exists(new_file_path):
                    name, ext = os.path.splitext(original_new_path)
                    new_file_path = f"{name}_{counter}{ext}"
                    counter += 1
                
                try:
                    # 移动文件
                    shutil.move(file_path, new_file_path)
                    print(f"✓ 已移动并重命名为: {new_filename}")
                    print(f"  标题: {title or '无'}")
                    print(f"  艺术家: {artist or '无'}")
                    print(f"  专辑: {album or '无'}")
                    print(f"  满足条件: {' + '.join(conditions_met)}")
                    processed_count += 1
                except Exception as e:
                    print(f"✗ 移动文件失败: {e}")
                    error_count += 1
            else:
                print(f"✗ 跳过文件（不满足勾选的条件）")
                print(f"  标题: {title or '缺失'}")
                print(f"  艺术家: {artist or '缺失'}")
                print(f"  专辑: {album or '缺失'}")
                if conditions_met:
                    print(f"  已满足: {' + '.join(conditions_met)}")
                else:
                    print(f"  已满足: 无")
                skipped_count += 1
    
    # 输出统计信息
    print(f"\n{'='*50}")
    print(f"处理完成！")
    print(f"已处理: {processed_count} 个文件")
    print(f"已跳过: {skipped_count} 个文件（不满足条件）")
    print(f"错误: {error_count} 个文件")
    print(f"{'='*50}")

if __name__ == "__main__":
    # 解析传入的参数
    check_title = "--title" in sys.argv
    check_artist = "--artist" in sys.argv
    check_album = "--album" in sys.argv
    
    # 如果没有任何参数，默认全部检查
    if not check_title and not check_artist and not check_album:
        check_title = True
        check_artist = True
        check_album = True
        print("未指定参数，默认检查所有条件（标题、艺术家、专辑）")
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置文件夹名称
    source_folder_name = "A_待整理音乐"
    target_folder_name = "A_已整理音乐"
    
    # 构建完整路径
    source_directory = os.path.join(script_dir, source_folder_name)
    target_directory = os.path.join(script_dir, target_folder_name)
    
    # 检查并创建文件夹
    if not os.path.exists(source_directory):
        print(f"错误：源文件夹 '{source_directory}' 不存在！")
        print(f"请确保在 '{script_dir}' 目录下有名为 'A_待整理音乐' 的文件夹")
        sys.exit(1)
    
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
        print(f"已创建目标文件夹: {target_directory}")
    
    print(f"源文件夹: {source_directory}")
    print(f"目标文件夹: {target_directory}")
    print(f"{'='*50}")
    
    # 调用处理函数，传入参数
    process_music_files(
        source_directory, 
        target_directory,
        check_title=check_title,
        check_artist=check_artist,
        check_album=check_album
    )