# MS Exchange Database counters

Write-Host "<<<msexch_database:sep(59)>>>"

Get-Counter -Counter "\MSExchange Database ==> Instances(*)\*" | % {$_.CounterSamples} | Select path,cookedvalue | ConvertTo-CSV -NoTypeInformation -Delimiter ";"
