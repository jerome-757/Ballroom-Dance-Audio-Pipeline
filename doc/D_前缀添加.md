# 🎵 音频处理工具 - 终极完整版



## 📋 功能列表

- 支持所有音频格式
- 自动重试失败文件
- 多种TTS引擎（Edge/Google/本地）
- 代理支持
- 语音缓存
- 网络错误处理
- 断点续传
- 详细日志

------



## 🔧 用户配置参数

### 基本配置

- `BGM_TOTAL_DURATION = 8` # 背景音乐总时长（秒）
- `BGM_START_TIME = 0` # 背景音乐从第几秒开始截取
- `SPEECH_POSITION = "middle"` # 语音位置: "start", "middle", "end" 或秒数
- `BGM_VOLUME = 0.2` # 背景音乐音量（0.1 ~ 1.0）
- `AUDIO_SOURCE_FOLDER = "C_裁剪输出"` # 音频源文件夹
- `OUTPUT_SUFFIX = "-魅影制作"` # 输出文件名后缀
- `OUTPUT_SUBFOLDER = "D_output"` # 输出子文件夹名

### BGM 文件名

- `BGM_NAMES = ["bgm.mp3", "bgm.MP3", "背景音乐.mp3", "background.mp3"]`

### 支持的音频格式

- `.mp3`, `.MP3`, `.wav`, `.WAV`, `.flac`, `.FLAC`
- `.m4a`, `.M4A`, `.aac`, `.AAC`, `.ogg`, `.OGG`
- `.wma`, `.WMA`, `.ape`, `.APE`, `.opus`, `.OPUS`
- `.webm`, `.WEBM`, `.aiff`, `.AIFF`

------



## 🌐 网络和TTS配置

### TTS引擎选择

- `TTS_ENGINE = 'edge'` # 'edge' (微软) / 'gtts' (谷歌) / 'local' (本地)
- 优先级: `edge > gtts > local` (失败自动降级)

### 代理设置

- `PROXY = None` # 例如: '[http://127.0.0.1:7890](http://127.0.0.1:7890/)' 或 'socks5://127.0.0.1:1080'

### 本地TTS配置

- `LOCAL_TTS_VOICE = 'zh-CN'` # 本地语音
- `LOCAL_TTS_SPEED = 150` # 语速 (100-200)

------



## 🔄 重试和缓存配置

### 重试配置

- `MAX_RETRIES_PER_FILE = 5` # 每个文件最大重试次数
- `MAX_TOTAL_RETRIES = 3` # 所有文件整体重试次数
- `REQUEST_INTERVAL = 1.0` # 请求间隔（秒），避免频率限制
- `RETRY_DELAY_BASE = 3` # 重试延迟基数（指数退避）

### 缓存配置

- `CACHE_SPEECH = True` # 是否缓存语音
- `CACHE_FOLDER = "speech_cache"` # 缓存文件夹
- `CACHE_EXPIRE_DAYS = 30` # 缓存过期天数

### 失败记录

- `FAILED_LOG = "failed_files.json"`

------



## 🎵 音频质量配置

### 编码质量

- `AUDIO_QUALITY = '-b:a'` # 使用码率方式
- `AUDIO_QUALITY_VALUE = '320k'` # 码率值

### 淡入淡出参数

- `FADE_OUT_DUR = 3.0` # 前奏淡出时长（秒）
- `FADE_IN_DUR = 5.0` # 原曲淡入时长（秒）

------



## 📝 日志配置

- `LOG_ENABLED = True`
- `LOG_FILE = "processing.log"`
- `DEBUG_MODE = False` # 调试模式，显示更多信息

------



## 🏗️ 核心类结构

### `Logger` - 日志管理器

- 功能：记录处理日志到文件
- 方法：
  - `log(message, level)` # 记录日志
  - `info(message)` # INFO级别
  - `warning(message)` # WARNING级别
  - `error(message)` # ERROR级别
  - `debug(message)` # DEBUG级别（仅调试模式）

### `TTSEngine` - TTS引擎管理器

- 功能：支持多种TTS引擎，自动切换和降级
- 核心方法：
  - `generate_speech(text, output_file)` # 生成语音（自动选择引擎）
  - `_generate_edge(text, output_file)` # Edge TTS
  - `_generate_gtts(text, output_file)` # Google TTS
  - `_generate_local(text, output_file)` # 本地TTS
- 缓存机制：MD5哈希缓存语音文件

### `SmartRetryManager` - 智能重试管理器

- 功能：管理失败文件的重试
- 核心方法：
  - `add_failed(file_path)` # 添加失败文件
  - `remove_failed(file_path)` # 移除成功文件
  - `get_failed_files()` # 获取失败文件列表
  - `should_continue()` # 是否继续重试
  - `get_summary()` # 获取处理摘要

------



## 🔧 工具函数

### `get_audio_duration(audio_file)`

- 获取音频文件时长（秒）

### `extract_dance_name(filename)`

- 智能提取舞蹈名称
- 支持舞种：
  - 国标舞：华尔兹、探戈、狐步、快步、伦巴、恰恰、桑巴、牛仔、斗牛
  - 地方舞：三步踩、平四
  - 交谊舞：慢三、慢四、中三、中四、快三、快四、并四、吉特巴、点帕斯、水兵舞、鬼步舞
  - 集体舞：兔子舞、十六步、三十二步
  - 网红舞：汉舞、唐舞、周舞
  - 其他：DJ、慢摇、肚皮舞、街舞、爵士、芭蕾、现代舞、民族舞、古典舞

### `process_one_file(input_file, bgm_file, output_folder, tts_engine, logger)`

- 处理单个文件的核心函数
- 流程：
  1. 识别舞蹈名称
  2. 生成语音（带缓存）
  3. 获取语音时长
  4. 计算语音插入位置
  5. 构建FFmpeg滤镜
  6. 混合音频输出

### `check_ffmpeg()` & `check_dependencies()`

- 检查FFmpeg和Python依赖是否安装

------



## 🎯 主流程 (`main()`)

### 第一轮处理

1. 从 `AUDIO_SOURCE_FOLDER` 读取所有音频文件
2. 过滤BGM文件和已处理文件
3. 逐个处理文件

### 后续重试轮次

1. 从失败日志加载失败文件
2. 仅处理失败文件
3. 直到所有文件成功或达到最大重试次数

### 处理流程

```tex
查找BGM → 初始化TTS引擎 → 读取音频文件 → 
逐个处理 → 生成语音 → 混合音频 → 输出结果
```



------

## 📊 输出和日志

### 输出文件

- 位置：`OUTPUT_SUBFOLDER` 文件夹
- 命名：`原文件名 + OUTPUT_SUFFIX + 原扩展名`
- 失败时自动转为MP3格式

### 日志文件

- `processing.log` - 详细处理日志
- `failed_files.json` - 失败文件记录
- `failed_report_YYYYMMDD_HHMMSS.txt` - 最终失败报告

------



## 💡 错误处理策略

### 网络错误

- 指数退避重试
- 自动降级TTS引擎
- 代理支持

### 文件错误

- 自动重试（最多5次）
- 整体重试（最多3轮）
- 断点续传

### 超时处理

- 语音生成：30秒超时
- FFmpeg处理：60秒超时
- 自动重试

------



## 🚀 运行方式

```bash
python audio_processor.py
```



### 依赖安装

```bash
pip install edge-tts gTTS pyttsx3
# 并确保 FFmpeg 已安装
```



------

## 📝 配置建议

### 网络问题

```python
PROXY = 'http://127.0.0.1:7890'  # 设置代理
TTS_ENGINE = 'gtts'  # 或 'local'
MAX_RETRIES_PER_FILE = 20
REQUEST_INTERVAL = 2.0
```



### 性能优化

```python
CACHE_SPEECH = True  # 启用缓存
BGM_TOTAL_DURATION = 8  # 调整背景音乐长度
AUDIO_QUALITY_VALUE = '192k'  # 降低码率
```



### 调试模式

```python
DEBUG_MODE = True  # 显示更多调试信息
```