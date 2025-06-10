BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot "..\plugins\mk_inventory.ps1"
    . $scriptPath
}

Context "mk_inventory.ps1 Tests" {
    Describe "Initialize" {
        BeforeEach {
            # Clear script variables before each test
            Remove-Variable -Name delay, exePaths, regPaths, stateDir, confDir, remoteHost -Scope Script -ErrorAction SilentlyContinue
        }

        It "sets defaults when no env vars or config file" {
            Mock GetEnvVar { $null }
            Mock Test-Path { $false }

            Initialize

            $script:delay | Should -Be 14400
            $script:exePaths | Should -Be @()
            $script:regPaths | Should -Contain "Software\Microsoft\Windows\CurrentVersion\Uninstall"
            $script:regPaths | Should -Contain "Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            $script:stateDir | Should -BeNullOrEmpty
            $script:confDir | Should -BeNullOrEmpty
            $script:remoteHost | Should -Be "local"
        }

        It "uses config file values if present" {
            Mock GetEnvVar {
                param($name)
                switch ($name) {
                    "MK_CONFDIR" { "C:\Config" }
                    "MK_STATEDIR" { "C:\State" }
                    "REMOTE_HOST" { "myhost" }
                    default { $null }
                }
            }
            Mock Test-Path { $true }
            Mock Get-Content { '{"delay":42,"exePaths":["C:\\test\\path"],"regPaths":["SOFTWARE\\WOW6432Node\\Microsoft\\.NETFramework"]}' }

            Initialize

            $script:delay | Should -Be 42
            $script:exePaths | Should -Be @("C:\test\path")
            $script:regPaths | Should -Be @("SOFTWARE\WOW6432Node\Microsoft\.NETFramework")
            $script:stateDir | Should -Be "C:\State"
            $script:confDir | Should -Be "C:\Config"
            $script:remoteHost | Should -Be "myhost"
        }
    }

    Describe "CreateTimestamp" {
        BeforeEach {
            # Set up script variables for each test
            $script:stateDir = "C:\State"
            $script:remoteHost = ":myhost"
            $script:delay = 1000
        }

        It "does nothing if stateDir is not set" {
            $script:stateDir = $null
            Mock Test-Path { $false }
            Mock New-Item {}
            { CreateTimestamp } | Should -Not -Throw
            Assert-MockCalled New-Item -Times 0
        }

        It "creates a new timestamp file if it does not exist" {
            Mock Test-Path { $false }
            Mock New-Item {}
            CreateTimestamp
            Assert-MockCalled New-Item -ParameterFilter { $Path -like "*mk_inventory._myhost*" } -Times 1
        }

        It "exits if timestamp is too young" {
            $fixedNow = [datetime]'2025-09-01T12:00:00Z'
            Mock Get-Date { $fixedNow }
            Mock Test-Path { $true }
            Mock Get-Item { [pscustomobject]@{ LastWriteTime = [datetime]'2025-09-01T11:59:50Z' } }
            $script:delay = 10000
            $result = CreateTimestamp
            $result | Should -Be 'Exiting the script because timestamp is too young.'
        }

        It "outputs error message if creation of a new timestamp file fails" {
            Mock Test-Path { $false }
            Mock New-Item { throw "fail" }
            $output = CreateTimestamp
            $output | Should -Contain "Failed to create timestamp: fail"
        }
    }

    Describe "StartSection" {
        It "outputs the correct section header" {
            $name = "test_section"
            $sep = "99"
            $timeUntil = "1234567890"
            $expected = "<<<test_section:sep(99):persist(1234567890)>>>"
            StartSection $name $sep $timeUntil | Should -Be $expected
        }
    }

    Describe "GetWmiObject" {
        It "outputs expected WMI properties" {
            Mock Get-CimInstance {
                [PSCustomObject]@{
                    Name         = "TestCPU"
                    Manufacturer = "TestCorp"
                    Caption      = "Test CPU"
                }
                $fields = @("Name", "Manufacturer", "Caption")
                $result = GetWmiObject "Win32_Processor" $fields
                $result | Should -Contain "Name: TestCPU"
                $result | Should -Contain "Manufacturer: TestCorp"
                $result | Should -Contain "Caption: Test CPU"
            }
        }

        It "formats datetime properties as DMTF datetime strings" {
            Mock Get-CimInstance {
                [PSCustomObject]@{
                    InstallDate = [datetime]"2024-06-01T12:34:56"
                }
            }
            $fields = @("InstallDate")
            $result = GetWmiObject "Win32_TestClass" $fields
            # DMTF datetime format: yyyymmddHHMMSS.mmmmmmsUUU
            $result | Should -Match 'InstallDate: \d{14}\.\d{6}\+\d{3}'
        }
    }

    Describe "GetWmiObject2" {
        It "outputs expected WMI properties with UBR" {
            Mock Get-CimInstance {
                [PSCustomObject]@{
                    csname  = "TestHost"
                    caption = "Test OS"
                    version = "10.0.12345"
                }
            }
            Mock Get-ItemProperty { @{ UBR = 999 } }
            $fields = @("csname", "caption", "version")
            $result = GetWmiObject2 "Win32_OperatingSystem" $fields
            $result | Should -Match "TestHost\|Test OS\|10.0.12345.999"
        }
    }

    Describe "GetNetworkAdapter" {
        It "outputs expected network adapter info" {
            Mock Get-CimInstance {
                param($ClassName)
                if ($ClassName -eq "Win32_NetworkAdapter") {
                    [PSCustomObject]@{
                        Name             = "Red Hat VirtIO Ethernet Adapter"
                        ServiceName      = "netkvm"
                        MACAddress       = "00:11:22:33:44:55"
                        AdapterType      = "Ethernet 802.3"
                        DeviceID         = "1"
                        NetworkAddresses = @("192.168.1.100")
                        Speed            = 1000000000
                    }
                }
                elseif ($ClassName -eq "Win32_NetworkAdapterConfiguration") {
                    [PSCustomObject]@{
                        Description      = "Red Hat VirtIO Ethernet Adapter"
                        IPAddress        = @("192.168.1.100", "fe80::1234:5678:9abc:def0", "fec0::620f:5f63:adc5:f42f")
                        IPSubnet         = @("255.255.255.0", "64", "64")
                        DefaultIPGateway = @("192.168.1.1", "fe80::1")
                    }
                }
            }
            $fields = @("Name", "ServiceName", "MACAddress")
            $result = GetNetworkAdapter $fields
            $result | Should -Contain "Name: Red Hat VirtIO Ethernet Adapter"
            $result | Should -Contain "ServiceName: netkvm"
            $result | Should -Contain "MACAddress: 00:11:22:33:44:55"
            $result | Should -Contain "Address: 192.168.1.100 fe80::1234:5678:9abc:def0 fec0::620f:5f63:adc5:f42f"
            $result | Should -Contain "Subnet: 255.255.255.0 64 64"
            $result | Should -Contain "DefaultGateway: 192.168.1.1 fe80::1"
        }
    }

    Describe "GetRouteTable" {
        It "outputs expected route table info" {
            Mock Get-CimInstance {
                param($ClassName)
                if ($ClassName -eq "Win32_NetworkAdapter") {
                    [PSCustomObject]@{
                        InterfaceIndex = 1
                        Name           = "Red Hat VirtIO Ethernet Adapter"
                    }
                }
                elseif ($ClassName -eq "Win32_IP4RouteTable") {
                    [PSCustomObject]@{
                        Type           = 3
                        NextHop        = "192.168.1.1"
                        Destination    = "0.0.0.0"
                        Mask           = "0.0.0.0"
                        InterfaceIndex = 1
                    }
                }
            }
            $result = GetRouteTable
            $result | Should -Contain "direct|0.0.0.0|0.0.0.0|192.168.1.1|Red Hat VirtIO Ethernet Adapter"
        }
    }

    Describe "GetSoftwareFromInstaller" {
        It "outputs expected fields using ProductsEx" {
            $mockProduct = [psobject]::new()
            $mockProduct | Add-Member -MemberType NoteProperty -Name ProductCode -Value "{1234-5678}"
            $mockProduct | Add-Member -MemberType ScriptMethod -Name InstallProperty -Value {
                param($field)
                switch ($field) {
                    "ProductName" { "TestApp" }
                    "Publisher" { "TestCorp" }
                    "VersionString" { "1.2.3" }
                    "InstallDate" { "20240601" }
                    "Language" { "en-US" }
                    default { "" }
                }
            }
            $mockInstaller = [psobject]::new()
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name ProductsEx -Value {
                param($a, $b, $c)
                @($mockProduct)
            }

            $fields = @("ProductName", "Publisher", "VersionString", "InstallDate", "Language")
            $result = GetSoftwareFromInstaller $fields $mockInstaller
            $sep = [char]31
            $expected = "TestApp${sep}TestCorp${sep}1.2.3${sep}20240601${sep}en-US"
            $result | Should -Be $expected
        }

        It "outputs expected fields using Products fallback" {
            $mockInstaller = [psobject]::new()
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name ProductsEx -Value { throw "fail" }
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name Products -Value { @("{1234-5678}") }
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name ProductInfo -Value {
                param($code, $field)
                switch ($field) {
                    "ProductName" { "TestApp" }
                    "Publisher" { "TestCorp" }
                    "VersionString" { "1.2.3" }
                    "InstallDate" { "20240601" }
                    "Language" { "en-US" }
                    default { "" }
                }
            }

            $fields = @("ProductName", "Publisher", "VersionString", "InstallDate", "Language")
            $result = GetSoftwareFromInstaller $fields $mockInstaller
            $sep = [char]31
            $expected = "TestApp${sep}TestCorp${sep}1.2.3${sep}20240601${sep}en-US"
            $result | Should -Be $expected
        }

        It "outputs error message if installer cannot be queried" {
            $mockInstaller = [psobject]::new()
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name ProductsEx -Value { throw "fail" }
            $mockInstaller | Add-Member -MemberType ScriptMethod -Name Products -Value { throw "fail" }

            $fields = @("ProductName")
            $result = GetSoftwareFromInstaller $fields $mockInstaller
            $result | Should -Match "Cannot list installed software:.*fail"
        }
    }

    Describe "GetUpdates" {
        It "outputs header and formatted hotfix info" {
            Mock Get-CimInstance { [pscustomobject]@{ Name = "DESKTOP-TEST" } }
            $mockHotFixes = @(
                [pscustomobject]@{ Description = "Security Update"; HotFixID = "KB123456"; InstalledOn = [datetime]"2024-06-01" },
                [pscustomobject]@{ Description = "Update"; HotFixID = "KB654321"; InstalledOn = "6/2/2024" }
            )
            Mock Get-HotFix { $mockHotFixes }

            $output = GetUpdates

            $output[0] | Should -Be "Node,Description,HotFixID,InstalledOn"
            $output[1] | Should -Be "DESKTOP-TEST,Security Update,KB123456,6/1/2024"
            $output[2] | Should -Be "DESKTOP-TEST,Update,KB654321,6/2/2024"
        }
    }

    Describe "EscapeRegistryPath" {
        It "escapes [" {
            EscapeRegistryPath 'HKLM:\Software\Key[1]' | Should -Be 'HKLM:\Software\Key`[1`]'
        }
        It "escapes ]" {
            EscapeRegistryPath 'HKLM:\Software\Key]1[' | Should -Be 'HKLM:\Software\Key`]1`['
        }
        It "escapes multiple squared brackets" {
            EscapeRegistryPath 'HKLM:\Software\Key[1]text[2]' | Should -Be 'HKLM:\Software\Key`[1`]text`[2`]'
        }
        It "escapes backtick" {
            EscapeRegistryPath 'HKLM:\Software\Key`1' | Should -Be 'HKLM:\Software\Key``1'
        }
        It "escapes *" {
            EscapeRegistryPath 'HKLM:\Software\Key*1' | Should -Be 'HKLM:\Software\Key`*1'
        }
        It "escapes ?" {
            EscapeRegistryPath 'HKLM:\Software\Key?1' | Should -Be 'HKLM:\Software\Key`?1'
        }
        It "escapes double quote" {
            EscapeRegistryPath 'HKLM:\Software\Key"1' | Should -Be 'HKLM:\Software\Key`"1'
        }
        It "escapes all at once" {
            EscapeRegistryPath 'HKLM:\Software\Key[1]*?""' | Should -Be 'HKLM:\Software\Key`[1`]`*`?`"`"'
        }
        It "does not escape single quote" {
            EscapeRegistryPath 'HKLM:\Software\Key'1' | Should -Be 'HKLM:\Software\Key'1'
        }
    }

    Describe "GetSoftwareFromRegistry" {
        It "outputs expected registry software info in correct format" {
            $mockSubkey = [PSCustomObject]@{
                PSPath      = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Git_is1'
                PSChildName = 'Git_is1'
            }
            Mock Get-ChildItem { @($mockSubkey) }
            Mock Test-Path { $true }
            Mock Get-ItemProperty {
                @{
                    DisplayName     = "Git"
                    Publisher       = "The Git Development Community"
                    InstallLocation = "C:\Program Files\Git"
                    DisplayVersion  = "2.47.1.2"
                    EstimatedSize   = "20250206"
                    InstallDate     = $null
                    Language        = $null
                }
            }

            $script:regPaths = @("Microsoft\Windows\CurrentVersion\Uninstall")
            $script:HKLM = "HKLM:\"

            $output = GetSoftwareFromRegistry

            # The output should contain the fields joined by ASCII 31
            $sep = [char]31
            $expected = "Git${sep}The Git Development Community${sep}C:\Program Files\Git${sep}Git_is1${sep}2.47.1.2${sep}20250206${sep}${sep}"
            $output | Should -Contain $expected
        }
    }

    Describe "RecurseFolderForExecs" {
        It "outputs details for .exe files in folder and subfolders" {
            $mockExe = [pscustomobject]@{
                FullName      = "C:\Test\app.exe"
                Extension     = ".exe"
                LastWriteTime = [datetime]"2024-06-01T12:00:00"
                Length        = 123456
            }
            $mockTxt = [pscustomobject]@{
                FullName      = "C:\Test\readme.txt"
                Extension     = ".txt"
                LastWriteTime = [datetime]"2024-06-01T11:00:00"
                Length        = 100
            }
            $mockSubExe = [pscustomobject]@{
                FullName      = "C:\Test\Sub\tool.exe"
                Extension     = ".exe"
                LastWriteTime = [datetime]"2024-06-01T13:00:00"
                Length        = 654321
            }
            $mockDir = [pscustomobject]@{ FullName = "C:\Test\Sub" }

            Mock Get-ChildItem {
                param(
                    $Path,
                    [switch]$File,
                    [switch]$Directory
                )

                if ($File.IsPresent) {
                    if ($Path -eq "C:\Test") { @($mockExe, $mockTxt) }
                    elseif ($Path -eq "C:\Test\Sub") { @($mockSubExe) }
                    else { @() }
                }
                elseif ($Directory.IsPresent) {
                    if ($Path -eq "C:\Test") { @($mockDir) }
                    elseif ($Path -eq "C:\Test\Sub") { @() }
                    else { @() }
                }
                else {
                    @()
                }
            }
            Mock Get-Item {
                param($Path)
                [pscustomobject]@{ VersionInfo = [pscustomobject]@{ FileVersionRaw = "1.2.3.4" } }
            }

            $output = & { RecurseFolderForExecs "C:\Test" }

            $output | Should -Not -Be $null
        ($output | Where-Object { $_ -eq "C:\Test\app.exe|6/1/2024 12:00:00|123456||1.2.3.4|" }) | Should -Not -BeNullOrEmpty
        ($output | Where-Object { $_ -eq "C:\Test\Sub\tool.exe|6/1/2024 13:00:00|654321||1.2.3.4|" }) | Should -Not -BeNullOrEmpty
        ($output | Where-Object { $_ -eq "C:\Test\readme.txt|6/1/2024 11:00:00|100||1.2.3.4|" }) | Should -BeNullOrEmpty
        }
    }

    Describe "GetSoftwareFromFilesystem" {
        It "calls RecurseFolderForExecs for each valid exePath" {
            $script:exePaths = @("C:\Path1", "C:\Path2", "C:\Path3")
            Mock Test-Path { $Path -ne "C:\Path2" } # Only Path1 and Path3 exist
            Mock RecurseFolderForExecs { "output for $Path" }

            $result = GetSoftwareFromFilesystem

            Assert-MockCalled Test-Path -ParameterFilter { $Path -eq "C:\Path1" -and $PathType -eq "Container" } -Times 1
            Assert-MockCalled Test-Path -ParameterFilter { $Path -eq "C:\Path2" -and $PathType -eq "Container" } -Times 1
            Assert-MockCalled Test-Path -ParameterFilter { $Path -eq "C:\Path3" -and $PathType -eq "Container" } -Times 1

            Assert-MockCalled RecurseFolderForExecs -ParameterFilter { $folderPath -eq "C:\Path1" } -Times 1
            Assert-MockCalled RecurseFolderForExecs -ParameterFilter { $folderPath -eq "C:\Path3" } -Times 1
            Assert-MockCalled RecurseFolderForExecs -ParameterFilter { $folderPath -eq "C:\Path2" } -Times 0

            $result | Should -Contain "output for C:\Path1"
            $result | Should -Contain "output for C:\Path3"
        }
    }
}
