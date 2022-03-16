$CMK_VERSION = "2.1.0b3"
#
#  http://blogs.technet.com/b/heyscriptingguy/archive/2006/12/04/how-can-i-expand-the-width-of-the-windows-powershell-console.aspx
# Output is a 4 column table of (Name: str, Jobs: int, PrinterStatus: int, Detectederrorstate: int)
# Name is a string that may contain spaces
# <<<win_printers>>>
# Printer Stockholm                     0                   3                   0
# WH1_BC_O3_UPS                         0                   3                   0

$pshost = get-host
$pswindow = $pshost.ui.rawui

$newsize = $pswindow.buffersize
$newsize.height = 300
$newsize.width = 150
$pswindow.buffersize = $newsize

Write-Host "<<<win_printers>>>"
$Data_Set1 = Get-WMIObject Win32_PerfFormattedData_Spooler_PrintQueue | Select Name, Jobs | Sort Name
$Data_Set2 = Get-WmiObject win32_printer | ?{$_.PortName -notmatch '^TS'} | Select Name, @{name="Jobs";exp={$null}}, PrinterStatus, DetectedErrorState | Sort Name

#
#  Merge the Job counts from Data_Set1 into Data_set2
#
#  Both "lists" are sorted into ascending Name order, so matching and merging is simple
#

$i = 0
$d1 = $data_set1[0]

foreach ($d2 in $Data_Set2) {
  #
  #  iterate through data_set1 elements until their "Name" >= the curent data_set2 element's "Name"
  #
  while ($d1 -ne $null -and $d1.Name -lt $d2.Name) {
	$d1 = $data_set1[++$i]
  }
  #
  #  if we have a match, store the "Jobs" value from data_set1 in data_set2,
  #  and move on to the next data_set1 element
  #
  #  if we don't have a match, data_set1 element's "Name" > data_set2 element's "Name",
  #  so keep the data_set1 element and go on to the next data_set2 element
  #
  if ($d1.name -eq $d2.Name) {
    $d2.Jobs = $d1.Jobs
    $d1 = $data_set1[++$i]
  }
}
#
#  If the "Jobs" element is Null, the printer was found in data_set2 but not in data_set1, so ignore it
#
$Data_Set2 | where { $_.Jobs -ne $null } | format-table -HideTableHeaders
