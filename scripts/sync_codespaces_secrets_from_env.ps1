param(
    [string]$Repo = "PugTools/Pega-Rat-o",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

& "$PSScriptRoot\sync_github_secrets.ps1" `
    -Repo $Repo `
    -EnvFile $EnvFile `
    -App codespaces

Write-Host ""
Write-Host "Codespaces Secrets atualizados. No Codespaces, rode:" -ForegroundColor Green
Write-Host "  git pull"
Write-Host "  bash scripts/reset_codespaces_stack.sh app"
