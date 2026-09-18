$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $HOME ".codex-usage-guard"
$DataRoot = Join-Path $HOME ".codex-usage-guard-data"
$SkillTarget = Join-Path $HOME ".agents\skills\usage-guard"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$Prompt = Join-Path $CodexHome "prompts\harness.md"
$Agents = @("guard_fast.toml", "guard_worker.toml", "guard_reasoner.toml", "guard_reviewer.toml")

if (Test-Path $SkillTarget) { Remove-Item -Recurse -Force $SkillTarget }
if (Test-Path $Prompt) { Remove-Item -Force $Prompt }
foreach ($agent in $Agents) {
    $path = Join-Path $CodexHome "agents\$agent"
    if (Test-Path $path) { Remove-Item -Force $path }
}
if (Test-Path $InstallRoot) { Remove-Item -Recurse -Force $InstallRoot }
if (Test-Path $DataRoot) { Remove-Item -Recurse -Force $DataRoot }

Write-Host "Codex Usage Guard removed." -ForegroundColor Green
