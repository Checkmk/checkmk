#
# all the output should be changed to a tables format with keys as column names
# or better you should get directly json output
#


"<<<hyperv_host_io_local>>>"

$MaxSamples = 1
$Interval = 1

$Counters = @('\PhysicalDisk(*)\Current Disk Queue Length','\PhysicalDisk(*)\% Disk Time','\PhysicalDisk(*)\Avg. Disk Queue Length','\PhysicalDisk(*)\% Disk Read Time','\PhysicalDisk(*)\Avg. Disk Read Queue Length','\PhysicalDisk(*)\% Disk Write Time','\PhysicalDisk(*)\Avg. Disk Write Queue Length','\PhysicalDisk(*)\Avg. Disk sec/Transfer','\PhysicalDisk(*)\Avg. Disk sec/Read','\PhysicalDisk(*)\Avg. Disk sec/Write','\PhysicalDisk(*)\Disk Transfers/sec','\PhysicalDisk(*)\Disk Reads/sec','\PhysicalDisk(*)\Disk Writes/sec','\PhysicalDisk(*)\Disk Bytes/sec','\PhysicalDisk(*)\Disk Read Bytes/sec','\PhysicalDisk(*)\Disk Write Bytes/sec','\PhysicalDisk(*)\Avg. Disk Bytes/Transfer','\PhysicalDisk(*)\Avg. Disk Bytes/Read','\PhysicalDisk(*)\Avg. Disk Bytes/Write','\PhysicalDisk(*)\% Idle Time','\PhysicalDisk(*)\Split IO/Sec')

$Splat = @{
    Counter = $Counters
    MaxSamples = $MaxSamples
    SampleInterval = $Interval
}

$customobjects = @()

Get-Counter @Splat | ForEach {
    $_.CounterSamples | ForEach {
        $customobjects += [pscustomobject]@{
            Path = $_.Path
            Value = $_.CookedValue
        }
    }
}

$counts = @()
$remotecounts = @()
$idtolun = @{}

$csvs = Get-ClusterSharedVolume
foreach ( $csv in $csvs )
    {
    if ($csv | Where-Object {$_.OwnerNode -match $env:COMPUTERNAME})
        {
        $diskguid = ($csv | Get-ClusterParameter DiskIdGuid).Value
        $lunid = $csv.Name
        $disk = get-disk | Where-Object {$_.guid -match $diskguid}
        $diskid = $disk.DiskNumber
        $idtolun[$diskid] = $lunid
        $counts +=  $disk
        }
    else {
        $diskguid = ($csv | Get-ClusterParameter DiskIdGuid).Value
        $lunid = $csv.Name
        $disk = get-disk | Where-Object {$_.guid -match $diskguid}
        $diskid = $disk.DiskNumber
        $idtolun[$diskid] = $lunid
        $remotecounts +=  $disk
        }
    }

$resultlist = @()

foreach ( $volume in $counts) {
    foreach ( $element in $customobjects) {
        $checkString = $volume.Number
        if ($element.Path -match "\($checkString\)") {
            $element.Path = [regex]::Replace($element.Path, '\\\\.*\\physicaldisk\(.*\)\\',$idtolun[$checkString]+'\')
            $resultlist += $element
        }
    }
}

$hostname = $env:COMPUTERNAME.ToLower()

$resultlist | select Path, Value | % {
    $_.Path = [regex]::Replace($_.Path, "\\\\$hostname\\physicaldisk\([0-9]+\)","");
    $_.Value = $_.Value;
    return $_;
} | ft -HideTableHeaders

'<<<hyperv_host_io_remote>>>'

$resultlist = @()

foreach ( $volume in $remotecounts) {
    foreach ( $element in $customobjects) {
        $checkString = $volume.Number
        if ($element.Path -match "\($checkString\)") {
            $element.Path = [regex]::Replace($element.Path, '\\\\.*\\physicaldisk\(.*\)\\',$idtolun[$checkString]+'\')
            $resultlist += $element
        }
    }
}

$resultlist | ft -HideTableHeaders
