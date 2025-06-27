# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

BeforeAll {
    # Dummy functions to be able to mock HyperV system calls when HyperV feature is disabled
    function Get-VMIntegrationService { return @() }
    function Get-VMNetworkAdapter { return @() }
    function Get-VMHardDiskDrive { return @() }
    function Get-VMMemory { return @() }
    function Get-VMProcessor { return @() }
    function Get-VMSnapshot { return @() }
    function Get-VMReplication { return $null }
    function Get-VMConnectAccess { return @() }
    function Get-VHD { return $null }
    function Get-VMFibreChannelHba { return @() }

    $scriptPath = Join-Path $PSScriptRoot "..\plugins\hyperv_host.ps1"
    . $scriptPath
}

Context "Hyper-V Host Plugin Tests" {

    Describe "Get-VMGeneralInfo" {

        It "outputs all expected fields for a non-clustered VM" {

            Mock Get-VMKVPdata { param($vm, $clusterNode, $kvpAttribute) return "mock-$kvpAttribute" }
            Mock Get-VMReplication { return $null }
            Mock Get-VMConnectAccess { return @() }
            Mock Get-Command { return $true }

            # The real Get-VMSecurity expects a [Microsoft.HyperV.PowerShell.VirtualMachine] object for its -VM parameter,
            # but the test is passing a [PSCustomObject]. So we override Get-VMSecurity in the test scope to avoid the type check.
            function Get-VMSecurity {
                param($VM)
                [PSCustomObject]@{
                    Shielded                          = $false
                    TpmEnabled                        = $false
                    KsdEnabled                        = $false
                    EncryptStateAndVmMigrationTraffic = $false
                }
            }

            $vm = [PSCustomObject]@{
                Name                     = "TestVM"
                IsClustered              = $false
                ComputerName             = "Host1"
                State                    = "Running"
                Status                   = "Operating normally"
                VMId                     = "12345678-1234-1234-1234-123456789abc"
                Generation               = 2
                Version                  = "9.0"
                CreationTime             = "2024-01-01"
                Groups                   = $null
                IntegrationServicesState = "UpToDate"
                AutomaticStopAction      = "Shutdown"
                AutomaticStartAction     = "StartIfRunning"
                AutomaticStartDelay      = 0
                ConfigurationLocation    = "C:\VMs\TestVM"
                SnapshotFileLocation     = "C:\VMs\TestVM\Snapshots"
                CheckpointType           = $null
            }
            $clusterNode = "Node1"

            $expected = @(
                "name TestVM"
                "cluster.clustered False"
                "runtime.host Host1"
                "runtime.powerState Running"
                "runtime.operationState Operating normally"
                "config.vmid 12345678-1234-1234-1234-123456789abc"
                "config.generation 2"
                "config.version 9.0"
                "config.created 2024-01-01"
                "guest.fqdn mock-FullyQualifiedDomainName"
                "guest.os mock-OSName"
                "guest.IntegrationServicesVersion mock-IntegrationServicesVersion"
                "guest.IntegrationServicesState UpToDate"
                "config.AutomaticStopAction Shutdown"
                "config.AutomaticStartAction StartIfRunning"
                "config.AutomaticStartDelay 0"
                "config.ConfigurationPath C:\VMs\TestVM"
                "config.CheckpointPath C:\VMs\TestVM\Snapshots"
                "config.CurrentCheckpointType Standard_(legacy)"
                "replication.mode not configured"
                "access nobody"
                "security.shieldedVM False"
                "security.TPMEnabled False"
                "security.KeyStorageDriveEnabled False"
                "security.StateMigrationEncrypted False"
            )

            $actual = & {
                $output = & {
                    Get-VMGeneralInfo -vm $vm -clusterNode $clusterNode
                } | Out-String
                $output -split "`r?`n" | Where-Object { $_ -ne "" }
            }

            $actual | Should -BeExactly $expected
        }
    }


    Describe "Get-vmCheckpoints" {

        It "outputs all expected fields when checkpoints exist" {
            Mock Get-VMSnapshot {
                return @(
                    [PSCustomObject]@{
                        Name               = "Checkpoint1"
                        Path               = "C:\VMs\Checkpoints\Checkpoint1"
                        CreationTime       = "2024-01-01T12:00:00"
                        ParentSnapshotName = $null
                    },
                    [PSCustomObject]@{
                        Name               = "Checkpoint2"
                        Path               = "C:\VMs\Checkpoints\Checkpoint2"
                        CreationTime       = "2024-01-02T12:00:00"
                        ParentSnapshotName = "Checkpoint1"
                    }
                )
            }

            $vm = [PSCustomObject]@{
                Name = "TestVM"
            }
            $clusterNode = "Node1"

            $expected = @(
                "checkpoints 2"
                "checkpoint.name Checkpoint1"
                "checkpoint.path C:\VMs\Checkpoints\Checkpoint1"
                "checkpoint.created 2024-01-01T12:00:00"
                "checkpoint.parent "
                "checkpoint.name Checkpoint2"
                "checkpoint.path C:\VMs\Checkpoints\Checkpoint2"
                "checkpoint.created 2024-01-02T12:00:00"
                "checkpoint.parent Checkpoint1"
            )

            $actual = Get-vmCheckpoints -vm $vm -clusterNode $clusterNode
            $actual | Should -BeExactly $expected
        }

        It "outputs none when no checkpoints exist" {
            Mock Get-VMSnapshot { @() } -Verifiable
            $vm = [PSCustomObject]@{
                Name = "TestVM"
            }
            $clusterNode = "Node1"
            $expected = @(
                "checkpoints 0"
                "checkpoints none"
            )

            $actual = Get-vmCheckpoints -vm $vm -clusterNode $clusterNode
            $actual | Should -BeExactly $expected
        }
    }

    Describe "Get-VMCPUInfo" {
        BeforeAll {
            Mock Get-VMProcessor {
                [PSCustomObject]@{
                    CompatibilityForOlderOperatingSystemsEnabled = $true
                    CompatibilityForMigrationEnabled             = $false
                    EnableHostResourceProtection                 = $true
                    ExposeVirtualizationExtensions               = $false
                }
            }

            $vm = [PSCustomObject]@{
                Name           = "TestVM"
                ProcessorCount = 4
            }
            $clusterNode = "Node1"
        }

        It "outputs all expected CPU info fields" {
            $expected = @(
                "config.hardware.numCPU 4"
                "config.hardware.CompatibilityForOlderOS True"
                "config.hardware.CompatibilityForMigration False"
                "config.hardware.HostResourceProtection True"
                "config.hardware.NestedVirtualization False"
            )

            $actual = Get-VMCPUInfo -vm $vm -clusterNode $clusterNode
            $actual | Should -BeExactly $expected
        }

        It "omits optional fields if they are null" {
            Mock Get-VMProcessor {
                [PSCustomObject]@{
                    CompatibilityForOlderOperatingSystemsEnabled = $false
                    CompatibilityForMigrationEnabled             = $true
                    EnableHostResourceProtection                 = $null
                    ExposeVirtualizationExtensions               = $null
                }
            } -Verifiable

            $expected = @(
                "config.hardware.numCPU 4"
                "config.hardware.CompatibilityForOlderOS False"
                "config.hardware.CompatibilityForMigration True"
            )

            $actual = Get-VMCPUInfo -vm $vm -clusterNode $clusterNode
            $actual | Should -BeExactly $expected
        }
    }

    Describe "Get-VMRAMInfo" {

        Context "When Dynamic Memory is enabled" {
            It "Outputs correct dynamic memory info" {
                $vm = [PSCustomObject]@{ Name = "TestVM"; MemoryStartup = 4096MB }
                $clusterNode = "Node1"
                $mockMemory = [PSCustomObject]@{
                    DynamicMemoryEnabled = $true
                    Startup              = 2048MB
                    Minimum              = 1024MB
                    Maximum              = 4096MB
                }

                Mock Get-VMMemory { $mockMemory }

                $output = Get-VMRAMInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "config.hardware.RAMType Dynamic Memory"
                $output | Should -Contain "config.hardware.StartRAM 2048"
                $output | Should -Contain "config.hardware.MinRAM 1024"
                $output | Should -Contain "config.hardware.MaxRAM 4096"
            }
        }

        Context "When Dynamic Memory is disabled" {
            It "Outputs correct static memory info" {
                $vm = [PSCustomObject]@{ Name = "TestVM"; MemoryStartup = 4096MB }
                $clusterNode = "Node1"
                $mockMemory = [PSCustomObject]@{
                    DynamicMemoryEnabled = $false
                }

                Mock Get-VMMemory { $mockMemory }

                $output = Get-VMRAMInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "config.hardware.RAMType Static Memory"
                $output | Should -Contain "config.hardware.RAM 4096"
            }
        }
    }

    Describe "Get-VMDriveInfo" {

        Context "When VM has one VHD with VHD info" {
            It "Outputs correct VHD info" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $vmHDD = [PSCustomObject]@{
                    Name               = "Hard Drive on SCSI controller number 0 at location 1"
                    ID                 = "Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C\0\0\D"
                    ControllerType     = "SCSI"
                    ControllerNumber   = 0
                    ControllerLocation = 1
                    Path               = "C:\VMs\Disk1.avhdx"
                }
                $vmHDDs = @($vmHDD)
                $vhdInfo = [PSCustomObject]@{
                    VhdFormat = "VHDX"
                    VhdType   = "Differencing"
                    Size      = 2147483648 # 2GB in bytes
                    FileSize  = 1073741824 # 1GB in bytes
                }

                Mock Get-VMHardDiskDrive { $vmHDDs }
                Mock Get-VHD { $vhdInfo }
                Mock Get-VMFibreChannelHba { @() }

                $output = Get-VMDriveInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "vhd 1"
                $output | Should -Contain "vhd.name Hard Drive on SCSI controller number 0 at location 1"
                $output | Should -Contain "vhd.controller.id Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C\0\0\D"
                $output | Should -Contain "vhd.controller.type SCSI"
                $output | Should -Contain "vhd.controller.number 0"
                $output | Should -Contain "vhd.controller.location 1"
                $output | Should -Contain "vhd.path C:\VMs\Disk1.avhdx"
                $output | Should -Contain "vhd.format VHDX"
                $output | Should -Contain "vhd.type Differencing"
                $output | Should -Contain "vhd.maximumcapacity 2048"
                $output | Should -Contain "vhd.usedcapacity 1024"
            }
        }

        Context "When VM has one VHD without VHD info" {
            It "Outputs Direct type if Get-VHD returns null" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $vmHDD = [PSCustomObject]@{
                    Name               = "Disk2"
                    ID                 = "2"
                    ControllerType     = "IDE"
                    ControllerNumber   = 1
                    ControllerLocation = 0
                    Path               = "C:\VMs\Disk2.vhdx"
                }
                $vmHDDs = @($vmHDD)

                Mock Get-VMHardDiskDrive { $vmHDDs }
                Mock Get-VHD { $null }
                Mock Get-VMFibreChannelHba { @() }

                $output = Get-VMDriveInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "vhd 1"
                $output | Should -Contain "vhd.name Disk2"
                $output | Should -Contain "vhd.controller.id 2"
                $output | Should -Contain "vhd.controller.type IDE"
                $output | Should -Contain "vhd.controller.number 1"
                $output | Should -Contain "vhd.controller.location 0"
                $output | Should -Contain "vhd.path C:\VMs\Disk2.vhdx"
                $output | Should -Contain "vhd.type Direct"
            }
        }

        Context "When VM has vSAN adapters" {
            It "Outputs vSAN info" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $vmHDDs = @()
                $vsan = [PSCustomObject]@{
                    SanName               = "SAN1"
                    WorldWideNodeNameSetA = "WWNN-A"
                    WorldWidePortNameSetA = "WWPN-A"
                    WorldWideNodeNameSetB = "WWNN-B"
                    WorldWidePortNameSetB = "WWPN-B"
                    ID                    = "VSAN1"
                }

                Mock Get-VMHardDiskDrive { $vmHDDs }
                Mock Get-VHD { $null }
                Mock Get-VMFibreChannelHba { @($vsan) }

                $output = Get-VMDriveInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "vhd 0"
                $output | Should -Contain "vsan 1"
                $output | Should -Contain "vsan.name SAN1"
                $output | Should -Contain "vsan.primaryWWNN WWNN-A"
                $output | Should -Contain "vsan.primaryWWPN WWPN-A"
                $output | Should -Contain "vsan.secondaryWWNN WWNN-B"
                $output | Should -Contain "vsan.secondaryWWPN WWPN-B"
                $output | Should -Contain "vsan.id VSAN1"
            }
        }
    }

    Describe "Get-VMNICInfo" {

        Context "When VM has one network adapter with all properties" {
            It "Outputs correct NIC info" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $nic = [PSCustomObject]@{
                    Name                     = "Network Adapter"
                    ID                       = "Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C"
                    Connected                = $true
                    SwitchName               = "Default Switch"
                    DynamicMacAddressEnabled = $true
                    MacAddress               = "00155D010203"
                    IPAddresses              = @("192.168.1.10", "fe80::1")
                    DhcpGuard                = "Off"
                    RouterGuard              = "Off"
                    VlanSetting              = [PSCustomObject]@{
                        OperationMode = "Untagged"
                        AccessVlanId  = 10
                    }
                    BandwidthSetting         = [PSCustomObject]@{
                        MinimumBandwidthAbsolute = 100
                        MaximumBandwidth         = 1000
                    }
                }
                $vmNetCards = @($nic)

                Mock Get-VMNetworkAdapter { $vmNetCards }

                $output = Get-VMNICInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "nic 1"
                $output | Should -Contain "nic.name Network Adapter"
                $output | Should -Contain "nic.id Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C"
                $output | Should -Contain "nic.connectionstate True"
                $output | Should -Contain "nic.vswitch Default Switch"
                $output | Should -Contain "nic.dynamicMAC True"
                $output | Should -Contain "nic.MAC 00155D010203"
                $output | Should -Contain "nic.IP 192.168.1.10"
                $output | Should -Contain "nic.IP fe80::1"
                $output | Should -Contain "nic.security.DHCPGuard Off"
                $output | Should -Contain "nic.security.RouterGuard Off"
                $output | Should -Contain "nic.VLAN.mode Untagged"
                $output | Should -Contain "nic.VLAN.id 10"
                $output | Should -Contain "nic.bandwidth.min 100"
                $output | Should -Contain "nic.bandwidth.max 1000"
            }
        }

        Context "When VM has a NIC with no MAC or IP" {
            It "Outputs not assigned for MAC and IP" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $nic = [PSCustomObject]@{
                    Name                     = "Network Adapter"
                    ID                       = "Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C"
                    Connected                = $false
                    SwitchName               = ""
                    DynamicMacAddressEnabled = $false
                    MacAddress               = ""
                    IPAddresses              = @()
                    DhcpGuard                = "Off"
                    RouterGuard              = "Off"
                    VlanSetting              = [PSCustomObject]@{
                        OperationMode = "Untagged"
                        AccessVlanId  = 0
                    }
                    BandwidthSetting         = [PSCustomObject]@{
                        MinimumBandwidthAbsolute = $null
                        MaximumBandwidth         = $null
                    }
                }
                $vmNetCards = @($nic)

                Mock Get-VMNetworkAdapter { $vmNetCards }

                $output = Get-VMNICInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "nic 1"
                $output | Should -Contain "nic.name Network Adapter"
                $output | Should -Contain "nic.id Microsoft:2211F777-6A47-4411-81DC-AC7769111191\CC1F1658-1135-1111-A87C-35F7B259360C"
                $output | Should -Contain "nic.connectionstate False"
                $output | Should -Contain "nic.vswitch none"
                $output | Should -Contain "nic.dynamicMAC False"
                $output | Should -Contain "nic.MAC not assigned"
                $output | Should -Contain "nic.IP not assigned"
                $output | Should -Contain "nic.security.DHCPGuard Off"
                $output | Should -Contain "nic.security.RouterGuard Off"
                $output | Should -Contain "nic.VLAN.mode Untagged"
                $output | Should -Contain "nic.VLAN.id 0"
            }
        }
    }

    Describe "Get-VMISInfo" {

        Context "When VM has two integration services" {
            It "Outputs correct integration service info" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $intServices = @(
                    [PSCustomObject]@{ Name = "Guest Service Interface"; Enabled = $true },
                    [PSCustomObject]@{ Name = "Heartbeat"; Enabled = $true },
                    [PSCustomObject]@{ Name = "Key-Value Pair Exchange"; Enabled = $true },
                    [PSCustomObject]@{ Name = "Shutdown"; Enabled = $true },
                    [PSCustomObject]@{ Name = "Time Synchronization"; Enabled = $false },
                    [PSCustomObject]@{ Name = "VSS"; Enabled = $true }
                )

                Mock Get-VMIntegrationService { $intServices }

                $output = Get-VMISInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "guest.tools.number 6"
                $output | Should -Contain "guest.tools.service.Guest_Service_Interface active"
                $output | Should -Contain "guest.tools.service.Heartbeat active"
                $output | Should -Contain "guest.tools.service.Key-Value_Pair_Exchange active"
                $output | Should -Contain "guest.tools.service.Shutdown active"
                $output | Should -Contain "guest.tools.service.Time_Synchronization inactive"
                $output | Should -Contain "guest.tools.service.VSS active"
            }
        }

        Context "When VM has no integration services" {
            It "Outputs zero integration services" {
                $vm = [PSCustomObject]@{ Name = "TestVM" }
                $clusterNode = "Node1"
                $intServices = @()

                Mock Get-VMIntegrationService { $intServices }

                $output = Get-VMISInfo -vm $vm -clusterNode $clusterNode

                $output | Should -Contain "guest.tools.number 0"
            }
        }
    }

    Describe "Get-VMKVPdata" {

        Context "When KVP attribute exists" {
            It "Returns the correct KVP value" {
                $vm = "TestVM"
                $clusterNode = "Node1"
                $kvpAttribute = "OSName"
                $expectedValue = "Windows Server 2022"

                $xml = @"
                            <INSTANCE>
                                <PROPERTY NAME='Name'>
                                    <VALUE>$kvpAttribute</VALUE>
                                </PROPERTY>
                                <PROPERTY NAME='Data'>
                                    <VALUE>$expectedValue</VALUE>
                                </PROPERTY>
                            </INSTANCE>
"@
                $mockKvpComponent = [PSCustomObject]@{
                    GuestIntrinsicExchangeItems = @($xml)
                }
                $mockVMWMI = New-Object PSObject
                $mockVMWMI | Add-Member -MemberType ScriptMethod -Name GetRelated -Value { param($class) $mockKvpComponent }

                Mock Get-WmiObject { $mockVMWMI }

                $result = Get-VMKVPdata -vm $vm -clusterNode $clusterNode -kvpAttribute $kvpAttribute

                $result | Should -Be $expectedValue
            }
        }

        Context "When KVP attribute does not exist" {
            It "Returns null" {
                $vm = "TestVM"
                $clusterNode = "Node1"
                $kvpAttribute = "NonExistent"
                $xml = @"
                            <INSTANCE>
                                <PROPERTY NAME='Name'>
                                    <VALUE>OtherAttribute</VALUE>
                                </PROPERTY>
                                <PROPERTY NAME='Data'>
                                    <VALUE>SomeValue</VALUE>
                                </PROPERTY>
                            </INSTANCE>
"@
                $mockKvpComponent = [PSCustomObject]@{
                    GuestIntrinsicExchangeItems = @($xml)
                }
                $mockVMWMI = New-Object PSObject
                $mockVMWMI | Add-Member -MemberType ScriptMethod -Name GetRelated -Value { param($class) $mockKvpComponent }


                Mock Get-WmiObject { $mockVMWMI }

                $result = Get-VMKVPdata -vm $vm -clusterNode $clusterNode -kvpAttribute $kvpAttribute
                $result | Should -Be $null
            }
        }

        Context "When WMI query throws an exception" {
            It "Returns null and does not throw" {
                $vm = "TestVM"
                $clusterNode = "Node1"
                $kvpAttribute = "OSName"

                Mock Get-WmiObject { throw "WMI error" }

                { Get-VMKVPdata -vm $vm -clusterNode $clusterNode -kvpAttribute $kvpAttribute } | Should -Not -Throw
                $result = Get-VMKVPdata -vm $vm -clusterNode $clusterNode -kvpAttribute $kvpAttribute
                $result | Should -Be $null
            }
        }
    }
}
