param($usbip, $addr, $port)
function Test-Administrator {  
    [OutputType([bool])]
    param()
    process {
        [Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent();
        return $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);
    }
}

if (-not(Test-Path -Path $usbip -PathType Leaf)) {
    Write-Host "$usbip doesn't exist" -ForegroundColor Red
    exit 1
}

if (-not (Test-Administrator)) {
    Write-Host "This script must be executed as Administrator." -ForegroundColor Red
    exit 1
}

&$usbip port
if ($LastExitCode -eq 3) {
    Write-Host "No chance"
    exit 1
}

&$usbip detach -p 00
if ($LastExitCode -eq 0) {
    Write-Host "Should not happen"
}

$sleep = 10
for ($i = 0; $i -lt 3; $i++) {
    Write-Host wait.... 
    &$usbip attach -r $addr -b $port
    if ($? ) {
        Write-Host "success!"
        exit 0
    }
    Write-Host "error $LastExitCode"
    Start-Sleep $sleep
}

exit 1