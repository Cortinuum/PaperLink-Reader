$ErrorActionPreference = 'Stop'
$uvVersion = '0.12.23'
$uvHash = '75d05de6762778c31ee183398de7dd15093fad0ed90b1f236d8205ea5ec00c90'
$toolDir = Join-Path $PSScriptRoot '.runtime\tools'
$uvPath = Join-Path $toolDir 'uv.exe'
New-Item -ItemType Directory -Force $toolDir | Out-Null
if (-not (Test-Path -LiteralPath $uvPath)) {
    $uvArchive = Join-Path $toolDir 'uv.zip'
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$uvVersion/uv-x86_64-pc-windows-msvc.zip" -OutFile $uvArchive
    if ((Get-FileHash -LiteralPath $uvArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $uvHash) { throw 'The setup download could not be verified.' }
    Expand-Archive -LiteralPath $uvArchive -DestinationPath $toolDir -Force
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.runtime\python'
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.runtime\cache'
$pythonVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '.python-version') -Raw).Trim()
& $uvPath python install $pythonVersion --no-bin --install-dir $env:UV_PYTHON_INSTALL_DIR
if ($LASTEXITCODE -ne 0) { throw 'Python setup failed.' }
$pythonPath = Get-ChildItem -LiteralPath $env:UV_PYTHON_INSTALL_DIR -Directory | Where-Object Name -Like "cpython-$pythonVersion-windows-x86_64*" | ForEach-Object { Join-Path $_.FullName 'python.exe' } | Select-Object -First 1
if (-not $pythonPath) { throw 'The private Python runtime was not found.' }
& $uvPath venv (Join-Path $PSScriptRoot '.venv') --python $pythonPath --allow-existing
if ($LASTEXITCODE -ne 0) { throw 'Reader environment setup failed.' }
& $uvPath pip sync (Join-Path $PSScriptRoot 'requirements.txt') --python (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')
if ($LASTEXITCODE -ne 0) { throw 'Reader package setup failed.' }
Write-Host 'PaperLink setup complete. Open Start_PaperLink.cmd.'
