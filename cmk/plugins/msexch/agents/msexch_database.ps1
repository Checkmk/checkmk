$CMK_VERSION = "3.0.0b1"
## MS Exchange Database counters

## localize counter name
$locale = ([System.Globalization.Cultureinfo]::CurrentCulture.name)
$decimal_separator = ([System.Globalization.Cultureinfo]::CurrentCulture.NumberFormat.NumberDecimalSeparator)

$counter_name = "\MSExchange Database ==> Instances(*)\*"
switch -wildcard($locale) {
    "de-*" { $counter_name = "\MSExchange-Datenbank  ==> Instanzen(*)\*" }
}

Write-Host "<<<msexch_database:sep(59)>>>"
Write-Host "locale;"$locale
Write-Host "separator;"$decimal_separator
Get-Counter -Counter $counter_name | % { $_.CounterSamples } | select path, cookedvalue | ConvertTo-Csv -NoTypeInformation -Delimiter ";"
