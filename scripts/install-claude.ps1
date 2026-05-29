param(
    [string]$RepoUrl = $env:CHIBI_REPO_URL,
    [string]$Marketplace = $env:CHIBI_MARKETPLACE,
    [string]$McpName = $env:CHIBI_MCP_NAME
)

$ErrorActionPreference = "Stop"

if (-not $RepoUrl) {
    $RepoUrl = "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
}
if (-not $Marketplace) {
    $Marketplace = "soccz/chibi-mcp"
}
if (-not $McpName) {
    $McpName = "chibi"
}

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "missing required command: $Name"
    }
}

function Get-UserBase {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($python) {
        $value = (& py -3 -m site --user-base 2>$null)
        if ($LASTEXITCODE -eq 0 -and $value) {
            return $value.Trim()
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $value = (& python -m site --user-base 2>$null)
        if ($LASTEXITCODE -eq 0 -and $value) {
            return $value.Trim()
        }
    }

    return $null
}

function Find-ChibiCommand {
    $cmd = Get-Command chibi-mcp -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $pipxBin = (& pipx environment --value PIPX_BIN_DIR 2>$null)
    if ($LASTEXITCODE -ne 0) {
        $pipxBin = $null
    }
    $userBase = Get-UserBase

    $candidates = @()
    if ($pipxBin) {
        $candidates += (Join-Path $pipxBin.Trim() "chibi-mcp.exe")
        $candidates += (Join-Path $pipxBin.Trim() "chibi-mcp")
    }
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE ".local\bin\chibi-mcp.exe")
    }
    if ($userBase) {
        $candidates += (Join-Path $userBase "Scripts\chibi-mcp.exe")
        $candidates += (Join-Path $userBase "bin/chibi-mcp")
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    throw "chibi-mcp was installed, but the executable was not found on PATH. Run: pipx ensurepath"
}

Require-Command pipx
Require-Command claude

$installed = (& pipx list --short 2>$null) -match '^chibi-mcp(\s|$)'
if ($installed) {
    & pipx upgrade chibi-mcp
    if ($LASTEXITCODE -ne 0) {
        & pipx reinstall chibi-mcp
    }
} else {
    & pipx install $RepoUrl
}
if ($LASTEXITCODE -ne 0) {
    throw "pipx install/upgrade failed"
}

$chibiCmd = Find-ChibiCommand
& $chibiCmd --check
if ($LASTEXITCODE -ne 0) {
    throw "chibi-mcp --check failed"
}

& claude mcp get $McpName *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Claude MCP '$McpName' already exists."
} else {
    & claude mcp add $McpName -- $chibiCmd
    if ($LASTEXITCODE -ne 0) {
        throw "claude mcp add failed"
    }
}

& claude plugin marketplace add $Marketplace
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Claude plugin marketplace add failed; MCP registration is still complete."
}

& claude plugin install "chibi@chibi-mcp"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Claude plugin install failed; MCP registration is still complete."
}

Write-Host "Claude install complete. Try: /chibi"
