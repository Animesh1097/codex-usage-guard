param(
    [switch]$PurgeData
)

$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $HOME ".codex-usage-guard"
$DataRoot = Join-Path $HOME ".codex-usage-guard-data"
$SkillTarget = Join-Path $HOME ".agents\skills\usage-guard"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$Prompt = Join-Path $CodexHome "prompts\harness.md"
$BinRoot = Join-Path $HOME ".codex-usage-guard-bin"
$Agents = @("guard_fast.toml", "guard_worker.toml", "guard_reasoner.toml", "guard_reviewer.toml")

if (Test-Path $SkillTarget) { Remove-Item -Recurse -Force $SkillTarget }
if (Test-Path $Prompt) { Remove-Item -Force $Prompt }
foreach ($agent in $Agents) {
    $path = Join-Path $CodexHome "agents\$agent"
    if (Test-Path $path) { Remove-Item -Force $path }
}
if (Test-Path $InstallRoot) { Remove-Item -Recurse -Force $InstallRoot }
if (Test-Path $BinRoot) { Remove-Item -Recurse -Force $BinRoot }

function Remove-PathEntry([string]$PathValue, [string]$Entry) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return $PathValue }
    $needle = $Entry.TrimEnd('\')
    return (($PathValue -split ';' | Where-Object {
        $_.Trim() -and $_.Trim().TrimEnd('\') -ine $needle
    }) -join ';')
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$NewUserPath = Remove-PathEntry $UserPath $BinRoot
if ($NewUserPath -ne $UserPath) {
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
}
$env:Path = Remove-PathEntry $env:Path $BinRoot

if ($PurgeData -and (Test-Path $DataRoot)) { Remove-Item -Recurse -Force $DataRoot }

Write-Host "Codex Usage Guard removed." -ForegroundColor Green
if (-not $PurgeData -and (Test-Path $DataRoot)) {
    Write-Host "Task state and telemetry were preserved at $DataRoot. Re-run with -PurgeData to delete them."
}
