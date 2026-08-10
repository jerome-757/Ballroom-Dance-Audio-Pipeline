## 安装依赖：

需要先安装 edge-tts：

```
pip install edge-tts
```


edge-tts -f "C:\jerome\DANCE\舞曲排序和重命名\prompt.xml" --voice zh-CN-XiaoxiaoNeural --write-media 星发舞厅_温馨提示_女声.mp3(废除)

**注**：xml精确控制到毫秒的生成方式失败（会把SSML 标签当作普通文本读出来）



## CMD终端运行下面命令，要更换文本内容和地址哦。

```cmd
edge-tts --text "温馨提示。。。亲爱的舞友们，你们好。欢迎来到广州星发舞厅。为了保持一个良好的环境和一个清新的空气，也为了您和他人的身体健康，请不要在场内吸烟。要吸烟的朋友请移步到场外吸烟区。。谢谢您的配合，祝您跳舞愉快。。。。。" --voice zh-CN-XiaoxiaoNeural --rate="-10%" --write-media C:\jerome\DANCE\舞曲排序和重命名\广州星发舞厅_温馨提示_女声.mp3
```

```cmd
edge-tts --text "亲爱的舞友们，本场舞曲已全部播放完毕。星发舞厅因您而精彩。感谢您的光临与陪伴。离场时请带好随身物品，回家路上注意安全。需要吸烟的朋友请到场外吸烟区。广州星发舞厅每天都有精彩，欢迎您常来。祝您生活愉快！" --voice zh-CN-XiaoxiaoNeural --rate="-8%" --write-media C:\jerome\DANCE\舞曲排序和重命名\广州星发舞厅_结束语_女声.mp3
```



## 使用说明

<pre>
停顿	             用句号 。 或 。。。
强调某个词	     无法通过 edge-tts 实现（需换其他 TTS 工具）
调整语速	             用 --rate 参数
调整音调	             用 --pitch 参数
</pre>