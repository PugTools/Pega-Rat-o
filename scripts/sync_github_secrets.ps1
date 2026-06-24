param(
    [string]$Repo = "PugTools/Pega-Rat-o",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) nao encontrado. Instale em https://cli.github.com/ e rode 'gh auth login'."
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw "Arquivo $EnvFile nao encontrado."
}

$values = @{}
Get-Content -LiteralPath $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
        return
    }

    $parts = $line.Split("=", 2)
    $values[$parts[0]] = $parts[1]
}

$requiredSecrets = @(
    "CGU_API_KEY",
    "PORTAL_TRANSPARENCIA_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET"
)

foreach ($name in $requiredSecrets) {
    if (-not $values.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($values[$name])) {
        throw "Variavel $name ausente ou vazia em $EnvFile."
    }

    $values[$name] | gh secret set $name --repo $Repo --body-file -
    Write-Host "Secret $name sincronizado no repositorio $Repo."
}
