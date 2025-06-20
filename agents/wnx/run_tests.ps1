# To execute all complicated tests of windows agent
# params regression, component, ext, simulation, integration, all
#
# CI must run regression, component, integration, powershell unit, all
# Dev machine must run also ext and simulation
# later tests may require some additional package installed which are not suitable for CI VM

if ((Get-Host).version.major -lt 7) {
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
$testBuildCtl = $false
$testAll = $false
$repo_root = (get-item $pwd).parent.parent.FullName
$cur_dir = $pwd
$env:repo_root = $repo_root
$results_dir = $repo_root + "\artefacts"

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
        }
    }
}

if ($testExt -or $testIntegration -or $testComponent) {
    $testBuild = $true
}

if ($testIntegration) {
    $testBuildCtl = $true
}

if ($testAll) {
    $testComponent = $true
    $testExt = $true
    $testSimulation = $true
    $testIntegration = $true
    $testRegression = $true
    $testPlugins = $true
    $testBuild = $true
    $testBuildCtl = $true
    $testAll = $true
}

function Write-Help() {
    $x = Get-Item $PSCommandPath
    $x.BaseName
    $name = "powershell -File " + $x.BaseName + ".ps1"

    Write-Host "Usage:"
    Write-Host ""
    Write-Host "$name [arguments]"
    Write-Host ""
    Write-Host "Available arguments:"
    Write-Host "  -?, -h, --help          display help and exit"
    Write-Host "  -A, --all               shortcut to -B -C -S -E -R -I -P"
    Write-Host "  -B, --build             build"
    Write-Host "  -C, --component         component testing"
    Write-Host "  -S, --simulation        simulation testing"
    Write-Host "  -E, --ext               ext component testing"
    Write-Host "  -R, --regression        regression testing"
    Write-Host "  -I, --integration       integration testing"
    Write-Host "  -P, --plugins           plugins testing"
    Write-Host "  -U, --unit              unit testing" # TODO remove, obsolete
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ""
    Write-Host "$name --component"
    Write-Host "$name --build --integration"
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

function Create_UnitTestDir([String]$prefix) {
    $wnx_test_dir = New-TemporaryDirectory -prefix "$prefix"
    Write-Host "Using temporary directory $wnx_test_dir..." -Foreground White
    if ($wnx_test_dir -eq "") {
        Write-Error "Failed to create temporary directory" -ErrorAction Stop
    }
    Copy-Item -Path ".\build\watest\Win32\Release\watest32.exe" -Destination "$wnx_test_dir\watest32.exe" -Force
    $root = "$wnx_test_dir\root"
    $data = "$wnx_test_dir\data"
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

    return $wnx_test_dir, "$wnx_test_dir\watest32.exe"
}

function Invoke-UnitTest([bool]$run, [String]$name, [String]$cmdline) {
    if (!$run) {
        Write-Host "Skipping test $name..." -Foreground Yellow
        return
    }

    Write-Host "Running $name test..." -Foreground White
    $firewall_rule_name = "AllowCheckMk_$name"
    $results = "${name}_tests_results.zip"
    $wnx_test_dir = ""
    $prefix = "checkmk_$name_"
    try {
        $wnx_test_dir, $exe_path = Create_UnitTestDir "$prefix"
        Create_FirewallRule $firewall_rule_name $exe_path
        $env:WNX_TEST_ROOT = $wnx_test_dir
        & net stop WinRing0_1_2_0
        & "$exe_path" --gtest_filter="$cmdline"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] $name test :$_" -ErrorAction Stop
        }
        Write-Host "Success $name test" -Foreground Green
    }
    finally {
        New-Item -ItemType Directory -Path $results_dir -ErrorAction SilentlyContinue > nul
        try {
            Remove-Item "$results_dir\$results" -ErrorAction SilentlyContinue
            Compress-Archive -Path $wnx_test_dir -DestinationPath "$results_dir\$results"
        }
        catch {
            Write-Host "Failed to compress $wnx_test_dir :$_" -Foreground Red
        }
        Remove-NetFirewallRule -DisplayName $firewall_rule_name -ErrorAction Continue
        if ($wnx_test_dir -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $wnx_test_dir..." -Foreground White
            Remove-Item $wnx_test_dir -Force -Recurse -ErrorAction SilentlyContinue
        }
    }
}

function Create_RegressionTestDir([String]$dir_prefix) {
    $regression_dir = New-TemporaryDirectory -prefix "$dir_prefix"
    if ($regression_dir -eq "") {
        Write-Error "Failed to create temporary directory" -ErrorAction Stop
    }
    Write-Host "Using temporary directory $regression_dir" -Foreground White
    $root_dir = "$regression_dir\test\root"
    $plugins_dir = "$regression_dir\test\root\plugins"
    $data_dir = "$regression_dir\test\data"
    New-Item -ItemType Directory -Path "$plugins_dir" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir" -ErrorAction Stop > nul
    Copy-Item .\build\check_mk_service\Win32\Release\check_mk_service32.exe $root_dir\check_mk_agent.exe -ErrorAction Stop > nul
    Copy-Item .\install\resources\check_mk.yml $root_dir\check_mk.yml  -ErrorAction Stop > nul
    &  xcopy "..\windows\plugins\*.*" "$plugins_dir" "/D" "/Y" > nul
    return $regression_dir, "$root_dir\check_mk_agent.exe"
}

function Create_FirewallRule([String]$name, [String]$exe_path) {
    Write-Host "Prepare firewall: $name for $exe_path" -Foreground White
    Remove-NetFirewallRule -DisplayName $name -ErrorAction Continue 2> nul
    New-NetFirewallRule -DisplayName $name -Direction Inbound -Program $exe_path -RemoteAddress LocalSubnet -Action Allow > nul
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
    $results_zip = "regression_tests_results.zip"
    $firewall_rule_name = "AllowCheckMkRegression"
    $regression_dir = ""
    $prefix = "checkmk_regression_"
    try {
        $regression_dir, $exe_path = Create_RegressionTestDir $prefix
        Create_FirewallRule $firewall_rule_name $exe_path
        $env:WNX_REGRESSION_BASE_DIR = "$regression_dir"
        $env:WNX_INTEGRATION_BASE_DIR = ""
        py -3 -m pytest tests\regression
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Regression test :$_" -ErrorAction Stop
        }
        Write-Host "Success regression test..." -Foreground Green
    }
    finally {
        try {
            Remove-Item "$results_dir\$results_zip" -ErrorAction SilentlyContinue
            Compress-Archive -Path $regression_dir -DestinationPath "$results_dir\$results_zip"
        }
        catch {
            Write-Host "Failed to compress $regression_dir :$_" -Foreground Red
        }
        Remove-NetFirewallRule -DisplayName $firewall_rule_name -ErrorAction Continue
        if ($regression_dir -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $regression_dir..." -Foreground White
            Remove-Item $regression_dir -Force -Recurse -ErrorAction SilentlyContinue
        }
    }
}

function Create_IntegrationTestDir([String]$dir_prefix) {
    $integration_dir = New-TemporaryDirectory -prefix "$prefix"
    if ($integration_dir -eq "") {
        Write-Error "Failed to create temporary directory" -ErrorAction Stop
    }
    Write-Host "Using temporary directory $integration_dir..." -Foreground White
    $root_dir = "$integration_dir\test\root"
    $plugins_dir = "$integration_dir\test\root\plugins"
    $data_dir = "$integration_dir\test\data"

    Write-Host "Prepare dirs..." -Foreground White
    New-Item -ItemType Directory -Path "$root_dir" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir\plugins" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir\bin" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir\modules" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir\modules\python-3" -ErrorAction Stop > nul
    New-Item -ItemType Directory -Path "$data_dir\install\modules" -ErrorAction Stop > nul  # need for cab to understand that python is installed
    New-Item -ItemType Directory -Path "$root_dir\plugins" -ErrorAction Stop > nul
    Write-Host "Copy exe..." -Foreground White
    Copy-Item .\build\check_mk_service\Win32\Release\check_mk_service32.exe $root_dir\check_mk_agent.exe > nul
    Copy-Item $repo_root\requirements\rust\host\target\i686-pc-windows-msvc\release\cmk-agent-ctl.exe $root_dir\cmk-agent-ctl.exe > nul

    Write-Host "Copy cab..." -Foreground White
    Copy-Item "$results_dir\python-3.cab"  "$root_dir" -Force -ErrorAction Stop > nul        		# unpack
    Copy-Item "$results_dir\python-3.cab"  "$data_dir\install\modules" -Force -ErrorAction Stop > nul   # check
    Write-Host "Copy yml..." -Foreground White
    Copy-Item ".\install\resources\check_mk.yml" "$root_dir\check_mk.yml" -Force -ErrorAction Stop > nul
    Write-Host "Copy plugins..." -Foreground White
    &  xcopy "..\windows\plugins\*.*" "$plugins_dir\" "/D" "/Y" > nul
    return $integration_dir, "$root_dir\check_mk_agent.exe", "$data_dir\bin\cmk-agent-ctl.exe"
}

function Invoke-IntegrationTest() {
    if (!$testIntegration) {
        Write-Host "Skipping integration test..." -Foreground Yellow
        return
    }
    if (-not (Test-Administrator)) {
        Write-Error "Integration Testing must be executed as Administrator." -ErrorAction Stop
    }

    Write-Host "Running integration test..." -Foreground White
    $results = "integration_tests_results.zip"
    $firewall_rule_name_agent = "AllowCheckMkIntegration_Agent"
    $firewall_rule_name_ctl = "AllowCheckMkIntegration_Ctl"
    $integration_dir = ""
    $prefix = "checkmk_integration_"
    try {
        $integration_dir, $agent_exe, $ctl_exe = Create_IntegrationTestDir -prefix "$prefix"
        Write-Host "Prepare firewall..." -Foreground White
        Create_FirewallRule $firewall_rule_name_agent $agent_exe
        Create_FirewallRule $firewall_rule_name_ctl $ctl_exe

        $env:WNX_REGRESSION_BASE_DIR = ""
        $env:WNX_INTEGRATION_BASE_DIR = "$integration_dir"
        Write-Host "RUN INTEGRATION in $env:WNX_INTEGRATION_BASE_DIR" -Foreground White
        py -3 -m pytest tests\integration\
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Integration test :$_" -ErrorAction Stop
        }
        Write-Host "Success integration test..." -Foreground Green
    }
    finally {
        try {
            Remove-Item "$results_dir\$results" -ErrorAction SilentlyContinue
            Compress-Archive -Path $integration_dir -DestinationPath "$results_dir\$results"
        }
        catch {
            Write-Host "Failed to compress $integration_dir :$_" -Foreground Red
        }
        Remove-NetFirewallRule -DisplayName $firewall_rule_name_agent -ErrorAction Continue
        Remove-NetFirewallRule -DisplayName $firewall_rule_name_ctl  -ErrorAction Continue
        if ($integration_dir -like "*temp*$prefix*") {
            Write-Host "Removing temporary directory $integration_dir..." -Foreground White
            Remove-Item $integration_dir -Force -Recurse -ErrorAction SilentlyContinue
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

function Invoke-PluginsUnitTests {
    if (!$testPlugins) {
        Write-Host "Skipping Powershell plugins unit tests..." -Foreground Yellow
        return
    }

    $minPesterVersion = [Version]'5.0.0'
    $pesterModule = Get-Module -ListAvailable -Name Pester | Sort-Object Version -Descending | Select-Object -First 1

    if (-not $pesterModule -or $pesterModule.Version -lt $minPesterVersion) {
        try {
            Install-Module -Name Pester -Scope CurrentUser -Force -ErrorAction Stop
        }
        catch {
            Write-Host "Failed to install Pester module: $_"
            return
        }
    }

    Write-Host "Running Powershell plugins unit tests..." -Foreground White
    $pluginsTestPath = Join-Path $PSScriptRoot "..\windows\unit_tests_ps1"
    if (-not (Test-Path $pluginsTestPath)) {
        Write-Host "Powershell plugins test directory not found: $pluginsTestPath" -ForegroundColor Red
        return
    }
    Write-Host "Running Powershell plugins tests in $pluginsTestPath..." -ForegroundColor White
    Invoke-Pester -Path $pluginsTestPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Powershell plugins unit tests failed, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Success Powershell plugins unit tests" -ForegroundColor Green
}

$result = 1
try {
    $mainStartTime = Get-Date
    if ($testBuild) {
        & pwsh ./run.ps1 --build
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Unable to rebuild" -ErrorAction Stop
        }
    }

    if ($testBuildCtl) {
        cd $repo_root/packages/cmk-agent-ctl
        try {
            & pwsh ./run.ps1 --build
            if ($LASTEXITCODE -ne 0) {
                Write-Error "[-] Unable to rebuild" -ErrorAction Stop
            }
        }
        finally {
            cd $cur_dir
        }
    }

    Invoke-UnitTest -run $testComponent -name "component" -cmdline "*Component"
    Invoke-UnitTest -run $testExt -name "ext" -cmdline "*ComponentExt"
    Invoke-UnitTest -run $testSimulation -name "simulation" -cmdline "*_Simulation"
    Invoke-PluginsUnitTests
    Invoke-RegressionTest
    Invoke-IntegrationTest
    try {
        Set-Location $repo_root
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
