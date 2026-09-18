$ErrorActionPreference = "Stop"

$Repo = "https://github.com/Animesh1097/codex-usage-guard.git"
$InstallRoot = Join-Path $HOME ".codex-usage-guard"
$SkillTarget = Join-Path $HOME ".agents\skills\usage-guard"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$AgentTarget = Join-Path $CodexHome "agents"
$PromptTarget = Join-Path $CodexHome "prompts"
$Launcher = Join-Path $InstallRoot "guard.cmd"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found."
    }
}

Require-Command "git"
Require-Command "codex"

$Python = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) { $Python = "python" }
elseif (Get-Command "py" -ErrorAction SilentlyContinue) { $Python = "py" }
else { throw "Python 3.10+ is required." }

if (Test-Path (Join-Path $InstallRoot ".git")) {
    git -C $InstallRoot pull --ff-only
} elseif (Test-Path $InstallRoot) {
    throw "$InstallRoot exists but is not a git clone. Move or remove it first."
} else {
    git clone --depth 1 $Repo $InstallRoot
}

New-Item -ItemType Directory -Force -Path (Split-Path $SkillTarget) | Out-Null
New-Item -ItemType Directory -Force -Path $AgentTarget | Out-Null
New-Item -ItemType Directory -Force -Path $PromptTarget | Out-Null

if (Test-Path $SkillTarget) { Remove-Item -Recurse -Force $SkillTarget }
Copy-Item -Recurse -Force (Join-Path $InstallRoot ".agents\skills\usage-guard") $SkillTarget
Copy-Item -Force (Join-Path $InstallRoot ".codex\agents\guard_*.toml") $AgentTarget
Copy-Item -Force (Join-Path $InstallRoot "prompts\harness.md") (Join-Path $PromptTarget "harness.md")

if ($Python -eq "py") {
    $LauncherBody = "@echo off`r`npy -3 `"%~dp0scripts\guard_cli.py`" %*`r`n"
} else {
    $LauncherBody = "@echo off`r`npython `"%~dp0scripts\guard_cli.py`" %*`r`n"
}
Set-Content -Path $Launcher -Value $LauncherBody -Encoding Ascii -NoNewline

Write-Host "Running local doctor..." -ForegroundColor Cyan
& $Launcher doctor
if ($LASTEXITCODE -ne 0) { throw "Usage Guard doctor failed." }

Write-Host ""
Write-Host "Codex Usage Guard installed." -ForegroundColor Green
Write-Host "Restart Codex, then use the usage-guard skill: `$usage-guard <task>"
Write-Host "On Codex CLI versions that support custom prompts, you can also use: /prompts:harness <task>"
Write-Host "No API key or Ollama is required. It uses your existing Codex sign-in."
