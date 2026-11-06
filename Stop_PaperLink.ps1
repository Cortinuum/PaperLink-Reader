$target = Join-Path $PSScriptRoot 'reader.py'
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($target) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
