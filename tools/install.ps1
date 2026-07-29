$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command python -ErrorAction SilentlyContinue

if ($null -ne $Python) {
    & $Python.Source "$ScriptDir/manage.py" install @args
    exit $LASTEXITCODE
}

$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $PyLauncher) {
    throw "未找到 Python。请安装 Python 3 后重试。"
}

& $PyLauncher.Source -3 "$ScriptDir/manage.py" install @args
exit $LASTEXITCODE
