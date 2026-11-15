$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $IsWindows -and $env:OS -ne 'Windows_NT') { throw '必须在 Windows x64 构建' }
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw '请安装 Python 3.11 x64 并启用 py launcher' }
$python = Join-Path $PWD '.venv\Scripts\python.exe'
& $python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '测试失败' }
& $python scripts/build.py
if ($LASTEXITCODE -ne 0) { throw '构建失败' }
& $python scripts/smoke_windows.py
if ($LASTEXITCODE -ne 0) { throw 'EXE 冒烟测试失败' }
& $python scripts/package.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
