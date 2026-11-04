$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $repoRoot
$pythonExecutable = Join-Path $repoRoot '.venv\Scripts\python.exe'
$mysqlExecutable = Join-Path $workspaceRoot '.tools\mysql-8.4.11-winx64\bin\mysqld.exe'
$mysqlConfig = Join-Path $workspaceRoot '.tools\my.ini'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Create the Python 3.12 .venv using README.md first.'
}
if ((Test-Path -LiteralPath $mysqlExecutable) -and (Test-Path -LiteralPath $mysqlConfig)) {
    $databaseProcess = Get-Process mysqld -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $mysqlExecutable }
    if (-not $databaseProcess) {
        Start-Process -FilePath $mysqlExecutable -ArgumentList ('--defaults-file="' + $mysqlConfig + '"') -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
}
Push-Location $repoRoot
try {
    & $pythonExecutable manage.py runserver 127.0.0.1:8000
} finally {
    Pop-Location
}
