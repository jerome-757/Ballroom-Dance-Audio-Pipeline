# 批量音频转换工具



## 概述

这是一个使用 Python 和 FFmpeg 实现的批量音频格式转换工具，主要功能是将各种音频格式转换为 MP3。



## 依赖项

- Python 3.x
- FFmpeg（外部工具）
- 标准库：os, subprocess, shutil, pathlib, concurrent.futures, threading



## 核心功能
- **批量转换**：将多种音频格式转换为 MP3
- **智能处理**：MP3 文件直接复制，其他格式转换
- **多线程**：支持并发处理，提高转换效率
- **目录结构保持**：保持源文件夹的目录结构
- **跳过机制**：目标文件已存在则跳过



## 配置参数

### 路径配置
- `INPUT_FOLDER`: 输入文件夹路径（自动获取脚本所在目录下的"A_已整理音乐"）
- `OUTPUT_FOLDER`: 输出文件夹（默认为"B_output_mp3"）
- `FFMPEG_PATH`: FFmpeg 可执行文件路径

### 音频参数
- `BITRATE`: 比特率设置（320k/256k/192k/128k）
- `USE_VBR`: 是否使用 VBR（变比特率）
- `VBR_QUALITY`: VBR 质量等级（0-9，0为最高）

### 并发控制
- `MAX_WORKERS`: 同时转换的文件数（默认2）



## 支持的格式

支持超过 30 种音频/视频格式，包括：
- 无损格式：WAV, FLAC, APE, TTA, WavPack
- 压缩格式：M4A, AAC, OGG, OPUS
- 视频格式：MP4, AVI, MKV, MOV（提取音频）
- 其他：WMA, AC3, DTS, AMR, MP2 等



## 数据结构

### 全局统计信息
```python
stats = {
    'total': 0,      # 总文件数
    'converted': 0,   # 已转换
    'copied': 0,     # 已复制(MP3)
    'failed': 0,     # 失败
    'skipped': 0     # 已跳过
}
```



## 核心函数

### `process_file(file_path, input_folder, output_folder, ffmpeg_params)`

处理单个文件的转换逻辑：

1. 计算相对路径和输出路径
2. MP3 文件直接复制
3. 其他支持格式调用 FFmpeg 转换
4. 不支持格式跳过

### `get_ffmpeg_params()`

构建 FFmpeg 参数：

- VBR 模式：`-b:a BITRATE -q:a VBR_QUALITY`
- 固定模式：`-b:a BITRATE`

### `setup_output_folder()`

设置并创建输出文件夹



## 技术实现

### 多线程处理

使用 `ThreadPoolExecutor` 实现并发转换，通过 `as_completed` 等待所有任务完成。

### 线程安全

使用 `threading.Lock()` 保护共享的统计数据。

### FFmpeg 命令构建



```python
cmd = [
    FFMPEG_PATH,
    '-i', file_path,          # 输入文件
    '-vn',                    # 不处理视频流
    '-acodec', 'libmp3lame',  # MP3编码器
    *ffmpeg_params,           # 比特率参数
    '-y',                     # 覆盖输出
    mp3_output                # 输出文件
]
```



### 错误处理

- FFmpeg 执行错误捕获
- 文件操作异常处理
- 详细的错误信息输出



## 执行流程

1. **初始化检查**
   - 验证输入文件夹存在
   - 检查 FFmpeg 可用性
   - 创建输出文件夹
2. **文件扫描**
   - 遍历输入文件夹
   - 收集支持的音频文件
   - 跳过 output 文件夹
3. **多线程处理**
   - 提交所有转换任务
   - 实时显示处理进度
   - 记录统计信息
4. **结果汇总**
   - 显示转换统计
   - 输出处理结果



## 交互反馈

- 实时显示每个文件的处理状态
- 区分不同操作类型：复制、转换、跳过、失败
- 使用 Emoji 图标增强可读性
- 最终显示完整统计报告



