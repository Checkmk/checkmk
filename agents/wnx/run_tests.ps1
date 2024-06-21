# To execute all complicated tests of windows agent
# params regression, component, ext, simulation, integration, all
#
# CI must run regression, component, integration, all
# Dev machine must run also ext and simulation
# later tests may require some additional package installed which ae not suitable for CI VM

if ((get-host).version.major -lt 7) {
    Write-Host "PowerShell version 7 or higher is required." -ForegroundColor Red
    exit
}


$testComponent = $false
$testExt = $false
$testSimulation = $false
$testIntegration = $false
$testRegression = $false
$testPlugins = $false
$testBuild = $false
$testAll = $false
$testUnit = $false
$repo_root = (get-item $pwd).parent.parent.FullName
$cur_dir = $pwd
$arte = "$repo_root/artefacts"

function Write-Help() {
    $x = Get-Item $PSCommandPath
    $x.BaseName
    $name = "powershell -File " + $x.BaseName + ".ps1"

    Write-Host "Usage:"
    Write-Host ""
    Write-Host "$name [arguments]"
    Write-Host ""
    Write-Host "Available arguments:"
    Write-Host "  -?, -h, --help       display help and exit"
    Write-Host "  -A, --all            shortcut to -B -C -S -E -R -I -P"
    Write-Host "  -B, --build          build"
    Write-Host "  -C, --component      component testing"
    Write-Host "  -S, --simulation     component testing"
    Write-Host "  -E, --ext            ext component testing"
    Write-Host "  -R, --regression     regression testing"
    Write-Host "  -I, --integration    integration testing"
    Write-Host "  -P, --plugins        plugins testing"
    Write-Host "  -U, --unit           unit testing"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ""
    Write-Host "$name --component"
    Write-Host "$name --build --integration"
}


if ($args.Length -eq 0) {
    Write-Host "No arguments provided. Running with default flags." -ForegroundColor Yellow
    $testComponent = $true
}
else {
    for ($i = 0; $i -lt $args.Length; $i++) {
        switch ($args[$i]) {
            { $("-?", "-h", "--help") -contains "$_" } { Write-Help; return }
            { $("-A", "--all") -contains $_ } { $testAll = $true }
            { $("-B", "--build") -contains $_ } { $testBuild = $true }
            { $("-C", "--component") -contains $_ } { $testComponent = $true }
            { $("-E", "--ext") -contains $_ } { $testExt = $true }
            { $("-S", "--simulation") -contains $_ } { $testSimulation = $true }
            { $("-P", "--plugins") -contains $_ } { $testPlugins = $true }
            { $("-I", "--integration") -contains $_ } { $testIntegration = $true }
            { $("-R", "--regression") -contains $_ } { $testRegression = $true }
            { $("-U", "--unit") -contains $_ } { $testUnit = $true }
        }
    }
}

if ($testExt -or $testIntegration -or $testComponent) {
    $testBuild = $true
}

if ($testAll) {
    $testComponent = $true
    $testExt = $true
    $testSimulation = $true
    $testIntegration = $true
    $testRegression = $true
    $testPlugins = $true
    $testBuild = $true
    $testAll = $true
    $testUnit = $true
}

function New-TemporaryDirectory() {
    param(
        [Parameter(
            Mandatory = $True,
            Position = 0
        )]
        [String]
        $prefix
    )
    try {
        $parent = [System.IO.Path]::GetTempPath()
        $name = "$prefix" + [System.IO.Path]::GetRandomFileName()
        $k = New-Item -ItemType Directory -Path (Join-Path $parent $name)
        return $k.FullName
    }
    catch {
        return ""
    }
}


function Test-Administrator {
    [OutputType([bool])]
    param()
    process {
        [Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent();
        return $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);
    }
}


function Invoke-PrepareTests($base) {
    $root = "$base\root"
    $data = "$base\data"
    $user_dir = $data
    New-Item -ItemType Directory -Path "$root\plugins" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$user_dir\bin" -ErrorAction Stop > nul

    & xcopy "..\windows\plugins\*.*"           "$root\plugins" "/D" "/Y" > nul
    & xcopy ".\tests\files\ohm\cli\*.*"        "$user_dir\bin" "/D" "/Y" > nul
    & xcopy ".\install\resources\check_mk.yml" "$root" "/D" "/Y" > nul

    & xcopy ".\test_files\config\*.yml"        "$root" "/D" "/Y" > nul

    & xcopy ".\test_files\config\*.cfg"        "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\config\*.test.ini"   "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\cap\*.test.cap"      "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\unit_test\*.ini"     "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\unit_test\*.dat"     "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\unit_test\*.state"   "$user_dir" "/D" "/Y" > nul
    & xcopy ".\test_files\config\*.yml"        "$user_dir" "/D" "/Y" > nul

}

function Invoke-UnitTest([bool]$run, [String]$name, [String]$cmdline) {
    if (!$run) {
        Write-Host "Skipping test $name..." -Foreground Yellow
        return
    }

    Write-Host "Running $name test..." -Foreground White
    $results = "${name}_tests_results.zip"
    $wnx_test_root = ""
    $prefix = "checkmk_$name_"
    try {
        $wnx_test_root = New-TemporaryDirectory -prefix "$prefix"
        if ($wnx_test_root -eq "") {
            Write-Error "Failed to create temporary directory" -ErrorAction Stop
        }
        $env:WNX_TEST_ROOT = $wnx_test_root
        Write-Host "Using temporary directory $wnx_test_root..." -Foreground White
        Invoke-PrepareTests "$wnx_test_root\test"
        New-Item -Path "$wnx_test_root\watest32.exe" -ItemType SymbolicLink -Value "$arte\watest32.exe" > nul
        & net stop WinRing0_1_2_0
        & "$wnx_test_root\watest32.exe" "--gtest_filter=$cmdline"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] $name test :$_" -ErrorAction Stop
        }
        Write-Host "Success $name test" -Foreground Green
    }
    finally {
        try {
            Remove-Item "$arte\$results" -ErrorAction SilentlyContinue
            Compress-Archive -Path $wnx_test_root -DestinationPath "$arte\$results"
        }
        catch {
            Write-Host "Failed to compress $wnx_test_root :$_" -Foreground Red
        }
        if ($wnx_test_root -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $wnx_test_root..." -Foreground White
            Remove-Item $wnx_test_root -Force -Recurse -ErrorAction SilentlyContinue
        }
    }

}


function Invoke-RegressionTest() {
    if (!$testRegression) {
        Write-Host "Skipping regression test..." -Foreground Yellow
        return
    }
    if (-not (Test-Administrator)) {
        Write-Error "Regression Testing must be executed as Administrator." -ErrorAction Stop
    }

    Write-Host "Running regression test..." -Foreground White
    $results = "regression_tests_results.zip"
    $wnx_test_root = ""
    $work_dir = "$pwd"
    $prefix = "checkmk_regression_"
    try {
        $wnx_test_root = New-TemporaryDirectory -prefix "$prefix"
        if ($wnx_test_root -eq "") {
            Write-Error "Failed to create temporary directory" -ErrorAction Stop
        }
        Write-Host "Using temporary directory $wnx_test_root..." -Foreground White
        $plugins_dir = "$wnx_test_root/test/root/plugins"
        $data_dir = "$wnx_test_root/test/data"
        New-Item -ItemType Directory -Path $plugins_dir -ErrorAction Stop > nul
        New-Item -ItemType Directory -Path $data_dir -ErrorAction Stop > nul
        Remove-NetFirewallRule -DisplayName "AllowRegression" 2> nul
        New-NetFirewallRule -DisplayName "AllowRegression" -Direction Inbound -Program "$wnx_test_root\check_mk_agent.exe" -RemoteAddress LocalSubnet -Action Allow >nul
        Copy-Item $arte\check_mk_agent.exe  $wnx_test_root\check_mk_agent.exe > nul
        Copy-Item $arte\check_mk.yml $wnx_test_root\test\root\check_mk.yml > nul
        &  xcopy "..\windows\plugins\*.*" "$wnx_test_root\test\root\plugins" "/D" "/Y" > nul
        $env:WNX_REGRESSION_BASE_DIR = "$wnx_test_root"
        $env:WNX_INTEGRATION_BASE_DIR = ""
        $env:arte = $arte
        Set-Location ".\tests\regression"
        py -3 -m pytest
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Regression test :$_" -ErrorAction Stop
        }
        Write-Host "Success regression test..." -Foreground Green
    }
    finally {
        try {
            Remove-Item "$arte\$results" -ErrorAction SilentlyContinue
            Compress-Archive -Path $wnx_test_root -DestinationPath "$arte\$results"
        }
        catch {
            Write-Host "Failed to compress $wnx_test_root :$_" -Foreground Red
        }
        Set-Location $work_dir -ErrorAction SilentlyContinue
        Remove-NetFirewallRule -DisplayName "AllowRegression" >nul
        if ($wnx_test_root -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $wnx_test_root..." -Foreground White
            Remove-Item $wnx_test_root -Force -Recurse -ErrorAction SilentlyContinue
        }
    }

}

function Invoke-IntegrationTest() {
    if (!$testIntegration) {
        Write-Host "Skipping integration test..." -Foreground Yellow
        return
    }
    if (-not (Test-Administrator)) {
        Write-Error "Integration Testing must be executed as Administrator." -ErrorAction Stop
    }
    $env:CHECKMK_GIT_DIR = $repo_root

    Write-Host "Running integration test..." -Foreground White
    $results = "integration_tests_results.zip"
    $wnx_test_root = ""
    $prefix = "checkmk_integration_"
    try {
        $wnx_test_root = New-TemporaryDirectory -prefix "$prefix"
        if ($wnx_test_root -eq "") {
            Write-Error "Failed to create temporary directory" -ErrorAction Stop
        }
        Write-Host "Using temporary directory $wnx_test_root..." -Foreground White
        $root_dir = "$wnx_test_root\test\root"
        $data_dir = "$wnx_test_root\test\data"

        Write-Host "Prepare dirs..." -Foreground White
        New-Item -ItemType Directory -Path $root_dir -ErrorAction Stop > nul
        New-Item -ItemType Directory -Path "$data_dir\plugins" -ErrorAction Stop > nul
        New-Item -ItemType Directory -Path "$data_dir\bin" -ErrorAction Stop > nul

        Write-Host "Prepare firewall..." -Foreground White
        Remove-NetFirewallRule -DisplayName "AllowIntegration1" 2> nul
        New-NetFirewallRule -DisplayName "AllowIntegration1" -Direction Inbound -Program "$wnx_test_root\check_mk_agent.exe" -RemoteAddress LocalSubnet -Action Allow >nul
        Remove-NetFirewallRule -DisplayName "AllowIntegration2" 2>nul
        New-NetFirewallRule -DisplayName "AllowIntegration2" -Direction Inbound -Program "$data_dir\bin\cmk-agent-ctl.exe" -RemoteAddress LocalSubnet -Action Allow > nul

        Write-Host "Copy exe..." -Foreground White
        Copy-Item $arte\check_mk_agent.exe  $wnx_test_root\check_mk_agent.exe > nul

        Write-Host "Copy yml..." -Foreground White
        Copy-Item $arte\check_mk.yml $wnx_test_root\test\root\check_mk.yml > nul
        &  xcopy "..\windows\plugins\*.*" "$wnx_test_root\test\root\plugins\" "/D" "/Y" > nul
        $env:WNX_REGRESSION_BASE_DIR = ""
        $env:WNX_INTEGRATION_BASE_DIR = "$wnx_test_root"
        $env:arte = $arte

        Write-Host "RUN INTEGRATION!" -Foreground White
        py -3 -m pytest tests\integration\
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Integration test :$_" -ErrorAction Stop
        }
        Write-Host "Success integration test..." -Foreground Green
    }
    finally {
        try {
            Remove-Item "$arte\$results" -ErrorAction SilentlyContinue
            Compress-Archive -Path $wnx_test_root -DestinationPath "$arte\$results"
        }
        catch {
            Write-Host "Failed to compress $wnx_test_root :$_" -Foreground Red
        }
        Remove-NetFirewallRule -DisplayName "AllowIntegration1" 2>nul
        Remove-NetFirewallRule -DisplayName "AllowIntegration2" 2>nul
        if ($wnx_test_root -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $wnx_test_root..." -Foreground White
            Remove-Item $wnx_test_root -Force -Recurse -ErrorAction SilentlyContinue
        }
    }

}


function Invoke-Exe {
    param(
        [Parameter(
            Mandatory = $True,
            Position = 0
        )]
        [bool]
        $run,
        [Parameter(
            Mandatory = $True,
            Position = 1
        )]
        [string]
        $name,
        [Parameter(
            Mandatory = $True,
            Position = 2
        )]
        [string]
        $exe,
        [Parameter(
            Mandatory = $True,
            ValueFromRemainingArguments = $true,
            Position = 3
        )][string[]]
        $listArgs
    )
    if ($run -ne $true) {
        Write-Host "Skipping $name..." -Foreground Yellow
        return
    }
    Write-Host "Running $name..." -Foreground White
    & $exe $listArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[-] $name :$_" -ErrorAction Stop
    }
    Write-Host "Running $name..." -Foreground White
}


$result = 1
try {
    $mainStartTime = Get-Date
    if ($testBuild) {
        & pwsh ./run.ps1 --build
    }

    Invoke-UnitTest -run $testUnit -name "unit" -cmdline "-*_Simulation:*Component:*ComponentExt:*Flaky"
    Invoke-UnitTest -run $testComponent -name "component" -cmdline "*Component"
    Invoke-UnitTest -run $testExt -name "ext" -cmdline "*ComponentExt"
    Invoke-UnitTest -run $testSimulation -name "simulation" -cmdline "*_Simulation"

    Invoke-RegressionTest
    Invoke-IntegrationTest
    try {
        Set-Location $repo_root
        $env:CHECKMK_GIT_DIR = $repo_root
        Invoke-Exe -run $testPlugins -name "plugins" -exe "py"  "-3" "-m" "pytest" "$cur_dir\tests\ap\test_mk_logwatch_win.py"
    }
    finally {
        Set-Location $cur_dir
    }

    $endTime = Get-Date
    $elapsedTime = $endTime - $mainStartTime
    Write-Host "Elapsed time: $($elapsedTime.Hours):$($elapsedTime.Minutes):$($elapsedTime.Seconds)"
    $result = 0
}
catch {
    Write-Host "Error: " $_ -ForegroundColor Red
    Write-Host "Trace stack: " -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Yellow
}
if ($result -eq 0) {
    Write-Host "SUCCESS" -ForegroundColor Green
}
exit $result
