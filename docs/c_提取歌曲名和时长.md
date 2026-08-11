## 在B_output_mp3文件夹地址栏复制以下代码回车直接运行

```
powershell -command "$folder=(Get-Location).Path; $shell=New-Object -ComObject Shell.Application; $f=$shell.Namespace($folder); $i=0; while(($prop=$f.GetDetailsOf($null,$i)) -ne '时长' -and $prop -ne 'Length'){$i++}; Get-ChildItem -File | ForEach-Object{$file=$f.ParseName($_.Name); [PSCustomObject]@{歌曲名=$_.Name; 时长=$f.GetDetailsOf($file,$i)}} | Export-Csv -Path '.\歌曲列表.csv' -NoTypeInformation -Encoding UTF8; Write-Host '完成！文件已保存在当前文件夹：歌曲列表.csv' -ForegroundColor Green"
```



**运行后，该文件夹内会生成一个歌曲列表.csv，里面A列是歌曲名字，B列是歌曲时长。**

