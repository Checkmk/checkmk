$service = Get-Service -Name w32time -ErrorAction SilentlyContinue
if ($service -eq $null -or $service.Status -ne 'Running') {
    return
}

Write-Host "<<<w32time_status:sep(0)>>>"
try {
    $output = & w32tm /query /status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $output
    } else {
        Write-Host "Error: Unable to retrieve NTP status"
        Write-Host $output
    }
} catch {
    Write-Host "Error: Exception while retrieving NTP status"
    Write-Host $_
}
