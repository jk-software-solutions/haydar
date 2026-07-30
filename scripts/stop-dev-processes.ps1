$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ProcessNames = @('dart', 'flutter', 'java', 'node', 'python', 'python3', 'uvicorn')

$Targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine.Contains($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
    $ProcessNames -contains [System.IO.Path]::GetFileNameWithoutExtension($_.Name).ToLowerInvariant()
}

foreach ($Target in $Targets) {
    Write-Host "Stopping Haydar process $($Target.Name) [$($Target.ProcessId)]"
    Stop-Process -Id $Target.ProcessId -Force
}

if (-not $Targets) {
    Write-Host 'No Haydar development processes are running.'
}
