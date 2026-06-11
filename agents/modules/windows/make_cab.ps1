#
# Script to compress the folder into the cab file
#
param([string] $the_file, [string] $the_dir)

function compress-directory([string]$dir, [string]$output)
{
    $ddf = ".OPTION EXPLICIT
.Set CabinetNameTemplate=$output
.Set DiskDirectory1=
.Set CompressionType=LZX
.Set Cabinet=on
.Set Compress=on
.Set CabinetFileCountThreshold=0
.Set FolderFileCountThreshold=0
.Set FolderSizeThreshold=0
.Set MaxCabinetSize=0
.Set MaxDiskFileCount=0
.Set MaxDiskSize=0
"
    $dirfullname = (get-item $dir).fullname
    $ddfpath = ($env:TEMP+"\puthon_compress_$PID.ddf")
    $base_path = '.' + $dirfullname |  Split-Path -NoQualifier
    $base_path = [regex]::escape($base_path)
    $ddf += (ls -recurse $dir | where { !$_.PSIsContainer } | select -ExpandProperty FullName | foreach { '"' + $_ + '" "' + (($_ | Split-Path -NoQualifier) -replace "$base_path", '') + '"' }) -join "`r`n"
    $ddf | Out-File -Encoding UTF8 $ddfpath
    makecab.exe /F $ddfpath
    rm $ddfpath
    rm setup.inf
    rm setup.rpt
}

compress-directory "$the_dir" "$the_file"
