[CmdletBinding()]
param(
    [string]$Destination = "build_source",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destinationPath = if ([IO.Path]::IsPathRooted($Destination)) {
    [IO.Path]::GetFullPath($Destination)
} else {
    [IO.Path]::GetFullPath((Join-Path $repositoryRoot $Destination))
}
$repositoryPrefix = $repositoryRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

if ($destinationPath -eq $repositoryRoot -or -not $destinationPath.StartsWith($repositoryPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination must be a directory inside the repository: $destinationPath"
}
if ([IO.Path]::GetFileName($destinationPath) -eq ".git") {
    throw "The .git directory cannot be used as the rebuild destination."
}
if ((Test-Path -LiteralPath $destinationPath) -and -not $Force) {
    throw "Destination already exists. Use -Force to replace it safely: $destinationPath"
}

$destinationParent = Split-Path -Parent $destinationPath
$destinationName = Split-Path -Leaf $destinationPath
$runId = [Guid]::NewGuid().ToString("N")
$stagingPath = Join-Path $destinationParent ".$destinationName.rebuild.$runId"
$archivePath = Join-Path $stagingPath ".rebuild_archives"
$backupPath = Join-Path $destinationParent ".$destinationName.backup.$runId"
$published = $false

function Invoke-Checked {
    param(
        [Parameter(Mandatory)] [string]$FilePath,
        [Parameter(ValueFromRemainingArguments)] [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Expand-ChunkedZip {
    param(
        [Parameter(Mandatory)] [string]$Pattern,
        [Parameter(Mandatory)] [int]$ExpectedCount,
        [Parameter(Mandatory)] [string]$ArchiveName,
        [Parameter(Mandatory)] [string]$ExpectedHash
    )

    $parts = @(Get-ChildItem -Path (Join-Path $repositoryRoot $Pattern) | Sort-Object Name)
    if ($parts.Count -ne $ExpectedCount) {
        throw "Unexpected chunk count for ${Pattern}: $($parts.Count), expected $ExpectedCount"
    }

    $base64 = ($parts | ForEach-Object { (Get-Content -LiteralPath $_.FullName -Raw).Trim() }) -join ""
    try {
        $bytes = [Convert]::FromBase64String($base64)
    } catch {
        throw "Invalid Base64 data in ${Pattern}: $($_.Exception.Message)"
    }

    $output = Join-Path $archivePath $ArchiveName
    [IO.File]::WriteAllBytes($output, $bytes)
    $actualHash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $ExpectedHash) {
        throw "Hash mismatch for ${Pattern}: $actualHash, expected $ExpectedHash"
    }

    Invoke-Checked tar -xf $output -C $stagingPath
    Write-Host "Verified and applied $ArchiveName ($actualHash)"
}

function Copy-VersionOverlay {
    param([Parameter(Mandatory)] [string]$Version)

    $overlay = Join-Path $repositoryRoot "patches/v$Version/overlay"
    foreach ($directory in @("app", "tests")) {
        $source = Join-Path $overlay $directory
        if (Test-Path -LiteralPath $source) {
            Copy-Item -Path (Join-Path $source "*") -Destination (Join-Path $stagingPath $directory) -Recurse -Force
        }
    }

    $scriptName = "apply_v$($Version.Replace('.', '')).py"
    Invoke-Checked python (Join-Path $repositoryRoot "patches/v$Version/$scriptName") $stagingPath
}

try {
    New-Item -ItemType Directory -Path $stagingPath -Force | Out-Null
    New-Item -ItemType Directory -Path $archivePath -Force | Out-Null

    Expand-ChunkedZip "source/v0.6/chunks/part*.txt" 7 "CirosPaint_0.6.zip" "6e49c42e7d3ccfcf219ea24f164a8c436c7875eb56084318242dcb3171337b94"
    Expand-ChunkedZip "patches/v0.7/chunks/part*.txt" 5 "CirosPaint_0.7.zip" "aa0d1fc99b0770425081f0e18cbb399440cab77768ea36887d33038947721620"
    Expand-ChunkedZip "patches/v0.8/chunks/part*.txt" 4 "CirosPaint_0.8.zip" "b30570d26f44aa0e5bf2727910396628e4ab8fc646ddacd49527991cde8d3b90"
    Expand-ChunkedZip "patches/v0.8-artfix/chunks/part*.txt" 1 "CirosPaint_0.8_artfix.zip" "3947092144570548e962b354ec0b7d6fa7b1f6416a2e0fbafa656b450945cbad"
    Expand-ChunkedZip "patches/v0.8.1/chunks/part*.txt" 9 "CirosPaint_0.8.1.zip" "ed47500df62010bb9d9f5fb26d09b1174a84787eb80d50c3251db3d433d7ce02"

    $normalizedPatch = Join-Path $archivePath "CirosPaint_0.8.2.patch"
    $patchText = [IO.File]::ReadAllText((Join-Path $repositoryRoot "patches/v0.8.2/CirosPaint_0.8.2.patch"), [Text.Encoding]::UTF8)
    $patchText = $patchText.Replace("`r`n", "`n").Replace("`r", "`n")
    [IO.File]::WriteAllText($normalizedPatch, $patchText, [Text.UTF8Encoding]::new($false))
    Push-Location $destinationParent
    try {
        Invoke-Checked git apply "--directory=$(Split-Path -Leaf $stagingPath)" $normalizedPatch
    } finally {
        Pop-Location
    }

    Expand-ChunkedZip "patches/v0.8.3/chunks/part*.txt" 12 "CirosPaint_0.8.3_overlay.zip" "185e2b09264544498de8da2d73e5f2c148b0a57b3fec6437bd7c22676b5b7dd9"
    Push-Location $stagingPath
    try {
        Invoke-Checked python "tools/apply_v083_metadata.py"
    } finally {
        Pop-Location
    }

    $dashboardPath = Join-Path $stagingPath "app/ui/pages/dashboard_page.py"
    $dashboard = [IO.File]::ReadAllText($dashboardPath, [Text.Encoding]::UTF8)
    $dashboard = $dashboard.Replace("Ciros Paint 0.8.3.3", "Ciros Paint 0.8.3.1")
    [IO.File]::WriteAllText($dashboardPath, $dashboard, [Text.UTF8Encoding]::new($false))

    Expand-ChunkedZip "patches/v0.9.0/code_overlay/part*.txt" 5 "CirosPaint_0.9.0_code_overlay.zip" "7dd1878ef496db816313474e55312da775cd505a4da571c68c6a5767d62272f3"

    foreach ($version in @("0.9.1", "0.9.2", "0.9.3", "0.9.4", "0.9.4.1")) {
        Copy-VersionOverlay $version
    }

    $configPath = Join-Path $stagingPath "app/core/config.py"
    $config = [IO.File]::ReadAllText($configPath, [Text.Encoding]::UTF8)
    if (-not $config.Contains('APP_VERSION = "0.9.4.1"')) {
        throw "Expected Ciros Paint 0.9.4.1 version marker was not found"
    }
    $config = $config.Replace('APP_VERSION = "0.9.4.1"', 'APP_VERSION = "0.9"')
    [IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($false))

    foreach ($version in @("0.10.1", "0.10.2", "0.10.3", "0.10.4", "0.10.5", "0.10.6")) {
        Copy-VersionOverlay $version
    }

    Expand-ChunkedZip "patches/v0.10.7/chunks/part*.txt" 9 "CirosPaint_0.10.7_overlay.zip" "062ae2b06e881f1d243b3ae7a4cbe150d889b46fb938f98735bd45c2def89f1b"
    Invoke-Checked python (Join-Path $repositoryRoot "patches/v0.10.7/apply_v0107.py") $stagingPath

    Expand-ChunkedZip "patches/v0.10.8/chunks/part*.txt" 6 "CirosPaint_0.10.8_overlay.zip" "d85dc1f7c9b168890f9f03d4f5973979fbafe73ff2712fbf7428d628ce09e860"
    Invoke-Checked python (Join-Path $repositoryRoot "patches/v0.10.8/apply_v0108.py") $stagingPath

    Remove-Item -LiteralPath $archivePath -Recurse -Force

    $checks = @{
        "app/core/config.py" = 'APP_VERSION = "0.10.8"'
        "requirements.txt" = "google-genai>=2.3,<3"
        "app/services/assistant_entity_resolver.py" = "LocalEntityResolver"
        "app/services/assistant_workflow_service.py" = "AssistantWorkflowEngine"
        "app/services/assistant_gemini_service.py" = "resolve_paint_name"
        "app/services/assistant_local_service.py" = "Cambiar otra miniatura"
        "app/ui/pages/assistant_page.py" = "owned_only=True"
        "app/ui/pages/settings_page.py" = "Requests Gemini del"
    }
    foreach ($entry in $checks.GetEnumerator()) {
        $path = Join-Path $stagingPath $entry.Key
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required reconstructed file is missing: $($entry.Key)"
        }
        $text = [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
        if (-not $text.Contains($entry.Value)) {
            throw "Verification marker missing in $($entry.Key): $($entry.Value)"
        }
    }
    Write-Host "Ciros Paint 0.10.8 source reconstruction verified"

    if (Test-Path -LiteralPath $destinationPath) {
        Move-Item -LiteralPath $destinationPath -Destination $backupPath
    }
    try {
        Move-Item -LiteralPath $stagingPath -Destination $destinationPath
        $published = $true
    } catch {
        if ((Test-Path -LiteralPath $backupPath) -and -not (Test-Path -LiteralPath $destinationPath)) {
            Move-Item -LiteralPath $backupPath -Destination $destinationPath
        }
        throw
    }
    if (Test-Path -LiteralPath $backupPath) {
        Remove-Item -LiteralPath $backupPath -Recurse -Force
    }

    Write-Host "Rebuilt Ciros Paint 0.10.8 source at $destinationPath"
} finally {
    if (-not $published -and (Test-Path -LiteralPath $stagingPath)) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    if (Test-Path -LiteralPath $backupPath) {
        if (-not (Test-Path -LiteralPath $destinationPath)) {
            Move-Item -LiteralPath $backupPath -Destination $destinationPath
        } else {
            Remove-Item -LiteralPath $backupPath -Recurse -Force
        }
    }
}
