#  -----------------------------------------------------------------------------
#  Check_MK windows agent plugin to gather information about signature date
#  of Mcafee Virusscan 8.8 or ENS Anti-Virus software.
#
#  Supersedes the mcafee_av_client.bat plugin
#  -----------------------------------------------------------------------------

$dateval=""
$key="registry::HKLM\SOFTWARE\McAfee\AvEngine"
$p=get-itemproperty $key -ea 0
if ($p) {
  $dateval = $p.AVDatDate
} else {
  $key="registry::HKLM\SOFTWARE\Wow6432Node\McAfee\AvEngine"
  $p=get-itemproperty $key -ea 0
  if ($p) {
    $dateval = $p.AVDatDate
  } else {  
    $key="registry::HKLM\SOFTWARE\McAfee\AVSolution\DS\DS"
    $p=get-itemproperty $key -ea 0
    if ($p) {
      $dateval = $p.szContentCreationDate -replace "-","/"
    } else {
      $key="registry::HKLM\Software\Wow6432Node\McAfee\AVSolution\DS\DS"
      $p=get-itemproperty $key -ea 0
      if ($p) {
        $dateval = $p.szContentCreationDate -replace "-","/"
      }
    }
  }
}

if ($dateval -ne "") {
  write-host "<<<mcafee_av_client>>>"
  write-host $dateval
}
