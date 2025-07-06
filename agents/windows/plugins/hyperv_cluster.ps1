#
# all the output should be changed to a tables format with keys as column names
# or better you should get directly json output
#

function Get-ClusterInfo()
{
'<<<hyperv_cluster_general>>>'
# get cluster core data
$cluster = Get-Cluster
Write-Host 'cluster.name' $cluster.Name

# get cluster IP address
$clusterGroup = Get-ClusterGroup | Where-Object { $_.GroupType -eq 'Cluster' }
$clusterIP = Get-ClusterResource | Where-Object { $_.ResourceType -eq 'IP Address' -and $_.OwnerGroup -eq $clusterGroup } | Get-ClusterParameter Address  
$clusterSubnet = Get-ClusterResource | Where-Object { $_.ResourceType -eq 'IP Address' -and $_.OwnerGroup -eq $clusterGroup } | Get-ClusterParameter SubnetMask
Write-Host 'cluster.ip' $clusterIP.Value
Write-Host 'cluster.subnet' $clusterSubnet.Value

# get quorum config and resource
$quorum = Get-ClusterQuorum
Write-Host 'quorum.resourcename' ($quorum.QuorumResource.Name)
Write-Host 'quorum.type' ($quorum.QuorumType)


# check for S2D presence
'<<<hyperv_cluster_s2d>>>'
if ($null -ne (Get-Command Get-ClusterStorageSpacesDirect -ErrorAction SilentlyContinue)) {
  $S2D = (Get-ClusterStorageSpacesDirect -ErrorAction SilentlyContinue)
  if ($null -ne $S2D) {
    Write-Host 'S2D' ($S2D.State)
    Write-Host 'S2D.name' ($S2D.Name)
    Write-Host 'S2D.cachemode.HDD' ($S2D.CacheModeHDD)
    Write-Host 'S2D.cachemode.SSD' ($S2D.CacheModeSSD)
    Write-Host 'S2D.cache.device_model' ($S2D.CacheDeviceModel)
    Write-Host 'S2D.cache.metadata_reserve_bytes' ($S2D.CacheMetadataReserveBytes)
    Write-Host 'S2D.cache.page_size_kbytes' ($S2D.CachePageSizeKBytes)
    
  }
}

# get cluster nodes
'<<<hyperv_cluster_nodes>>>'
$clusterNodes = (Get-ClusterNode | Sort-Object ID)
Write-Host 'cluster.number_of_nodes' ($clusterNodes.Count)

foreach ($clusterNode in $clusterNodes)
{
  Write-Host 'cluster.node.name' ($clusterNode.Name)
  Write-Host 'cluster.node.id ' ($clusterNode.ID) 
  Write-Host 'cluster.node.state' ($clusterNode.State)
  Write-Host 'cluster.node.info' ($clusterNoder.StatusInformation)
  Write-Host 'cluster.node.weight' ($clusterNode.NodeWeight)
  Write-Host 'cluster.node_vendor.manufacturer' ($clusterNode.Manufacturer)
  Write-Host 'cluster.node_vendor.model' ($clusterNode.Model)
  Write-Host 'cluster.node_vendor.serial' ($clusterNode.SerialNumber)
}

# get cluster networks
'<<<hyperv_cluster_network>>>'
$clusterNetworks = (Get-ClusterNetwork | Sort-Object Name)
Write-Host 'cluster.number_of_networks' ($clusterNetworks.Count)
foreach($clusterNetwork in $clusterNetworks)
{
    Write-Host 'cluster.network.name' ($clusterNetwork.Name)
    Write-Host 'cluster.network.role' ([string]$clusterNetwork.Role)
    Write-Host 'cluster.network.state' ($clusterNetwork.State)
    Write-Host 'cluster.network.ip' ($clusterNetwork.Address)
    Write-Host 'cluster.network.netmask' ($clusterNetwork.Addressmask)
    Write-Host 'cluster.network.ipv4_address' ($clusterNetwork.Ipv4Addresses)
    Write-Host 'cluster.network.ipv6_address' ($clusterNetwork.Ipv6Addresses)
}

# get cluster disks (non-CSV first, then CSV)
'<<<hyperv_cluster_disks>>>'
$ClusterDisks =  (Get-ClusterResource | Where-Object {$_.ResourceType -eq 'Physical Disk'} | Sort-Object OwnerGroup,Name)
Write-Host 'cluster.number_of_disks' ($ClusterDisks.Count)

foreach ($Disk in $ClusterDisks)
{
  Write-Host 'cluster.disk.name' ($Disk.Name)
  Write-Host 'cluster.disk.owner_group' ($Disk.OwnerGroup)
  Write-Host 'cluster.disk.owner_node' ($Disk.OwnerNode)
  Write-Host 'cluster.disk.state' ($Disk.State)
  
}

# get CSVs
'<<<hyperv_cluster_csv>>>'
$clusterSharedVolume = (Get-ClusterSharedVolume -Cluster $cluster | Sort-Object Name)
Write-Host 'cluster.number_of_csv' ($clusterSharedVolume.Count)

foreach ($CSV in $clusterSharedVolume)
{
  Write-Host 'cluster.csv.name' ($CSV.Name)
  Write-Host 'cluster.csv.owner' ($CSV.OwnerNode)
  foreach ($CSVInfo in $CSV.SharedVolumeInfo)
  {
    Write-Host 'cluster.csv.volume' ($CSVInfo.FriendlyVolumeName)
    $CSVVolume = Get-ClusterSharedVolume -Name $CSV.Name | select -Expand SharedVolumeInfo | select -Expand Partition
    Write-Host 'cluster.csv.size' ($CSVVolume.Size)
    Write-Host 'cluster.csv.free_space' ($CSVVolume.FreeSpace)
    Write-Host 'cluster.csv.used_space' ($CSVVolume.UsedSpace)
  }
}

# get clustered VMs 
'<<<hyperv_cluster_roles>>>'
$arrClusterVMs = (Get-ClusterGroup -Cluster $cluster | Where-Object {$_.GroupType -eq 'VirtualMachine'} | Sort-Object Name)
if ($arrClusterVMs.length -ne 0)
{
  Write-Host 'cluster.number_of_vms' $arrClusterVMs.length
  foreach ($clusterVM in $arrClusterVMs)
  {
    Write-Host 'cluster.vm.name' ($clusterVM.Name)
    Write-Host 'cluster.vm.state' ($clusterVM.State)
    Write-Host 'cluster.vm.owner' ($clusterVM.OwnerNode)
  }
}

# get additional cluster roles
'<<<hyperv_cluster_additional_roles>>>'
$arrRolesToIgnore = 'VirtualMachine', 'Cluster', 'AvailableStorage'
$arrClusterGroups = (Get-ClusterGroup -Cluster $cluster | Where-Object {$arrRolesToIgnore -notcontains $_.GroupType} | Sort-Object Name)
if ($arrClusterGroups.length -ne 0)
{
  Write-Host 'cluster.number_of_roles' ($arrClusterGroups.length)
  
  foreach ($clusterRole in $arrClusterGroups)
  {
    Write-Host 'cluster.role.name' ($clusterRole.Name)
    Write-Host 'cluster.role.state' ($clusterRole.State)
    Write-Host 'cluster.role.type' ($clusterRole.GroupType)
    Write-Host 'cluster.role.owner' ($clusterRole.OwnerNode)
  }
}

# determine CAU availability
'<<<hyperv_cluster_updater>>>'
$CAU = (Get-ClusterResource -Cluster $cluster | Where-Object { $_.ResourceType -eq 'ClusterAwareUpdatingResource' })
if ($null -ne $CAU) {
  Write-Host 'cluster.cau.state' ($CAU.State)
  Write-Host 'cluster.cau.name' ($CAU.OwnerGroup)
} else {
  Write-Host 'cluster.cau.state not installed'
  Write-Host 'cluster.cau.name -'
}
}

Get-ClusterInfo
