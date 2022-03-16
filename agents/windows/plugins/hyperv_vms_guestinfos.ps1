$CMK_VERSION = "2.1.0b3"
####
## Hyper-V VM state
####
## Script must executed with local administrator credentials!
##
## This script gathers a few information about VM integration services,
## checkpoints and replication. All other information about the system
## health are gathered by the operating system agents on both, host and
## guest servers
##
## Version: 1.0
##
## Date: 2015-08-01
##
## Author: A. Exner, ACP

## Script parameters:

$OutputFile = "c:\scripts\VM-State.txt" # Path and filename for file output
$WriteFileOutput = $false


# DO NOT CHANGE ANYTHING BELOW THIS LINE!
#-------------------------------------------------------------------------------

function Script-Output
{
    param([Parameter(Mandatory = $true)][string]$String,[Parameter(Mandatory = $true)][string]$File,[Parameter(Mandatory = $false)][bool]$FileOut=$false,[Parameter(Mandatory = $false)][bool]$Append=$true)

    Write-Host $String

    If($FileOut)
    {
        If($Append)
        {
            Out-File -FilePath $File -Encoding unicode -Append -InputObject $OutputString
        }
        Else
        {
            Out-File -FilePath $OutputFile -Encoding unicode -Force -InputObject $OutputString
        }
    }
}

# Open / overwrite file output

If($WriteFileOutput)
{
    $OutputString = Get-Date -Format yyyy-MM-dd_hh-mm-ss
    Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $false
}

# Get VM's from host and collect informations

$VMList = Get-VM
$now = Get-Date

Foreach ($VM in $VMList)
{
    $OutputString = "<<<<" + $VM.name + ">>>>"
    Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
    $OutputString = "<<<hyperv_vmstatus>>>"
    Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true

    # Integration Services

    $VMI = Get-VMIntegrationService -VMName $VM.name
    $VMIStat = $VMI | where {$_.OperationalStatus -match "ProtocolMismatch"}

    If($VMIStat.Count -gt 0)
    {
        $OutputString = "Integration_Services Protocol_Mismatch"
        Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
    }
    Else
    {
        $OutputString = "Integration_Services Ok"
        Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
    }


    #Replica

    $OutputString = "Replica_Health None"
    Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true

    #Checkpoints

    $VMCP = Get-VMSnapshot -VMName $VM.name

    $OutputString = "<<<hyperv_checkpoints>>>"
    Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true

    If ($VMCP)
    {
        Foreach($CP in $VMCP)
        {
            $OutputString = [string]$CP.Id + " " + [string][System.Math]::Round((($now - $CP.CreationTime).TotalSeconds), 0)
            Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
        }
    }
    Else
    {
        $OutputString = "No_Checkpoints"
        Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
    }
}

$OutputString = "<<<<>>>>"
Script-Output -String $OutputString -File $OutputFile -FileOut $WriteFileOutput -Append $true
