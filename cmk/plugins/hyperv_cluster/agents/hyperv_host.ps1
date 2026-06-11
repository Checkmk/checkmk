# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

function Get-VMGeneralInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  Write-Output "name $($vm.Name)"
  Write-Output "cluster.clustered $($vm.IsClustered)"

  if ($vm.IsClustered) {
    $VMClusterResource = (Get-ClusterResource -VMId $vm.VMId)
    Write-Output "cluster.group $($VMClusterResource.OwnerGroup)"
    Write-Output "cluster.startup_priority $($VMClusterResource.OwnerGroup.Priority)"
  }

  Write-Output "runtime.host $($vm.ComputerName)"
  Write-Output "runtime.powerState $($vm.State)"
  Write-Output "runtime.operationState $($vm.Status)"
  Write-Output "config.vmid $($vm.VMId)"
  Write-Output "config.generation $($vm.Generation)"
  Write-Output "config.version $($vm.Version)"
  Write-Output "config.created $($vm.CreationTime)"

  if ($null -ne $vm.Groups) {
    Write-Output "config.MemberOfVMGroups $($vm.Groups.Count)"
    foreach ($Member in $vm.Groups) {
      Write-Output "$null $($vm.Groups.Name) ($($vm.Groups.InstanceId))"
    }
  }

  Write-Output "guest.fqdn $(Get-VMKVPdata -vm $vm.Name -clusterNode $clusterNode -kvpAttribute 'FullyQualifiedDomainName')"
  Write-Output "guest.os $(Get-VMKVPdata -vm $vm.Name -clusterNode $clusterNode -kvpAttribute 'OSName')"
  Write-Output "guest.IntegrationServicesVersion $(Get-VMKVPdata -vm $vm.Name -clusterNode $clusterNode -kvpAttribute 'IntegrationServicesVersion')"
  Write-Output "guest.IntegrationServicesState $($vm.IntegrationServicesState)"
  Write-Output "config.AutomaticStopAction $($vm.AutomaticStopAction)"
  Write-Output "config.AutomaticStartAction $($vm.AutomaticStartAction)"
  Write-Output "config.AutomaticStartDelay $($vm.AutomaticStartDelay)"
  Write-Output "config.ConfigurationPath $($vm.ConfigurationLocation)"
  Write-Output "config.CheckpointPath $($vm.SnapshotFileLocation)"

  $CheckpointType = $vm.CheckpointType

  if ($null -eq $CheckpointType) {
    $CheckpointType = 'Standard_(legacy)'
  }

  Write-Output "config.CurrentCheckpointType $CheckpointType"

  $VMReplica = Get-VMReplication -ComputerName $clusterNode -VMName $vm.Name -ErrorAction SilentlyContinue

  if ($null -ne $VMReplica) {
    Write-Output "replication.mode $($VMReplica.ReplicationMode)"
    Write-Output "replication.state $($VMReplica.ReplicationState)"
    Write-Output "replication.CurrentServer $($VMReplica.CurrentReplicaServerName)"

    try {
      $ReplicationFreq = ($VMReplica.ReplicationFrequencySec)
    }
    catch {
      $ReplicationFreq = $null
    }

    if ($null -ne $ReplicationFreq) {
      Write-Output "replication.frequency $ReplicationFreq"
    }
  }
  else {
    Write-Output "replication.mode not configured"
  }

  $VMConnect = Get-VMConnectAccess -ComputerName $clusterNode -VMName $vm.Name
  if ($VMConnect.Count -eq 0) {
    $VMConnectUsers = 'nobody'
  }
  else {
    $VMConnectUsers = $VMConnect.Username
  }
  Write-Output "access $VMConnectUsers"

  if ($null -ne (Get-Command Get-VMSecurity -ErrorAction SilentlyContinue)) {
    $VMSec = (Get-VMSecurity -VM $vm)
    Write-Output "security.shieldedVM $($VMSec.Shielded)"
    Write-Output "security.TPMEnabled $($VMSec.TpmEnabled)"
    Write-Output "security.KeyStorageDriveEnabled $($VMSec.KsdEnabled)"
    Write-Output "security.StateMigrationEncrypted $($VMSec.EncryptStateAndVmMigrationTraffic)"
  }
}

############################################################################################################

function Get-vmCheckpoints {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  $Checkpoints = (Get-VMSnapshot -VMName $vm.Name -ComputerName $clusterNode | Sort-Object CreationTime)
  Write-Output "checkpoints $($Checkpoints.Length)"

  if ($Checkpoints.Length -eq 0) {
    Write-Output "checkpoints none"
  }
  else {
    foreach ($Checkpoint in $Checkpoints) {
      Write-Output "checkpoint.name $($Checkpoint.Name)"
      Write-Output "checkpoint.path $($Checkpoint.Path)"
      Write-Output "checkpoint.created $($Checkpoint.CreationTime)"
      Write-Output "checkpoint.parent $($Checkpoint.ParentSnapshotName)"
    }
  }
}

############################################################################################################

function Get-VMCPUInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  Write-Output "config.hardware.numCPU $($vm.ProcessorCount)"
  $vmProcessor = Get-VMProcessor -VMName $vm.Name -ComputerName $clusterNode
  Write-Output "config.hardware.CompatibilityForOlderOS $($vmProcessor.CompatibilityForOlderOperatingSystemsEnabled)"
  Write-Output "config.hardware.CompatibilityForMigration $($vmProcessor.CompatibilityForMigrationEnabled)"

  if ($null -ne $vmProcessor.EnableHostResourceProtection) {
    Write-Output "config.hardware.HostResourceProtection $($vmProcessor.EnableHostResourceProtection)"
  }

  if ($null -ne $vmProcessor.ExposeVirtualizationExtensions) {
    Write-Output "config.hardware.NestedVirtualization $($vmProcessor.ExposeVirtualizationExtensions)"
  }
}

############################################################################################################
function Get-VMRAMInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  $getRAMInfo = Get-VMMemory -VMName $vm.Name -ComputerName $clusterNode
  if ($getRAMInfo.DynamicMemoryEnabled -eq $true) {
    Write-Output "config.hardware.RAMType dynamic"
  }
  else {
    Write-Output "config.hardware.RAMType static"
  }
  Write-Output "config.hardware.StartRAM $($getRAMInfo.Startup)"
  Write-Output "config.hardware.MinRAM $($getRAMInfo.Minimum)"
  Write-Output "config.hardware.MaxRAM $($getRAMInfo.Maximum)"
  Write-Output "config.hardware.AssignedRAM $($vm.MemoryAssigned)"
  Write-Output "config.hardware.RAMDemand $($vm.MemoryDemand)"
}

############################################################################################################
function Get-VMDriveInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  $vmHDDs = (Get-VMHardDiskDrive -VMName $vm.Name -ComputerName $clusterNode | Sort-Object Name)

  Write-Output "vhd $($vmHDDs.Count)"

  foreach ($vmHDD in $vmHDDs) {
    Write-Output "vhd.Name $($vmHDD.Name)"
    Write-Output "vhd.controller.ID $($vmHDD.ID)"
    Write-Output "vhd.controller.Type $($vmHDD.ControllerType)"
    Write-Output "vhd.controller.Number $($vmHDD.ControllerNumber)"
    Write-Output "vhd.controller.Location $($vmHDD.ControllerLocation)"

    $vmHDDVHD = $vmHDD.Path | Get-VHD -ComputerName $clusterNode -ErrorAction SilentlyContinue

    if ($vmHDDVHD -ne $null) {
      # When automatic checkpoints are enabled, the volume
      # of a system may not strictly be the original
      # but instead a snapshot, so we have to go one level up to get the real drive info
      # because these snapshots can be shortlived.
      $ext = (Get-Item($vmHDDVHD.Path)).Extension.ToLower();
      $finalVhd = $vmHDDVHD

      $isSnapshot = {
        $ext = [System.IO.Path]::GetExtension($finalVhd.Path);

        return ($ext -eq ".avhd" -or $ext -eq ".avhdx") -and $finalVhd.VhdType -eq "Differencing";
      }

      while ($isSnapshot.Invoke()) {
        $finalVhd = $finalVhd.ParentPath | Get-VHD -ErrorAction SilentlyContinue

        # Best parent could not be found, so falling back to the original file.
        # This can happen if the parent file becomes unavailable (deleted, on a disconnected drive, etc).
        if ($finalVhd -eq $null) {
          $finalVhd = $vmHDDVHD
          break
        }
      }

      Write-Output "vhd.Path $($finalVhd.Path)"
      Write-Output "vhd.Format $($finalVhd.VhdFormat)"
      Write-Output "vhd.Type $($finalVhd.VhdType)"
      Write-Output "vhd.DiskSize $($finalVhd.Size)"
      Write-Output "vhd.FileSize $($finalVhd.FileSize)"
    }
    else {
      Write-Output "vhd.Path $($vmHDD.Path)"
      Write-Output "vhd.Type Direct"
    }
  }

  # Get vFC, if any
  $vmvSAN = (Get-VMFibreChannelHba -VMName $vm.Name -ComputerName $clusterNode | Sort-Object Name)
  if ($null -ne $vmvSAN) {
    Write-Output "vsan $($vmvSAN.Count)"

    foreach ($vmvSAN in $vmvSAN) {
      Write-Output "vsan.Name $($vmvSAN.SanName)"
      Write-Output "vsan.PrimaryWWNN $($vmvSAN.WorldWideNodeNameSetA)"
      Write-Output "vsan.PrimaryWWPN $($vmvSAN.WorldWidePortNameSetA)"
      Write-Output "vsan.SecondaryWWNN $($vmvSAN.WorldWideNodeNameSetB)"
      Write-Output "vsan.SecondaryWWPN $($vmvSAN.WorldWidePortNameSetB)"
      Write-Output "vsan.ID $($vmvSAN.ID)"
    }
  }
}

############################################################################################################
function Get-VMNICInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  $vmNetCards = (Get-VMNetworkAdapter -VMName $vm.Name -ComputerName $clusterNode | Sort-Object Name, ID)

  Write-Output "nic $($vmNetCards.Count)"

  foreach ($vmNetCard in $vmNetCards) {
    Write-Output "nic.name $($vmNetCard.Name)"
    Write-Output "nic.id $($vmNetCard.ID)"
    Write-Output "nic.connectionstate $($vmNetCard.Connected)"

    #vmNetCard Switch
    if ($vmNetCard.SwitchName.Length -ne 0) {
      Write-Output "nic.vswitch $($vmNetCard.SwitchName)"
    }
    else {
      Write-Output "nic.vswitch none"
    }

    #vmNetCard MACAddress
    Write-Output "nic.dynamicMAC $($vmNetCard.DynamicMacAddressEnabled)"
    if ($vmNetCard.MacAddress.Length -ne 0) {
      Write-Output "nic.MAC $($vmNetCard.MacAddress)"
    }
    else {
      Write-Output "nic.MAC not assigned"
    }

    #vmNetCard IPAddress
    $vmnetCardIPs = $vmNetCard.IPAddresses
    if ($vmNetCard.IPAddresses.Length -ne 0) {
      foreach ($vmnetCardIP in $vmnetCardIPs) {
        Write-Output "nic.IP $($vmNetCardIP)"
      }
    }
    else {
      Write-Output "nic.IP not assigned"
    }
    # special features (could be extended in future versions)
    Write-Output "nic.security.DHCPGuard $($vmNetCard.DhcpGuard)"
    Write-Output "nic.security.RouterGuard $($vmNetCard.RouterGuard)"
    Write-Output "nic.VLAN.mode $($vmNetCard.VlanSetting.OperationMode)"
    Write-Output "nic.VLAN.id $($vmNetCard.VlanSetting.AccessVlanId)"
    if ($null -ne $vmNetCard.BandwidthSetting.MinimumBandwidthAbsolute -or $null -ne $vmNetCard.BandwidthSetting.MaximumBandwidth) {
      # Bandwidth settings say they use Mbit but they only multiply the GUI value by a million ...
      Write-Output "nic.bandwidth.min $($vmNetCard.BandwidthSetting.MinimumBandwidthAbsolute)"
      Write-Output "nic.bandwidth.max $($vmNetCard.BandwidthSetting.MaximumBandwidth)"
    }
  }
}

############################################################################################################
function Get-VMISInfo {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode
  )

  $vmIntSer = (Get-VMIntegrationService -VMName $vm.Name -ComputerName $clusterNode | Sort-Object Name)
  Write-Output "guest.tools.number $($vmIntSer.Count)"
  foreach ($IS in $vmIntSer) {
    if ($IS.Enabled) {
      $ISActive = 'active'
    }
    else {
      $ISActive = 'inactive'
    }
    Write-Output "guest.tools.service.$($IS.Name.Replace(' ', '_')) $ISActive"
  }
}

############################################################################################################
function Get-VMKVPdata {
  param
  (
    [Object]
    $vm,
    [Object]
    $clusterNode,
    [Object]
    $kvpAttribute
  )
  $VMKVPdata = $null
  $WMIFilter = "ElementName='$vm'"
  $attrName = "/INSTANCE/PROPERTY[@NAME='Name']/VALUE[child::text()='$kvpAttribute']"

  try {
    $VMWMI = Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter $WMIFilter -ComputerName $clusterNode -ErrorAction SilentlyContinue
    $VMWMI.GetRelated('Msvm_KvpExchangeComponent').GuestIntrinsicExchangeItems | ForEach-Object { `
        $GuestExchangeItemXml = ([XML]$_).SelectSingleNode(`
          $attrName)

      if ($null -ne $GuestExchangeItemXml) {
        $VMKVPdata = ($GuestExchangeItemXml.SelectSingleNode(`
              "/INSTANCE/PROPERTY[@NAME='Data']/VALUE/child::text()").Value)
      }
    }
  }
  catch {
    Write-Verbose "Failed to retrieve KVP data for VM '$vm' on '$clusterNode': $_"
  }

  return $VMKVPData
}

############################################################################################################

function Get-VMInventoryHost() {
  param
  (
    [Parameter(Mandatory = $false, Position = 1)]
    [string]$Node
  )

  # creates an inventory reports of all VMs on a single host

  if ($Node.Length -eq 0) {
    '<<<hyperv_node>>>'
    return
  }

  if ((Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V).State -ne 'Enabled') {
    '<<<hyperv_node>>>'
    Write-Output "Hyper-V feature is not enabled on $Node. Exiting."
    return
  }

  # connect only if host reacts to ping
  '<<<hyperv_node>>>'
  if (Test-Connection -ComputerName $Node -Quiet) {
    $vms = (Get-VM -ComputerName $Node | Sort-Object Name)
    Write-Output "vms.defined $($vms.count)"
    foreach ($vm in $vms) {
      '<<<<' + $vm.Name + '>>>>'
      '<<<hyperv_vm_general>>>'
      Get-VMGeneralInfo -vm $vm -clusterNode $Node
      '<<<hyperv_vm_checkpoints>>>'
      Get-vmCheckpoints -vm $vm -clusterNode $Node
      '<<<hyperv_vm_cpu>>>'
      Get-VMCPUInfo -vm $vm -clusterNode $Node
      '<<<hyperv_vm_ram>>>'
      Get-VMRAMInfo -vm $vm -clusterNode $Node
      '<<<hyperv_vm_vhd>>>'
      Get-VMDriveInfo -vm $vm -clusterNode $Node
      '<<<hyperv_vm_nic>>>'
      Get-VMNICInfo -vm $vm -clusterNode $Node
      '<<<hyperv_vm_integration>>>'
      Get-VMISInfo -vm $vm -clusterNode $Node
      '<<<<>>>>'
    }
  }
  else {
    '<<<hyperv_node>>>'
  }
}

Get-VMInventoryHost ($env:COMPUTERNAME)
