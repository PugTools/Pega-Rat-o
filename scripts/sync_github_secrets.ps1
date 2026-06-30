param(
    [string]$Repo = "PugTools/Pega-Rat-o",
    [string]$EnvFile = ".env",
    [ValidateSet("codespaces", "actions", "both")]
    [string]$App = "codespaces"
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
    "APP_ENV",
    "AUTH_COOKIE_NAME",
    "AUTH_COOKIE_SECURE",
    "AUTH_COOKIE_SAMESITE",
    "AUTH_COOKIE_DOMAIN",
    "JWT_SECRET_KEY",
    "SYSTEM_ADMIN_EMAILS",
    "ADMIN_BOOTSTRAP_EMAIL",
    "ADMIN_BOOTSTRAP_PASSWORD",
    "ADMIN_BOOTSTRAP_RESET_PASSWORD",
    "CORS_ALLOWED_ORIGINS",
    "CORS_ALLOWED_ORIGIN_REGEX",
    "CGU_API_KEY",
    "PORTAL_TRANSPARENCIA_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "GOVBR_CLIENT_ID",
    "GOVBR_REDIRECT_URI"
)

function Set-RepoSecret {
    param(
        [string]$Name,
        [string]$Value,
        [string]$TargetApp
    )

    $Value | gh secret set $Name --repo $Repo --app $TargetApp --body-file -
    Write-Host "Secret $Name sincronizado em $TargetApp para $Repo."
}

foreach ($name in $requiredSecrets) {
    if (-not $values.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($values[$name])) {
        Write-Warning "Variavel $name ausente ou vazia em $EnvFile. Pulando."
        continue
    }

    if ($App -eq "both") {
        Set-RepoSecret -Name $name -Value $values[$name] -TargetApp "codespaces"
        Set-RepoSecret -Name $name -Value $values[$name] -TargetApp "actions"
    } else {
        Set-RepoSecret -Name $name -Value $values[$name] -TargetApp $App
    }
}
