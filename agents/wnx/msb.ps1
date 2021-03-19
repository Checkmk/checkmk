# Powershell file to start in parallel jobs to build the agent
# unfortunately we have no good & alternative in Windows
#
# TODO: make output visible after job starting
# TODO: make diagnostic better
# 2019 (c) tribe29
# 

$make_exe = $Env:make_exe
if( "$make_exe" -eq "" ){
	Write-Host "make_exe should be defined for  the build" -foreground Red
        return 1
}

$sln = (Get-Item -Path ".\").FullName + "\wamain_build.sln"  # 'c:\z\m\check_mk\agents\wnx\wamain.sln'
$makefile = (Get-Item -Path ".\").FullName + "\Makefile" 
$host_dir = (Get-Item -Path ".\").FullName
# string below is used to quckly switch to the Powershell ISE, do not delete it
# $sln = 'c:\z\m\check_mk\agents\wnx\wamain.sln'

$platforms = "Configuration=Release,Platform=x86", "Configuration=Release,Platform=x64"
$err = 0
$StartTime = $(get-date)

function RunningCount($j_all){
    $running_count = 0
    foreach ($job in $j_all) {
        if ($job.State -eq 'Running'){
            $running_count +=1
        }
    }

    if($running_count -eq 0){
	Write-Host "end" -foreground Cyan
        return 0
    }
    $elapsedTime = $(get-date) - $global:StartTime
    Write-Host -NoNewLine "`rStill running " $running_count " seconds elapsed: " $elapsedTime.seconds -foreground Cyan
    return $running_count
}


function RcvJob($j, $name){
    if($err -ne 0){
        Stop-Job -Job $j
        return
    }

    Receive-Job -Job $j
    if ($j.State -eq 'Failed') {
        Write-Host "On " $name ":" ($job.ChildJobs[0].JobStateInfo.Reason.Message) -ForegroundColor Red
        $script:err = 1          
    } else {                     
        Write-Host "On " $name ": Success" -ForegroundColor Green 
    }
    return
}

# Bases
$msb = {
& "C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\msbuild.exe" $args 
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: " $LASTEXITCODE -foreground Red
    throw "Failed"
}
else {
    Write-Host "Success!" -foreground Green
}
}

$mk = {
& "$Env:make_exe" $args 
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: " $LASTEXITCODE -foreground Red
    throw "Failed make"
}
else {
    Write-Host "Success make!" -foreground Green
}
}

# disabled as unstable
# $j_make = start-job -Init ([ScriptBlock]::Create("Set-Location '$pwd'")) -scriptblock $mk -argumentlist "-w", "-j", "2", "frozen_binaries"


# Exe 32 & 64 bits
$j_s = @()
$target = "engine"
foreach($p in $platforms){
    Write-Host "Starting Job $target - $p" -foreground Blue
    $j_s += start-job -scriptblock $msb -argumentlist $sln, "/m:4", "/t:$target", "/p:$p"
}
Write-Host "Jobs waiting... This may take few minutes" -foreground White

do {
    Wait-Job -Job $j_s -Timeout 5 | Out-Null
} while(RunningCount($j_s) -eq 0 )

Write-Host "Jobs ready" -foreground Blue
foreach ($job in $j_s) {
    RcvJob $job "engine"
}

if($err -ne 0){
    Write-Host "Exiting powershell script" -foreground Red
    exit 1
}

#
$j_w = @()
$target = "check_mk_service"
foreach($p in $platforms){
    Write-Host "Starting Job $target - $p" -foreground Blue
    $n =  "$target" + "_"+ $pid.ToString() + "_""$p"
    $j_w += start-job -Name $n -scriptblock $msb -argumentlist $sln, "/m:4", "/t:$target", "/p:$p"
}
$target = "watest"
foreach($p in $platforms){
    Write-Host "Starting Job $target - $p" -foreground Blue
    $n =  "$target" + "_"+ $pid.ToString() + "_""$p"
    $j_w += start-job -Name $n -scriptblock $msb -argumentlist $sln, "/m:4", "/t:$target", "/p:$p"
}
Write-Host "Jobs waiting... This may take few minutes" -foreground White
do {
    Wait-Job -Job $j_w -Timeout 5 | Out-Null
} while(RunningCount($j_w) -eq 0 )

Write-Host "Jobs ready" -foreground Blue
foreach ($job in $j_w) {
    RcvJob $job $job.Name
}

# disabled as unstable ###############
# Wait-Job -Job $j_make | Out-Null
#
# Write-Host "Make ready" -foreground Blue
# RcvJob $j_make $j_make.Name


if($err -ne 0)
{
    Write-Host "Exiting powershell script" -foreground Red
    exit 1
}
