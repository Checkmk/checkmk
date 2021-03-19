$CMK_VERSION = "2.1.0i1"
## MS Exchange Database counters

## localize counter name
$locale = ([System.Globalization.Cultureinfo]::CurrentCulture.name)
switch -wildcard($locale){
    "en-*" {$counter_name = "\MSExchange Database ==> Instances(*)\*"}
    "de-*" {$counter_name = "\MSExchange-Datenbank  ==> Instanzen(*)\*"}
}

Write-Host "<<<msexch_database:sep(59)>>>"
Write-Host "locale;"$locale
Get-Counter -Counter $counter_name | % {$_.CounterSamples} | Select path,cookedvalue | ConvertTo-CSV -NoTypeInformation -Delimiter ";"
