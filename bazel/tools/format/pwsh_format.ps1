[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)][string]$PssaPsd1,
    [string]$Settings,
    [switch]$Check,
    [Parameter(ValueFromRemainingArguments)][string[]]$Files
)

# Load PSScriptAnalyzer (which provides Invoke-Formatter) by explicit manifest path
# -- PSModulePath directory-level approach fails in Bazel sandbox.
Import-Module $PssaPsd1 -ErrorAction Stop

$exitCode = 0
foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        Write-Host "Skipping non-existent: $file"
        continue
    }
    $content = Get-Content -Raw -Path $file
    if ([string]::IsNullOrEmpty($content)) { continue }

    $invokeArgs = @{ ScriptDefinition = $content }
    if ($Settings -and (Test-Path $Settings)) {
        $invokeArgs['Settings'] = $Settings
    }
    try {
        $formatted = Invoke-Formatter @invokeArgs -ErrorAction Stop
    }
    catch {
        Write-Host "Failed to format ${file}: $($_.Exception.Message)"
        $exitCode = 1
        continue
    }

    if ($formatted -ne $content) {
        if ($Check) {
            Write-Host "Needs formatting: $file"
            $exitCode = 1
        }
        else {
            Set-Content -NoNewline -Path $file -Value $formatted
        }
    }
}
exit $exitCode
