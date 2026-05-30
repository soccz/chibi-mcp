param(
    [string]$RepoUrl = $env:CHIBI_REPO_URL,
    [string]$Marketplace = $env:CHIBI_MARKETPLACE,
    [string]$McpName = $env:CHIBI_MCP_NAME
)

$ErrorActionPreference = "Stop"
$script:PipxCommand = $null
$script:PipxPrefix = @()
$ExpectedVersion = $env:CHIBI_EXPECT_VERSION

if (-not $RepoUrl) {
    $RepoUrl = "git+https://github.com/soccz/chibi-mcp.git#subdirectory=server"
}
if (-not $Marketplace) {
    $Marketplace = "soccz/chibi-mcp"
}
if (-not $McpName) {
    $McpName = "chibi"
}
if (-not $ExpectedVersion) {
    $ExpectedVersion = "1.4.27"
}

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "missing required command: $Name"
    }
}

function Update-SessionPath {
    $currentPath = $env:Path
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $paths = @()
    if ($currentPath) {
        $paths += $currentPath
    }
    if ($machinePath) {
        $paths += $machinePath
    }
    if ($userPath) {
        $paths += $userPath
    }
    if ($paths.Count -gt 0) {
        $env:Path = ($paths -join ";")
    }
}

function Install-PythonWithWinget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        return $false
    }

    Write-Host "Python not found; installing Python with winget"
    & winget install --exact --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    Update-SessionPath
    return $true
}

function Ensure-Pipx {
    $pipx = Get-Command pipx -ErrorAction SilentlyContinue
    if ($pipx) {
        $script:PipxCommand = "pipx"
        $script:PipxPrefix = @()
        return
    }

    if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        [void](Install-PythonWithWinget)
    }

    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        Write-Host "pipx not found; installing pipx with py -m pip"
        & py -m pip install --user pipx
        if ($LASTEXITCODE -ne 0) {
            throw "pipx install failed"
        }
        $script:PipxCommand = "py"
        $script:PipxPrefix = @("-m", "pipx")
        return
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        Write-Host "pipx not found; installing pipx with python -m pip"
        & python -m pip install --user pipx
        if ($LASTEXITCODE -ne 0) {
            throw "pipx install failed"
        }
        $script:PipxCommand = "python"
        $script:PipxPrefix = @("-m", "pipx")
        return
    }

    throw "missing required command: pipx, py, or python"
}

function Invoke-Pipx {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PipxArgs)
    $allArgs = @()
    $allArgs += $script:PipxPrefix
    $allArgs += $PipxArgs
    & $script:PipxCommand @allArgs
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

    $pipxBin = (Invoke-Pipx environment --value PIPX_BIN_DIR 2>$null)
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

function Install-ServerFromGitHub {
    Invoke-Pipx uninstall chibi-mcp *> $null
    Invoke-Pipx install $RepoUrl
    if ($LASTEXITCODE -ne 0) {
        throw "pipx install failed"
    }
}

function Verify-ChibiVersion {
    param([string]$ChibiCmd)

    $installedVersion = (& $ChibiCmd --version 2>$null)
    if ($LASTEXITCODE -eq 0 -and $installedVersion -eq $ExpectedVersion) {
        return $ChibiCmd
    }

    Write-Warning "Expected chibi-mcp $ExpectedVersion but found $installedVersion; reinstalling fresh."
    Install-ServerFromGitHub
    $ChibiCmd = Find-ChibiCommand
    $installedVersion = (& $ChibiCmd --version 2>$null)
    if ($LASTEXITCODE -ne 0 -or $installedVersion -ne $ExpectedVersion) {
        throw "chibi-mcp version check failed: expected $ExpectedVersion, got $installedVersion"
    }
    return $ChibiCmd
}

Ensure-Pipx
Require-Command codex

Write-Host "Installing chibi-mcp $ExpectedVersion from GitHub..."
Install-ServerFromGitHub
Invoke-Pipx ensurepath *> $null

$chibiCmd = Find-ChibiCommand
$chibiCmd = Verify-ChibiVersion $chibiCmd
$checkOutput = (& $chibiCmd --check)
$checkJson = ($checkOutput -join "`n")
Write-Host $checkJson
if ($LASTEXITCODE -ne 0) {
    throw "chibi-mcp --check failed"
}
try {
    $check = ($checkJson | ConvertFrom-Json)
    if (-not $check.tkinter) {
        Write-Warning "Python tkinter is unavailable. MCP tools work, but the floating pet window cannot open. Install Python with Tcl/Tk support, then run: pipx uninstall chibi-mcp; pipx install `"$RepoUrl`""
    }
} catch {
    Write-Warning "Could not parse chibi-mcp --check output."
}

Write-Host "Refreshing Codex MCP '$McpName' registration..."
& codex mcp remove $McpName *> $null
& codex mcp add $McpName -- $chibiCmd
if ($LASTEXITCODE -ne 0) {
    throw "codex mcp add failed"
}

& codex plugin marketplace add $Marketplace
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Codex plugin marketplace add failed; MCP registration is still complete."
}

Write-Host "Codex install complete. Try: chibi 보여줘"
