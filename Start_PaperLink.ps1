param([ValidateRange(1024,65515)][int]$Port=8765,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$version='0.8.0'
$runtime=Join-Path $PSScriptRoot '.runtime\python\cpython-3.13.16-windows-x86_64-none'
$python=Join-Path $runtime 'pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup_PaperLink.cmd first, or extract the complete PaperLink ZIP.' }
$identityFile=Join-Path $PSScriptRoot '.runtime\instance-id.txt'
if (-not (Test-Path -LiteralPath $identityFile)) { [guid]::NewGuid().ToString() | Set-Content -LiteralPath $identityFile -Encoding ASCII }
$identity=(Get-Content -LiteralPath $identityFile -Raw).Trim()
$selected=$null;$running=$false
for ($candidate=$Port;$candidate -lt $Port+20;$candidate++) {
    $url="http://127.0.0.1:$candidate";$health=$null
    try { $health=Invoke-RestMethod "$url/api/health" -TimeoutSec 1 } catch {}
    if ($health -and $health.ok -and $health.instance -eq $identity) {
        if ($health.version -ne $version) { throw 'Close this reader with Stop_PaperLink.cmd, then start again.' }
        $selected=$candidate;$running=$true;break
    }
    $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$candidate)
    try { $listener.Start();$selected=$candidate;break } catch {} finally { $listener.Stop() }
}
if ($null -eq $selected) { throw 'No local port is available for PaperLink.' }
$url="http://127.0.0.1:$selected"
if (-not $running) {
    $env:PYTHONPATH=Join-Path $PSScriptRoot '.venv\Lib\site-packages'
    $env:PYTHONNOUSERSITE='1';$env:PYTHONDONTWRITEBYTECODE='1';$env:PAPERLINK_INSTANCE_ID=$identity
    Start-Process -FilePath $python -ArgumentList @('-s',('"'+(Join-Path $PSScriptRoot 'reader.py')+'"'),'--port',"$selected") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    for ($i=0;$i -lt 60;$i++) {
        Start-Sleep -Milliseconds 250
        try { $health=Invoke-RestMethod "$url/api/health" -TimeoutSec 1;if ($health.ok -and $health.instance -eq $identity -and $health.version -eq $version) { $running=$true;break } } catch {}
    }
}
if (-not $running) { throw 'PaperLink could not start. Extract the whole ZIP into a writable folder and retry.' }
if (-not $NoBrowser) { Start-Process $url }
Write-Output $url
