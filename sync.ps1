$ErrorActionPreference = "Stop"
Write-Host "正在检查 Open WebUI (8080端口) 状态..." -ForegroundColor Cyan
$isRunning = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", 8080)
    $isRunning = $true
    $tcp.Close()
} catch {}

if (-not $isRunning) {
    Write-Host "`n[错误] Open WebUI 未启动！" -ForegroundColor Red
    Write-Host "请先双击 '双击启动AI助手.bat'，等后台启动完毕后再运行本脚本。" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit
}

Write-Host "服务已运行，开始扫描并同步文件..." -ForegroundColor Green
Write-Host "----------------------------------------"
$oikb = "G:\工作台\10-doc-tools\inkdoc-src\.venv\Scripts\oikb.exe"
$dir = "G:\工作台\_processed"
$url = "http://127.0.0.1:8080"
$token = "sk-e5c5eee1eb55429baba3498f5490cca4"
$kbid = "85139fc7-3b2f-4216-bc14-9aadb34e9d94"

& $oikb sync $dir --url $url --token $token --kb-id $kbid
Write-Host "----------------------------------------"
Write-Host "同步完成！" -ForegroundColor Green
Read-Host "按回车键退出"