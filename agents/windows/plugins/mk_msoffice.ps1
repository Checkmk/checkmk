$CMK_VERSION = "2.1.0p3"
## filename for timestamp
$MK_CONFDIR = $env:MK_CONFDIR

## Source the configuration file for this agent plugin
$CONFIG_FILE="${MK_CONFDIR}\msoffice.cfg.ps1"
if (test-path -path "${CONFIG_FILE}" ) {
     . "${CONFIG_FILE}"
} else {
    exit
}

$secpasswd = ConvertTo-SecureString $password -AsPlainText -Force
$o365credentials = New-Object System.Management.Automation.PSCredential($username, $secpasswd)

Import-Module MSOnline
Connect-MsolService -Credential $o365credentials

write-host "<<<msoffice_licenses>>>"
foreach ($license in Get-MsolAccountSku) {
    $line = "{0} {1} {2} {3}" -f $license.AccountSkuId, $license.ActiveUnits, $license.WarningUnits, $license.ConsumedUnits
    write-host $line
}

write-host "<<<msoffice_serviceplans>>>"
foreach ($license in Get-MsolAccountSku) {
    foreach ($serviceplan in $license.servicestatus) {
        $line = "{0} {1} {2}" -f $license.AccountSkuId, $serviceplan.serviceplan.servicename, $serviceplan.provisioningstatus
        write-host $line
    }
}
