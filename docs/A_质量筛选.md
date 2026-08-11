# 音乐文件整理工具

## 📋 项目概述

这是一个用于自动整理音乐文件的Python工具，能够根据音频文件的元数据（标题、艺术家、唱片集）自动重命名并归类文件。该工具支持多种音频格式，包括MP3、FLAC、M4A等。

**核心功能**：扫描指定文件夹中的所有音频文件，提取元数据，然后按照"歌名-艺术家"的格式重命名并移动到目标文件夹。

##  🎵 支持的音频格式

| 格式 | 扩展名 | 说明                          |
| ---- | ------ | ----------------------------- |
| MP3  | .mp3   | 最流行的音频格式，使用ID3标签 |
| FLAC | .flac  | 无损音频格式                  |
| M4A  | .m4a   | Apple的音频格式               |
| WMA  | .wma   | Windows Media Audio           |
| OGG  | .ogg   | 开源音频格式                  |
| WAV  | .wav   | 未压缩的音频格式              |

## 🔧 代码结构详解

### 1. 元数据提取函数 get_metadata(file_path)

python

```
def get_metadata(file_path):
   """
   提取音乐文件的元数据
   支持 MP3, FLAC, M4A 等格式
   """
```
  
**功能**：从音频文件中提取标题、艺术家、唱片集信息

**处理流程**：
- 1，尝试通用加载：使用mutagen.File()尝试加载文件
- 2，格式判断：根据文件类型使用不同的解析器
- 3，元数据提取：
    - MP3：使用EasyID3读取title、artist、album
    - FLAC：直接从FLAC对象读取标签
    - M4A：读取MP4标签（©nam、©ART、©alb）
    - 兜底方案：如果上述方法失败，再尝试一次EasyID3

**返回值**：
- title：歌曲标题
- artist：艺术家名称
- album：唱片集名称



###  2. 文件处理函数 process_music_files(source_dir, target_dir)

python

```
def process_music_files(source_dir, target_dir):
    """
    处理音乐文件
    :param source_dir: 源文件夹路径
    :param target_dir: 目标文件夹路径
    """
```

**功能**：遍历源文件夹，处理所有音频文件

**主要步骤**：

**步骤1：初始化**
- 创建目标文件夹（如果不存在）
- 定义支持的音频扩展名
- 初始化统计计数器

**步骤2：遍历文件**



python

```
for root, dirs, files in os.walk(source_dir):
      for file in files:
        # 检查是否为音频文件
        if file_ext not in audio_extensions:
            continue
````



**步骤3：元数据验证**

只有同时满足以下三个条件才会被处理：
 - title 不为空
 - artist 不为空
 - album 不为空

**步骤4：文件名清理**

python

```
def clean_filename(text):
    # 替换Windows文件名中的非法字符
    illegal_chars = '<>:"/|?*'
    for char in illegal_chars:
        text = text.replace(char, '')
    return text.strip()
```

清理的非法字符包括：
- <>:"/|?*（Windows文件名不允许的字符）

**步骤5：生成新文件名**
- 格式：{标题}-{艺术家}{扩展名}
- 示例：Yesterday-The Beatles.mp3

**步骤6：处理重名文件**
如果文件名已存在，自动添加数字后缀：
-   Yesterday-The Beatles.mp3 → Yesterday-The Beatles_1.mp3
-   Yesterday-The Beatles_1.mp3 → Yesterday-The Beatles_2.mp3

**步骤7：移动文件**
- 使用shutil.move()将文件从源目录移动到目标目录并重命名。

### 3. 主程序入口

python

```
if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
  
    # 设置文件夹名称
    source_folder_name = "A_待整理音乐"
    target_folder_name = "A_已整理音乐"
```

**目录结构**：

text
- 脚本所在目录/
- ├── A_music_processor.py
- ├── A_待整理音乐/          # 源文件夹（需要手动创建）
- │   ├── 歌曲1.mp3
- │   └── 歌曲2.flac
- └── A_已整理音乐/          # 目标文件夹（自动创建）
    - ├── Yesterday-The Beatles.mp3
    - └── Bohemian Rhapsody-Queen.mp3

##  📊 运行输出示例

text
- 源文件夹: C:MusicA_待整理音乐
- 目标文件夹: C:MusicA_已整理音乐

处理文件: song1.mp3
- ✓ 已移动并重命名为: Yesterday-The Beatles.mp3
  - 标题: Yesterday
  - 艺术家: The Beatles
  - 唱片集: Help!



处理文件: unknown.mp3
- ✗ 跳过文件（缺少元数据）
  - 标题: 缺失
  - 艺术家: 缺失
  - 唱片集: 缺失

<pre>
==================================================
处理完成！
已处理: 45 个文件
已跳过: 12 个文件（缺少元数据）
错误: 0 个文件
==================================================
</pre>

##  ⚠️ 注意事项

###  依赖库安装

bash
```
pip install mutagen
```

###  文件操作说明
 当前版本使用 shutil.move() 移动文件
 如需保留原文件，可将第100行的 move 改为 copy2：

python
```
shutil.copy2(file_path, new_file_path)
```

### 安全提示
- 1,**备份重要数据**：在运行前建议备份音乐文件
- 2,**测试运行**：先用少量文件测试
- 3,**元数据依赖**：程序仅依靠元数据，没有元数据的文件会被跳过



###  适用场景
- 整理下载的散乱音乐文件
- 统一音乐库的命名规范
- 批量处理音乐文件重命名



##  📝 总结

> 这个音乐整理工具是一个实用、高效的自动化脚本，通过读取音频元数据实现智能文件重命名和归类。代码结构清晰，支持多种主流音频格式，具有错误处理机制和详细的运行反馈，适合音乐爱好者和管理大量音频文件的用户使用。

