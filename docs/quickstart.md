# Quick start

## Install

Windows:

```powershell
irm https://raw.githubusercontent.com/Animesh1097/codex-usage-guard/main/install.ps1 | iex
```

Then open Codex in the project you want to work on.

## Run a task

Inside Codex:

```text
$usage-guard fix the mobile checkout overlap and verify the changed flow
```

Normal Usage Guard behavior:

- stays in your current Codex session
- does not automatically change model/reasoning
- inspects the repository
- creates bounded task state
- opens the visual companion when available
- records meaningful phases/actions
- detects verification commands
- uses UI/system/browser guidance only when relevant
- finishes with verification and measured usage data

## Check progress

```text
$usage-guard status
```

The graphical companion is presentation-only. If it is unavailable or crashes, the guard continues and the terminal HUD/status path remains available.

## Advanced routing

Do not use this unless you explicitly want model routing:

```powershell
cguard "your task"
```

## Troubleshooting

Run:

```powershell
& "$HOME\.codex-usage-guard\guard.cmd" doctor
```

The doctor reports whether the current installation is using the compiled Tauri visualizer, the Tkinter fallback, or no desktop visualizer.
