#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🎵 音频处理工具 - 终极完整版   
功能：
  1. 支持所有音频格式
  2. 自动重试失败文件
  3. 多种TTS引擎（Edge/Google/本地）
  4. 代理支持
  5. 语音缓存
  6. 网络错误处理
  7. 断点续传
  8. 详细日志
"""

import asyncio
import os
import subprocess
import glob
import re
import time
import json
import shutil
import hashlib
import sys
import random
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import tkinter as tk
from tkinter import messagebox

# ============================================================
# 🔧 用户可修改的配置参数
# ============================================================

# 基本配置
BGM_TOTAL_DURATION = 8          # 背景音乐总时长（秒）
BGM_START_TIME = 0               # 背景音乐从第几秒开始截取
SPEECH_POSITION = "middle"       # 语音位置: "start", "middle", "end" 或秒数
BGM_VOLUME = 0.2                 # 背景音乐音量（0.1 ~ 1.0）
AUDIO_SOURCE_FOLDER = "C_裁剪输出"  # 音频源文件夹
OUTPUT_SUFFIX = "-魅影制作"        # 输出文件名后缀
OUTPUT_SUBFOLDER = "D_output"      # 输出子文件夹名
EXTRACT_DANCE = False             # 是否提取舞种名称（默认False，会在运行时弹窗询问）

# BGM 文件名（会自动在文件夹里找）
BGM_NAMES = ["bgm.mp3", "bgm.MP3", "背景音乐.mp3", "background.mp3"]

# 支持的音频格式
SUPPORTED_FORMATS = ['.mp3', '.MP3', '.wav', '.WAV', '.flac', '.FLAC', 
                     '.m4a', '.M4A', '.aac', '.AAC', '.ogg', '.OGG',
                     '.wma', '.WMA', '.ape', '.APE', '.opus', '.OPUS',
                     '.webm', '.WEBM', '.aiff', '.AIFF']

# ============================================================
# 🌐 网络和TTS配置
# ============================================================

# TTS引擎选择: 'edge' (微软) 或 'gtts' (谷歌) 或 'local' (本地)
# 优先级: edge > gtts > local (失败自动降级)
TTS_ENGINE = 'edge'

# 代理设置（解决网络问题）
# 格式: 'http://127.0.0.1:7890' 或 'socks5://127.0.0.1:1080'
PROXY = None  # 例如: PROXY = 'http://127.0.0.1:7890'

# 本地TTS配置（当网络不可用时使用）
LOCAL_TTS_VOICE = 'zh-CN'  # 本地语音
LOCAL_TTS_SPEED = 150      # 语速 (100-200)

# ============================================================
# 🔄 重试和缓存配置
# ============================================================

# 重试配置
MAX_RETRIES_PER_FILE = 5     # 每个文件最大重试次数
MAX_TOTAL_RETRIES = 3          # 所有文件整体重试次数
REQUEST_INTERVAL = 1.0         # 请求间隔（秒），避免频率限制
RETRY_DELAY_BASE = 3           # 重试延迟基数（指数退避）

# 缓存配置
CACHE_SPEECH = True            # 是否缓存语音
CACHE_FOLDER = "speech_cache"  # 缓存文件夹
CACHE_EXPIRE_DAYS = 30         # 缓存过期天数

# 失败记录
FAILED_LOG = "failed_files.json"

# ============================================================
# 🎵 音频质量配置
# ============================================================

# 音频编码质量
# 方式1: 使用质量参数 (0=最高, 9=最低)
#AUDIO_QUALITY = '-q:a'
#AUDIO_QUALITY_VALUE = '0'

# 方式2: 使用码率 (取消下面注释，并注释上面的)
AUDIO_QUALITY = '-b:a'
AUDIO_QUALITY_VALUE = '320k'

# 淡入淡出参数
FADE_OUT_DUR = 3.0   # 前奏淡出时长（秒）
FADE_IN_DUR = 5.0    # 原曲淡入时长（秒）

# ============================================================
# 📝 日志配置
# ============================================================

LOG_ENABLED = True
LOG_FILE = "processing.log"
DEBUG_MODE = False  # 调试模式，显示更多信息

# ============================================================


class Logger:
    """日志管理器"""
    
    def __init__(self, log_file=LOG_FILE, enabled=True):
        self.log_file = log_file
        self.enabled = enabled
        if enabled:
            # 清空或创建日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== 处理日志 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    def log(self, message, level='INFO'):
        """记录日志"""
        if not self.enabled:
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass
    
    def info(self, message):
        self.log(message, 'INFO')
    
    def warning(self, message):
        self.log(message, 'WARNING')
    
    def error(self, message):
        self.log(message, 'ERROR')
    
    def debug(self, message):
        if DEBUG_MODE:
            self.log(message, 'DEBUG')


class TTSEngine:
    """TTS引擎管理器 - 支持多种TTS引擎"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.current_engine = TTS_ENGINE
        self.edge_available = True
        self.gtts_available = True
        self.local_available = True
        self.failure_count = 0
        self.last_request_time = 0
        self.cache_folder = CACHE_FOLDER
        self.cache = {}
        
        # 创建缓存文件夹
        os.makedirs(self.cache_folder, exist_ok=True)
        
        # 加载缓存
        self._load_cache()
        
        # 检查本地TTS
        self._check_local_tts()
    
    def _load_cache(self):
        """加载语音缓存"""
        if not CACHE_SPEECH:
            return
        
        try:
            for f in os.listdir(self.cache_folder):
                if f.endswith('.mp3'):
                    text_hash = f.replace('.mp3', '')
                    file_path = os.path.join(self.cache_folder, f)
                    
                    # 检查是否过期
                    if CACHE_EXPIRE_DAYS > 0:
                        mtime = os.path.getmtime(file_path)
                        if time.time() - mtime > CACHE_EXPIRE_DAYS * 24 * 3600:
                            os.remove(file_path)
                            continue
                    
                    self.cache[text_hash] = file_path
            
            self.logger.info(f"加载缓存: {len(self.cache)} 个文件")
        except Exception as e:
            self.logger.error(f"加载缓存失败: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached_speech(self, text: str) -> Optional[str]:
        """获取缓存的语音"""
        if not CACHE_SPEECH:
            return None
        
        key = self._get_cache_key(text)
        if key in self.cache and os.path.exists(self.cache[key]):
            return self.cache[key]
        return None
    
    def _cache_speech(self, text: str, file_path: str):
        """缓存语音"""
        if not CACHE_SPEECH:
            return
        
        try:
            key = self._get_cache_key(text)
            cache_file = os.path.join(self.cache_folder, f"{key}.mp3")
            shutil.copy2(file_path, cache_file)
            self.cache[key] = cache_file
            self.logger.debug(f"缓存语音: {text[:20]}...")
        except Exception as e:
            self.logger.error(f"缓存失败: {e}")
    
    def _check_local_tts(self):
        """检查本地TTS是否可用"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.getProperty('voices')
            engine.stop()
            self.local_available = True
            self.logger.info("本地TTS (pyttsx3) 可用")
        except ImportError:
            self.local_available = False
            self.logger.warning("本地TTS (pyttsx3) 未安装，跳过")
        except Exception as e:
            self.local_available = False
            self.logger.warning(f"本地TTS初始化失败: {e}")
    
    async def _wait_for_rate_limit(self):
        """限流等待"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < REQUEST_INTERVAL:
            await asyncio.sleep(REQUEST_INTERVAL - time_since_last)
        self.last_request_time = time.time()
    
    async def generate_speech(self, text: str, output_file: str) -> bool:
        """生成语音（自动选择引擎）"""
        # 1. 检查缓存
        cached_file = self._get_cached_speech(text)
        if cached_file:
            try:
                shutil.copy2(cached_file, output_file)
                self.logger.debug(f"使用缓存: {text[:20]}...")
                return True
            except Exception as e:
                self.logger.error(f"缓存复制失败: {e}")
        
        # 2. 尝试各个引擎
        engines = []
        
        # 根据配置决定引擎顺序
        if self.current_engine == 'edge' and self.edge_available:
            engines.append(('edge', self._generate_edge))
        if self.current_engine == 'gtts' and self.gtts_available:
            engines.append(('gtts', self._generate_gtts))
        if self.current_engine == 'local' and self.local_available:
            engines.append(('local', self._generate_local))
        
        # 如果当前引擎不可用，尝试其他引擎
        if not engines:
            # 按优先级添加所有可用引擎
            if self.edge_available:
                engines.append(('edge', self._generate_edge))
            if self.gtts_available:
                engines.append(('gtts', self._generate_gtts))
            if self.local_available:
                engines.append(('local', self._generate_local))
        
        # 3. 尝试每个引擎
        for engine_name, engine_func in engines:
            self.logger.info(f"尝试 {engine_name} TTS...")
            
            for attempt in range(MAX_RETRIES_PER_FILE):
                try:
                    # 限流
                    await self._wait_for_rate_limit()
                    
                    # 生成语音
                    success = await engine_func(text, output_file)
                    
                    if success and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        # 缓存
                        self._cache_speech(text, output_file)
                        self.failure_count = 0
                        self.current_engine = engine_name
                        self.logger.info(f"✅ {engine_name} TTS 成功")
                        return True
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    error_msg = str(e)
                    self.logger.warning(f"{engine_name} 尝试 {attempt+1}/{MAX_RETRIES_PER_FILE} 失败: {error_msg[:80]}")
                    
                    # 网络错误 - 指数退避
                    if any(keyword in error_msg.lower() for keyword in ['connect', 'timeout', 'network', 'ssl']):
                        delay = RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                        self.logger.debug(f"等待 {delay:.1f} 秒后重试...")
                        await asyncio.sleep(delay)
                    else:
                        await asyncio.sleep(RETRY_DELAY_BASE)
                    
                    # 如果Edge连续失败，标记为不可用
                    if engine_name == 'edge' and attempt >= 2:
                        self.edge_available = False
                        self.logger.warning("Edge TTS 连续失败，标记为不可用")
                        break
        
        self.logger.error(f"所有TTS引擎都失败: {text[:20]}...")
        return False
    
    async def _generate_edge(self, text: str, output_file: str) -> bool:
        """使用Edge TTS"""
        try:
            import edge_tts
            
            # 设置代理
            if PROXY:
                os.environ['HTTP_PROXY'] = PROXY
                os.environ['HTTPS_PROXY'] = PROXY
            
            # 创建communicate
            communicate = edge_tts.Communicate(text, "zh-CN-YunjianNeural")
            
            # 异步保存（带超时）
            await asyncio.wait_for(communicate.save(output_file), timeout=30)
            
            return True
        except ImportError:
            self.edge_available = False
            raise Exception("Edge TTS 未安装")
        except asyncio.TimeoutError:
            raise Exception("Edge TTS 超时")
        except Exception as e:
            raise
    
    async def _generate_gtts(self, text: str, output_file: str) -> bool:
        """使用Google TTS"""
        try:
            from gtts import gTTS
            
            # gTTS是同步的，在executor中运行
            loop = asyncio.get_event_loop()
            
            def _gtts_sync():
                tts = gTTS(text=text, lang='zh-cn', slow=False)
                tts.save(output_file)
            
            await asyncio.wait_for(
                loop.run_in_executor(None, _gtts_sync),
                timeout=20
            )
            
            return True
        except ImportError:
            self.gtts_available = False
            raise Exception("Google TTS (gTTS) 未安装")
        except asyncio.TimeoutError:
            raise Exception("Google TTS 超时")
        except Exception as e:
            raise
    
    async def _generate_local(self, text: str, output_file: str) -> bool:
        """使用本地TTS"""
        try:
            import pyttsx3
            
            def _local_tts_sync():
                engine = pyttsx3.init()
                
                # 设置语音
                voices = engine.getProperty('voices')
                for voice in voices:
                    if LOCAL_TTS_VOICE in voice.id:
                        engine.setProperty('voice', voice.id)
                        break
                
                # 设置语速
                engine.setProperty('rate', LOCAL_TTS_SPEED)
                
                # 保存为wav，然后用ffmpeg转mp3
                temp_wav = output_file.replace('.mp3', '.wav')
                engine.save_to_file(text, temp_wav)
                engine.runAndWait()
                engine.stop()
                
                # 转换为mp3
                if os.path.exists(temp_wav):
                    cmd = [
                        'ffmpeg',
                        '-i', temp_wav,
                        '-c:a', 'libmp3lame',
                        '-b:a', '320k',
                        '-y',
                        output_file
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)
                    os.remove(temp_wav)
                    return True
                return False
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, _local_tts_sync)
            return success
            
        except ImportError:
            self.local_available = False
            raise Exception("本地TTS (pyttsx3) 未安装")
        except Exception as e:
            raise


class SmartRetryManager:
    """智能重试管理器"""
    
    def __init__(self, logger: Logger, log_file: str = FAILED_LOG):
        self.logger = logger
        self.log_file = log_file
        self.failed_files = []
        self.processed_files = set()
        self.success_files = set()
        self.total_retries = 0
        self.max_retries = MAX_TOTAL_RETRIES
        self.start_time = time.time()
        
        # 加载失败记录
        self.load_failed_log()
    
    def load_failed_log(self):
        """加载失败日志"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.failed_files = data.get('failed', [])
                    self.processed_files = set(data.get('processed', []))
                    self.success_files = set(data.get('success', []))
                    self.total_retries = data.get('retry_count', 0)
                
                # 过滤不存在的文件
                existing = [f for f in self.failed_files if os.path.exists(f)]
                if len(existing) != len(self.failed_files):
                    self.failed_files = existing
                    self.save_failed_log()
                
                self.logger.info(f"加载失败日志: {len(self.failed_files)} 个文件待重试")
            except Exception as e:
                self.logger.error(f"加载失败日志错误: {e}")
                self.failed_files = []
                self.processed_files = set()
                self.success_files = set()
                self.total_retries = 0
    
    def save_failed_log(self):
        """保存失败日志"""
        try:
            data = {
                'failed': self.failed_files,
                'processed': list(self.processed_files),
                'success': list(self.success_files),
                'retry_count': self.total_retries,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_time': f"{time.time() - self.start_time:.1f}秒"
            }
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存失败日志错误: {e}")
    
    def add_failed(self, file_path: str):
        """添加失败文件"""
        if file_path not in self.failed_files:
            self.failed_files.append(file_path)
        self.save_failed_log()
    
    def remove_failed(self, file_path: str):
        """移除成功的文件"""
        if file_path in self.failed_files:
            self.failed_files.remove(file_path)
        self.processed_files.add(file_path)
        self.success_files.add(file_path)
        self.save_failed_log()
    
    def get_failed_files(self) -> List[str]:
        """获取失败文件列表"""
        existing = [f for f in self.failed_files if os.path.exists(f)]
        self.failed_files = existing
        self.save_failed_log()
        return existing
    
    def should_continue(self) -> bool:
        """是否应该继续重试"""
        if self.total_retries >= self.max_retries:
            return False
        return len(self.get_failed_files()) > 0
    
    def increment_retry(self):
        """增加重试计数"""
        self.total_retries += 1
        self.save_failed_log()
    
    def get_summary(self) -> Dict:
        """获取处理摘要"""
        return {
            'total': len(self.processed_files) + len(self.failed_files),
            'success': len(self.success_files),
            'failed': len(self.failed_files),
            'retries': self.total_retries,
            'elapsed': f"{time.time() - self.start_time:.1f}秒"
        }


def get_audio_duration(audio_file: str) -> float:
    """获取音频文件时长"""
    try:
        cmd = f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{audio_file}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            return float(result.stdout.strip())
    except:
        pass
    return 3.0


def extract_dance_name(filename: str) -> str:
    """智能提取舞蹈名称"""
    DANCE_PATTERNS = [
        # 特殊词组（必须在前面）
        ("维也纳华尔兹", "摩登舞，维也纳华尔兹"),
        ("休闲伦巴", "交谊舞，休闲伦巴"),
        
        # 国标舞
        ("华尔兹", "摩登舞，华尔兹"),
        ("探戈", "摩登舞，探戈"),
        ("狐步", "摩登舞，狐步"),
        ("快步", "摩登舞，快步"),
        ("伦巴", "拉丁舞，伦巴"),
        ("恰恰", "拉丁舞，恰恰"),
        ("桑巴", "拉丁舞，桑巴"),
        ("牛仔", "拉丁舞，牛仔"),
        ("斗牛", "拉丁舞，斗牛"),
        
        # 地方舞
        ("三步踩", "地方舞，武汉三步踩"),
        ("平四", "地方舞，北京平四"),
        
        # 交谊舞
        ("慢三", "交谊舞，慢三"),
        ("慢四", "交谊舞，慢四"),
        ("中三", "交谊舞，中四"),
        ("中四", "交谊舞，中四"),
        ("快三", "交谊舞，快三"),
        ("快四", "交谊舞，快四"),
        ("并四", "交谊舞，并四"),
        ("吉特巴", "交谊舞，吉特巴"),
        ("点帕斯", "交谊舞，点帕斯"),
        ("水兵舞", "交谊舞，水兵舞"),
        ("鬼步舞", "交谊舞，鬼步舞"),
        
        # 集体舞
        ("兔子舞", "集体舞，兔子舞"),
        ("十六步", "集体舞，十六步"),
        ("三十二步", "集体舞，三十二步"),
        
        # 网红舞
        ("汉舞", "网红舞，汉舞王伦巴"),
        ("唐舞", "网红舞，唐舞伦巴"),        
        ("周舞", "网红舞，周舞伦巴"),
        
        # 其他
        ("DJ", "DJ混音舞曲、大家一起嗨起来"),
        ("慢摇", "慢摇"),
        ("肚皮舞", "肚皮舞"),
        ("街舞", "街舞"),
        ("爵士", "爵士"),
        ("芭蕾", "芭蕾"),
        ("现代舞", "现代舞"),
        ("民族舞", "民族舞"),
        ("古典舞", "古典舞"),
    ]
    
    # 从书名号中提取
    bracket_match = re.search(r'[《【\[].*?[》】\]]', filename)
    if bracket_match:
        content = bracket_match.group()[1:-1]
        for keyword, dance_name in DANCE_PATTERNS:
            if keyword in content:
                return dance_name
    
    # 扫描整个文件名
    for keyword, dance_name in DANCE_PATTERNS:
        if keyword in filename:
            return dance_name
    
    return "舞蹈"


async def process_one_file(
    input_file: str,
    bgm_file: str,
    output_folder: str,
    tts_engine: TTSEngine,
    logger: Logger
) -> bool:
    """处理单个文件"""
    temp_speech = None
    
    try:
        filename = os.path.basename(input_file)
        name_no_ext = os.path.splitext(filename)[0]
        
        # 识别舞蹈名称（仅在需要时）
        dance_name = extract_dance_name(filename)
        logger.info(f"处理: {filename}")
        print(f"  🎵 {filename}")
        
        # 生成语音
        temp_speech = os.path.join(output_folder, "__temp_speech.mp3")
        
        if EXTRACT_DANCE:
            # 需要提取舞种名称
            speech_text = f"下面请欣赏{dance_name}"
            print(f"  💃 舞蹈: {dance_name}")
            
            success = await tts_engine.generate_speech(speech_text, temp_speech)
            
            if not success or not os.path.exists(temp_speech) or os.path.getsize(temp_speech) == 0:
                logger.error(f"语音生成失败: {filename}")
                print(f"  ❌ 语音生成失败")
                return False
            
            # 获取语音时长
            speech_dur = get_audio_duration(temp_speech)
            print(f"  ⏱️  语音时长: {speech_dur:.1f}秒")
        else:
            # 不提取舞种名称，生成静音
            print(f"  🔇 不提取舞种名称")
            speech_dur = 0.1  # 设置一个很短的时长
            # 创建一个静音文件
            cmd_silence = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'anullsrc=r=44100:cl=mono',
                '-t', '0.1',
                '-c:a', 'libmp3lame',
                '-b:a', '320k',
                '-y',
                temp_speech
            ]
            subprocess.run(cmd_silence, capture_output=True, check=True)

        # 计算语音位置
        if not EXTRACT_DANCE:
            # 不提取舞种时，语音位置设为0
            speech_start = 0
        elif isinstance(SPEECH_POSITION, (int, float)):
            speech_start = SPEECH_POSITION
        elif SPEECH_POSITION == "start":
            speech_start = 0
        elif SPEECH_POSITION == "end":
            speech_start = BGM_TOTAL_DURATION - speech_dur
        else:  # "middle"
            speech_start = (BGM_TOTAL_DURATION - speech_dur) / 2
        
        speech_start = max(0, min(speech_start, BGM_TOTAL_DURATION - speech_dur))
        if EXTRACT_DANCE:
            print(f"  🎚️  语音在第 {speech_start:.1f} 秒开始")

        # 准备输出文件
        input_ext = os.path.splitext(input_file)[1]
        output_file = os.path.join(output_folder, f"{name_no_ext}{OUTPUT_SUFFIX}{input_ext}")
        
        # 构建FFmpeg滤镜
        filter_complex = (
            f"[1:a]atrim={BGM_START_TIME}:{BGM_START_TIME+BGM_TOTAL_DURATION},"
            f"volume={BGM_VOLUME}[bgm];"
            f"[0:a]adelay={int(speech_start*1000)}|{int(speech_start*1000)}[speech_delayed];"
            f"[bgm][speech_delayed]amix=inputs=2:duration=first:"
            f"dropout_transition={BGM_TOTAL_DURATION}[intro];"
            f"[intro]atrim=0:{BGM_TOTAL_DURATION},"
            f"afade=t=out:st={BGM_TOTAL_DURATION-FADE_OUT_DUR}:d={FADE_OUT_DUR}[intro_faded];"
            f"[2:a]afade=t=in:d={FADE_IN_DUR}[music_faded];"
            f"[intro_faded][music_faded]concat=n=2:v=0:a=1"
        )
        
        # 质量参数
        quality_params = []
        if AUDIO_QUALITY and AUDIO_QUALITY_VALUE:
            quality_params.extend([AUDIO_QUALITY, AUDIO_QUALITY_VALUE])
        
        # FFmpeg命令
        cmd = [
            'ffmpeg',
            '-i', temp_speech,
            '-i', bgm_file,
            '-i', input_file,
            '-filter_complex', filter_complex,
            '-c:a', 'libmp3lame',
        ] + quality_params + [
            '-y',
            output_file
        ]
        
        # 执行FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
        
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"✅ 成功: {os.path.basename(output_file)}")
            print(f"  ✅ 成功 → {os.path.basename(output_file)}")
            return True
        
        # 如果失败，尝试输出为MP3
        output_file_mp3 = os.path.join(output_folder, f"{name_no_ext}{OUTPUT_SUFFIX}.mp3")
        cmd_alt = [
            'ffmpeg',
            '-i', temp_speech,
            '-i', bgm_file,
            '-i', input_file,
            '-filter_complex', filter_complex,
            '-c:a', 'libmp3lame',
        ] + quality_params + [
            '-y',
            output_file_mp3
        ]
        
        result_alt = subprocess.run(cmd_alt, capture_output=True, text=True, encoding='utf-8', timeout=60)
        
        if result_alt.returncode == 0 and os.path.exists(output_file_mp3) and os.path.getsize(output_file_mp3) > 0:
            logger.info(f"✅ 成功(MP3): {os.path.basename(output_file_mp3)}")
            print(f"  ✅ 成功（转为MP3） → {os.path.basename(output_file_mp3)}")
            return True
        
        # 失败
        logger.error(f"FFmpeg失败: {filename}")
        if result.stderr:
            error_lines = result.stderr.strip().split('\n')
            for line in error_lines[-3:]:
                logger.error(f"  {line}")
                if DEBUG_MODE:
                    print(f"  ⚠️  {line}")
        return False
        
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg超时: {os.path.basename(input_file)}")
        print(f"  ❌ 处理超时")
        return False
    except Exception as e:
        logger.error(f"处理错误: {os.path.basename(input_file)} - {e}")
        print(f"  ❌ 错误: {e}")
        return False
    finally:
        # 清理临时文件
        if temp_speech and os.path.exists(temp_speech):
            try:
                os.remove(temp_speech)
            except:
                pass


def check_ffmpeg() -> bool:
    """检查FFmpeg是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def check_dependencies() -> Tuple[bool, List[str]]:
    """检查依赖"""
    missing = []
    
    # 检查FFmpeg
    if not check_ffmpeg():
        missing.append("FFmpeg (未安装或不在PATH中)")
    
    # 检查Python包
    try:
        import edge_tts
    except ImportError:
        missing.append("edge-tts (pip install edge-tts)")
    
    try:
        import gtts
    except ImportError:
        missing.append("gTTS (pip install gTTS)")
    
    try:
        import pyttsx3
    except ImportError:
        missing.append("pyttsx3 (pip install pyttsx3) - 可选")
    
    return len(missing) == 0, missing


async def main():
    """主函数"""
    # 初始化日志
    logger = Logger()
    logger.info("="*70)
    logger.info("🎵 音频处理工具 - 终极完整版")
    logger.info("="*70)
    
    # 打印标题
    print("="*70)
    print("🎵 音频处理工具 - 终极完整版")
    print("="*70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 弹窗询问是否提取舞种名称
    global EXTRACT_DANCE
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    result = messagebox.askquestion(
        "舞种提取",
        "是否要提取舞种名称？\n\n点击【是】= 提取舞种名称\n点击【否】= 不提取舞种名称（默认）",
        parent=root,
        default='no'  # 设置默认按钮为"否"
    )
    
    EXTRACT_DANCE = (result == 'yes')
    root.destroy()
    
    if EXTRACT_DANCE:
        print("✅ 已选择：提取舞种名称")
        logger.info("用户选择：提取舞种名称")
    else:
        print("✅ 已选择：不提取舞种名称")
        logger.info("用户选择：不提取舞种名称")
    print()
    
    # 检查依赖
    print("🔍 检查依赖...")
    ok, missing = check_dependencies()
    if not ok:
        print("❌ 缺少以下依赖:")
        for item in missing:
            print(f"  - {item}")
        print("\n请安装后重试:")
        print("  pip install edge-tts gtts pyttsx3")
        print("  并确保 FFmpeg 已安装")
        logger.error(f"依赖检查失败: {missing}")
        return
    print("✅ 依赖检查通过")
    print()
    
    # 初始化TTS引擎
    tts_engine = TTSEngine(logger)
    print(f"🗣️  TTS引擎: {tts_engine.current_engine}")
    if PROXY:
        print(f"🌐 代理: {PROXY}")
    print(f"💾 语音缓存: {'启用' if CACHE_SPEECH else '禁用'}")
    print(f"🔄 最大重试: {MAX_RETRIES_PER_FILE}次/文件, {MAX_TOTAL_RETRIES}轮")
    print()
    
    # 初始化重试管理器
    retry_manager = SmartRetryManager(logger)
    
    # 查找背景音乐
    CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
    bgm_file = None
    
    print("🔍 查找背景音乐...")
    for name in BGM_NAMES:
        test_path = os.path.join(CURRENT_FOLDER, name)
        if os.path.exists(test_path):
            bgm_file = test_path
            print(f"✅ BGM: {name}")
            break
    
    if not bgm_file:
        for f in os.listdir(CURRENT_FOLDER):
            f_lower = f.lower()
            if any(f_lower.endswith(ext.lower()) for ext in SUPPORTED_FORMATS) and 'bgm' in f_lower:
                bgm_file = os.path.join(CURRENT_FOLDER, f)
                print(f"✅ BGM（自动识别）: {f}")
                break
    
    if not bgm_file:
        print("❌ 未找到背景音乐！")
        logger.error("未找到背景音乐")
        return
    
    # 创建输出文件夹
    output_folder = os.path.join(CURRENT_FOLDER, OUTPUT_SUBFOLDER)
    os.makedirs(output_folder, exist_ok=True)
    logger.info(f"输出文件夹: {output_folder}")
    
    # ============================================================
    # 主处理循环
    # ============================================================
    round_num = 1
    
    while True:
        # 获取要处理的文件列表
        if round_num == 1:
            # 第一轮：处理所有文件
            audio_files = []
            audio_source_path = os.path.join(CURRENT_FOLDER, AUDIO_SOURCE_FOLDER)

            if not os.path.exists(audio_source_path):
                print(f"⚠️ 警告：音频源文件夹 '{AUDIO_SOURCE_FOLDER}' 不存在")
                print(f"   期望路径: {audio_source_path}")
                audio_files = []
            else:
                for ext in SUPPORTED_FORMATS:
                    for f in glob.glob(os.path.join(audio_source_path, f"*{ext}")):
                        basename = os.path.basename(f).lower()
                        if basename in [n.lower() for n in BGM_NAMES]:
                            continue
                        if bgm_file and os.path.normpath(f) == os.path.normpath(bgm_file):
                            continue
                        if ('__temp' not in f 
                            and OUTPUT_SUBFOLDER not in f
                            and OUTPUT_SUFFIX not in f
                            and f not in retry_manager.processed_files):
                            audio_files.append(f)
            
            audio_files = list(set(audio_files))
            
            if not audio_files:
                print("❌ 未找到音频文件")
                logger.warning("未找到音频文件")
                return
            
            print(f"\n📁 找到 {len(audio_files)} 个文件待处理")
            print(f"🎚️  BGM {BGM_TOTAL_DURATION}秒 | 语音位置: {SPEECH_POSITION}")
            print()
            logger.info(f"开始处理 {len(audio_files)} 个文件")
            
        else:
            # 后续轮次：只处理失败的文件
            audio_files = retry_manager.get_failed_files()
            if not audio_files:
                print("\n🎉 所有文件已成功处理！")
                logger.info("所有文件处理完成")
                break
            
            print(f"\n🔄 第 {round_num} 轮重试: {len(audio_files)} 个失败文件")
            print(f"📊 已完成: {len(retry_manager.success_files)}/{len(retry_manager.processed_files) + len(audio_files)}")
            print()
            logger.info(f"第 {round_num} 轮重试: {len(audio_files)} 个文件")
        
        # 处理文件
        success_count = 0
        fail_count = 0
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"[{i}/{len(audio_files)}]", end="")
            result = await process_one_file(
                audio_file, bgm_file, output_folder, tts_engine, logger
            )
            
            if result:
                success_count += 1
                retry_manager.remove_failed(audio_file)
            else:
                fail_count += 1
                if round_num == 1:
                    retry_manager.add_failed(audio_file)
            
            # 进度显示
            if i % 5 == 0 or i == len(audio_files):
                print(f"  📊 进度: {i}/{len(audio_files)} | ✅ {success_count} | ❌ {fail_count}")
        
        # 显示本轮结果
        print(f"\n📊 第 {round_num} 轮完成:")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ❌ 失败: {fail_count}")
        logger.info(f"第 {round_num} 轮完成: 成功={success_count}, 失败={fail_count}")
        
        # 检查是否还有失败文件
        remaining_failed = retry_manager.get_failed_files()
        if remaining_failed:
            retry_manager.increment_retry()
            print(f"\n⏳ 还有 {len(remaining_failed)} 个文件失败")
            
            if retry_manager.total_retries >= MAX_TOTAL_RETRIES:
                print(f"⚠️  已达到最大重试次数 ({MAX_TOTAL_RETRIES})")
                print("\n📋 失败文件列表:")
                for f in remaining_failed:
                    print(f"  ❌ {os.path.basename(f)}")
                
                # 保存详细的失败报告
                report_file = f"failed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write("失败文件报告\n")
                    f.write("="*50 + "\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"失败文件数: {len(remaining_failed)}\n\n")
                    for ff in remaining_failed:
                        f.write(f"  - {os.path.basename(ff)}\n")
                        f.write(f"    路径: {ff}\n\n")
                
                print(f"\n📄 失败报告已保存: {report_file}")
                logger.error(f"最终失败: {len(remaining_failed)} 个文件")
                break
            else:
                print(f"🔄 将在下一轮重试...")
                logger.info(f"准备第 {retry_manager.total_retries + 1} 轮重试")
                round_num += 1
                # 等待一下再开始下一轮
                await asyncio.sleep(5)
        else:
            print("\n🎉 所有文件处理成功！")
            logger.info("🎉 所有文件处理成功")
            break
    
    # 显示最终统计
    summary = retry_manager.get_summary()
    print("\n" + "="*70)
    print("📊 最终统计:")
    print(f"  📄 总文件数: {summary['total']}")
    print(f"  ✅ 成功: {summary['success']}")
    print(f"  ❌ 失败: {summary['failed']}")
    print(f"  🔄 重试轮次: {summary['retries']}")
    print(f"  ⏱️  用时: {summary['elapsed']}")
    print(f"  📁 输出文件夹: {output_folder}")
    print("="*70)
    
    # 日志统计
    logger.info(f"最终统计: {summary}")
    
    # 失败文件的建议
    if summary['failed'] > 0:
        print("\n💡 解决建议:")
        print("  1. 检查网络连接，或设置代理: PROXY = 'http://127.0.0.1:7890'")
        print("  2. 更换TTS引擎: TTS_ENGINE = 'gtts' 或 'local'")
        print("  3. 增加重试次数: MAX_RETRIES_PER_FILE = 20")
        print("  4. 增加请求间隔: REQUEST_INTERVAL = 2.0")
        print("  5. 查看日志: processing.log")
        print("  6. 再次运行脚本自动重试失败文件")
        print("  7. 检查文件是否损坏或格式异常")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", default="8")
    parser.add_argument("--start", default="0")
    parser.add_argument("--position", default="middle")
    parser.add_argument("--volume", default="0.2")
    args = parser.parse_args()
    
    # 用 args 替换硬编码配置
    BGM_TOTAL_DURATION = float(args.duration)
    BGM_START_TIME = float(args.start)
    SPEECH_POSITION = args.position
    # 如果是数字字符串，转换为float
    try:
        SPEECH_POSITION = float(SPEECH_POSITION)
    except:
        pass
    BGM_VOLUME = float(args.volume)
    
    # 然后执行你的主逻辑
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
    # main() 或直接执行代码