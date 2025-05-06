$CMK_VERSION = "2.4.0p8"
## filename for timestamp
$MK_CONFDIR = $env:MK_CONFDIR

# Configuration file for this agent plugin
$CONFIG_FILE="${MK_CONFDIR}\msoffice.cfg.ps1"
if (test-path -path "${CONFIG_FILE}" ) {
     . "${CONFIG_FILE}"
} else {
    exit
}

if (-not (Get-Module -ListAvailable -Name Microsoft.Graph)) {
    Install-Module -Name Microsoft.Graph -Scope CurrentUser -Force -ErrorAction SilentlyContinue
}

try {
    $SecureClientSecret = ConvertTo-SecureString -String $ClientSecret -AsPlainText -Force
    $ClientSecretCredential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $ClientId, $SecureClientSecret
    Connect-MgGraph -TenantId $TenantId -ClientSecretCredential $ClientSecretCredential -NoWelcome
} catch {
    Write-Host "Failed to connect to Microsoft Graph: $_"
    exit
}

try {
    $licenses = Get-MgSubscribedSku
} catch {
    Write-Host "Failed to fetch licenses: $_"
    exit
}

Write-Host "<<<msoffice_licenses>>>"
foreach ($license in $licenses) {
    $line = "mggraph:{0} {1} {2} {3}" -f $license.SkuPartNumber, $license.PrepaidUnits.Enabled, $license.PrepaidUnits.Warning, $license.ConsumedUnits
    Write-Host $line
}

Write-Host "<<<msoffice_serviceplans>>>"
foreach ($license in $licenses) {
    foreach ($serviceplan in $license.ServicePlans) {
        $line = "mggraph:{0} {1} {2}" -f $license.SkuPartNumber, $serviceplan.ServicePlanName, $serviceplan.ProvisioningStatus
        Write-Host $line
    }
}

Disconnect-MgGraph | Out-Null
