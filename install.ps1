$ErrorActionPreference = "Stop"

$Repo = "https://github.com/Animesh1097/codex-usage-guard.git"
$InstallRoot = Join-Path $HOME ".codex-usage-guard"
$SkillTarget = Join-Path $HOME ".agents\skills\usage-guard"
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$AgentTarget = Join-Path $CodexHome "agents"
$PromptTarget = Join-Path $CodexHome "prompts"
$Launcher = Join-Path $InstallRoot "guard.cmd"
$BinRoot = Join-Path $HOME ".codex-usage-guard-bin"
$CguardLauncher = Join-Path $BinRoot "cguard.cmd"

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
    $Origin = (git -C $InstallRoot remote get-url origin).Trim()
    if ($Origin -ne $Repo) {
        throw "$InstallRoot exists but points to '$Origin', not the official Codex Usage Guard repository."
    }
    git -C $InstallRoot fetch origin main --quiet
    git -C $InstallRoot checkout main --quiet
    git -C $InstallRoot reset --hard origin/main --quiet
} elseif (Test-Path $InstallRoot) {
    throw "$InstallRoot exists but is not a git clone. Move or remove it first."
} else {
    git clone --depth 1 --branch main $Repo $InstallRoot
}

New-Item -ItemType Directory -Force -Path (Split-Path $SkillTarget) | Out-Null
New-Item -ItemType Directory -Force -Path $AgentTarget | Out-Null
New-Item -ItemType Directory -Force -Path $PromptTarget | Out-Null

if (Test-Path $SkillTarget) { Remove-Item -Recurse -Force $SkillTarget }
Copy-Item -Recurse -Force (Join-Path $InstallRoot ".agents\skills\usage-guard") $SkillTarget
Copy-Item -Force (Join-Path $InstallRoot ".codex\agents\guard_*.toml") $AgentTarget

# Legacy/custom-prompt wrapper is optional. Skills are the supported Codex entry point.
$PromptSource = Join-Path $InstallRoot "prompts\harness.md"
if (Test-Path $PromptSource) {
    Copy-Item -Force $PromptSource (Join-Path $PromptTarget "harness.md")
}

if ($Python -eq "py") {
    $LauncherBody = "@echo off`r`npy -3 `"%~dp0scripts\guard_cli.py`" %*`r`n"
} else {
    $LauncherBody = "@echo off`r`npython `"%~dp0scripts\guard_cli.py`" %*`r`n"
}
Set-Content -Path $Launcher -Value $LauncherBody -Encoding Ascii -NoNewline

# Install a global cguard launcher. It classifies the task locally first, then
# starts Codex with an explicit project root, model, and reasoning effort.
New-Item -ItemType Directory -Force -Path $BinRoot | Out-Null
$CguardBody = "@echo off`r`ncall `"$Launcher`" launch %*`r`n"
Set-Content -Path $CguardLauncher -Value $CguardBody -Encoding Ascii -NoNewline

function Has-PathEntry([string]$PathValue, [string]$Entry) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) { return $false }
    $needle = $Entry.TrimEnd('\')
    foreach ($part in ($PathValue -split ';')) {
        if ($part.Trim().TrimEnd('\') -ieq $needle) { return $true }
    }
    return $false
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (Has-PathEntry $UserPath $BinRoot)) {
    $NewUserPath = if ([string]::IsNullOrWhiteSpace($UserPath)) { $BinRoot } else { "$UserPath;$BinRoot" }
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
}
if (-not (Has-PathEntry $env:Path $BinRoot)) {
    $env:Path = "$env:Path;$BinRoot"
}

Write-Host "Running local doctor..." -ForegroundColor Cyan
& $Launcher doctor
if ($LASTEXITCODE -ne 0) { throw "Usage Guard doctor failed." }

$Version = (& $Launcher version).Trim()
Write-Host ""
Write-Host "Codex Usage Guard $Version installed." -ForegroundColor Green
Write-Host "Recommended after this one-time install: work inside Codex."
Write-Host "  `$usage-guard <task>  # auto-enforces selected model/reasoning when needed"
Write-Host "  `$usage-guard status"
Write-Host "  `$usage-guard usage"
Write-Host "If the open Codex model differs, Usage Guard runs one verified pinned Codex worker automatically."
Write-Host "Optional parent-model pre-routing remains available with cguard."
Write-Host "No API key or Ollama is required. It uses your existing Codex sign-in."
Write-Host "Browser Harness / Browser Use Cloud are optional and not required by the core guard."
