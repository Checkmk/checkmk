[CmdletBinding(PositionalBinding=$false)]
param(
    [Parameter(Mandatory)][string]$PssaPsd1,
    [Parameter(Mandatory)][string]$SarifPsd1,
    [Parameter(Mandatory)][string]$OutFile,
    [Parameter(Mandatory)][string]$SarifFile,
    [string]$HumanExitCodeFile,
    [string]$MachineExitCodeFile,
    [string]$Settings,
    [Parameter(ValueFromRemainingArguments)][string[]]$Files
)

# Load modules by explicit manifest path -- PSModulePath directory-level approach
# fails in Bazel sandbox because PowerShell expects parent-of-module-dir entries.
Import-Module $PssaPsd1 -ErrorAction Stop
Import-Module $SarifPsd1 -ErrorAction Stop

$results = @(foreach ($file in $Files) {
    $invokeArgs = @{ Path = $file }
    if ($Settings) { $invokeArgs['Settings'] = $Settings }
    Invoke-ScriptAnalyzer @invokeArgs
})

$results | Format-Table -AutoSize RuleName, Severity, ScriptName, Line, Message |
    Out-String | Out-File -FilePath $OutFile -Encoding utf8

$results | ConvertTo-SARIF -FilePath $SarifFile

$exitCode = if ($results.Count -gt 0) { 1 } else { 0 }

if ($HumanExitCodeFile -or $MachineExitCodeFile) {
    if ($HumanExitCodeFile)   { $exitCode | Out-File -FilePath $HumanExitCodeFile   -Encoding utf8 -NoNewline }
    if ($MachineExitCodeFile) { $exitCode | Out-File -FilePath $MachineExitCodeFile -Encoding utf8 -NoNewline }
    exit 0
} else {
    exit $exitCode
}
