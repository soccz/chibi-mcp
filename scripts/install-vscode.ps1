param(
    [string]$Repo = $env:CHIBI_GITHUB_REPO
)

$ErrorActionPreference = "Stop"

if (-not $Repo) {
    $Repo = "soccz/chibi-mcp"
}

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    throw "missing required command: code"
}

$apiUrl = "https://api.github.com/repos/$Repo/releases/latest"
$release = Invoke-RestMethod -Uri $apiUrl
$asset = $release.assets | Where-Object { $_.name -like "*.vsix" } | Select-Object -First 1
if (-not $asset) {
    throw "No .vsix asset found in the latest GitHub Release."
}

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("chibi-mcp-" + [System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tmp | Out-Null
$vsix = Join-Path $tmp "chibi-mcp.vsix"

try {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $vsix
    & code --install-extension $vsix --force
    if ($LASTEXITCODE -ne 0) {
        throw "code --install-extension failed"
    }
    Write-Host "VS Code install complete. Open the tteoki activity bar view."
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
