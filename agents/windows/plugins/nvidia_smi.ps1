$CMK_VERSION = "2.4.0p21"

Write-Host "<<<nvidia_smi:sep(9)>>>"

$MK_CONFDIR = $env:MK_CONFDIR
if (!$MK_CONFDIR) {
    $MK_CONFDIR = "%PROGRAMDATA%\checkmk\agent\config"
}
$CONFIG_FILE = "${MK_CONFDIR}\nvidia_smi_cfg.ps1"
$DEFAULT_NVIDIA_SMI_PATH = "C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"

if (Test-Path -Path $CONFIG_FILE ) {
    . $CONFIG_FILE
}

if (Test-Path -Path $nvidia_smi_path) {
    & $nvidia_smi_path -q -x
    exit
}

if (Test-Path -Path $DEFAULT_NVIDIA_SMI_PATH) {
    & $DEFAULT_NVIDIA_SMI_PATH -q -x
    exit
}

if (Get-Command "nvidia-smi.exe" -ErrorAction SilentlyContinue) {
    nvidia-smi.exe -q -x
    exit
}

Write-Host "ERROR: nvidia-smi.exe was not found in: "
"- $nvidia_smi_path (configured path)"
"- $DEFAULT_NVIDIA_SMI_PATH (default path)"
"- system PATH"
