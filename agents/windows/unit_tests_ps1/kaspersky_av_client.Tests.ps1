BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot "..\plugins\kaspersky_av_client.ps1"
    . $scriptPath
}

Describe "StrDateTimeToCheckmkFormat" {
    It "Converts valid Kaspersky UTC date string to local checkmk format" {
        $utcString = "02-02-2024 13-30-00"
        $expected = (Get-Date "2024-02-02T13:30:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
        $result = StrDateTimeToCheckmkFormat $utcString
        $result | Should -Be $expected
    }
    It "Outputs Error parsing date on invalid date string" {
        $result = StrDateTimeToCheckmkFormat "not-a-date"
        ($result  | Where-Object { $_ -match "Error parsing date:.*" }) | Should -Not -BeNullOrEmpty
    }
}

Describe "GetKasperskyRegistryDateValue" {
    It "Returns key value when present" {
        Mock Get-ItemPropertyValue { param($Path, $Name) "value" }
        $result = GetKasperskyRegistryDateValue "dummy" "dummy"
        $result | Should -Be "value"
    }

    It "Returns null when value is missing" {
        Mock Get-ItemPropertyValue { param($Path, $Name) $null }
        $result = GetKasperskyRegistryDateValue "dummy" "dummy"
        $result | Should -Be $null
    }

    It "Returns null when value is empty string" {
        Mock Get-ItemPropertyValue { param($Path, $Name) "" }
        $result = GetKasperskyRegistryDateValue "dummy" "dummy"
        $result | Should -Be $null
    }
}

Describe "GetKasperskyFullscanStatus" {
    It "Returns formatted Fullscan date" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) "03-03-2024 15-00-00" }
        $expected = (Get-Date "2024-03-03T15:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
        $result = GetKasperskyFullscanStatus "dummy"
        $result | Should -Be "Fullscan $expected"
    }

    It "Returns 'Fullscan Missing' when value is missing" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) $null }
        $result = GetKasperskyFullscanStatus "dummy"
        $result | Should -Be "Fullscan Missing"
    }

    It "Returns error message when value is not a valid date" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) "not-a-date" }
        $result = GetKasperskyFullscanStatus "dummy"
        $result | Should -Match "Fullscan Error parsing date:.*"
    }
}

Describe "GetKasperskySignatureStatus" {
    It "Returns formatted Signatures date" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) "04-04-2024 16-00-00" }
        $expected = (Get-Date "2024-04-04T16:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
        $result = GetKasperskySignatureStatus "dummy"
        $result | Should -Be "Signatures $expected"
    }
    It "Returns 'Signatures Missing' when value is missing" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) $null }
        $result = GetKasperskySignatureStatus "dummy"
        $result | Should -Be "Signatures Missing"
    }

    It "Returns error message when value is not a valid date" {
        Mock GetKasperskyRegistryDateValue { param($Path, $Name) "not-a-date" }
        $result = GetKasperskySignatureStatus "dummy"
        $result | Should -Match "Signatures Error parsing date:.*"
    }
}

Describe "GetKasperskyAvClientStatus" {
    Context "All registry values present" {
        It "Outputs all expected lines with formatted dates" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "05-05-2024 17-00-00" }
                    "Protection_BasesDate" { "05-05-2024 18-00-00" }
                    "Protection_LastFscan" { "05-05-2024 19-00-00" }
                }
            }
            $expectedBases = (Get-Date "2024-05-05T18:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            $expectedFscan = (Get-Date "2024-05-05T19:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "<<<kaspersky_av_client>>>"
            $output | Should -Contain "Signatures $expectedBases"
            $output | Should -Contain "Fullscan $expectedFscan"
        }
    }

    Context "When GetKasperskySignatureStatus throws" {
        It "Outputs error message" {
            Mock GetKasperskyRegistryDateValue {
                if ($Name -eq "Protection_LastConnected") { return "01-01-2024 12-00-00" }
                if ($Name -eq "Protection_BasesDate") { throw "Registry error" }
                if ($Name -eq "Protection_LastFscan") { return "01-01-2024 12-00-00" }
            }
            Mock StrDateTimeToCheckmkFormat { return "01.01.2024 13:00:00" }

            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "<<<kaspersky_av_client>>>"
            $output | Should -Contain "GetKasperskySignatureStatus Error: Registry error"
        }
    }

    Context "When GetKasperskyFullscanStatus throws" {
        It "Outputs error message" {
            Mock GetKasperskyRegistryDateValue {
                if ($Name -eq "Protection_LastConnected") { return "01-01-2024 12-00-00" }
                if ($Name -eq "Protection_BasesDate") { return "01-01-2024 12-00-00" }
                if ($Name -eq "Protection_LastFscan") { throw "Registry error" }
            }
            Mock StrDateTimeToCheckmkFormat { return "01.01.2024 13:00:00" }

            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "<<<kaspersky_av_client>>>"
            $output | Should -Contain "GetKasperskyFullscanStatus Error: Registry error"
        }
    }

    Context "Signatures missing" {
        It "Outputs 'Signatures Missing' and formatted Fullscan" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "06-06-2024 10-00-00" }
                    "Protection_BasesDate" { $null }
                    "Protection_LastFscan" { "06-06-2024 11-00-00" }
                }
            }
            $expectedFscan = (Get-Date "2024-06-06T11:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "Signatures Missing"
            $output | Should -Contain "Fullscan $expectedFscan"
        }
    }

    Context "Fullscan missing" {
        It "Outputs formatted Signatures and 'Fullscan Missing'" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "07-07-2024 12-00-00" }
                    "Protection_BasesDate" { "07-07-2024 13-00-00" }
                    "Protection_LastFscan" { $null }
                }
            }
            $expectedBases = (Get-Date "2024-07-07T13:00:00Z").ToLocalTime().ToString("dd.MM.yyyy HH:mm:ss")
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "Signatures $expectedBases"
            $output | Should -Contain "Fullscan Missing"
        }
    }

    Context "Kaspersky client not installed" {
        It "Outputs nothing (all output commented out in else branch)" {
            Mock GetKasperskyRegistryDateValue { param($Path, $Name) $null }
            $output = GetKasperskyAvClientStatus
            $output | Should -BeNullOrEmpty
        }
    }

    Context "Protection_LastConnected present but both other values missing" {
        It "Outputs 'Signatures Missing' and 'Fullscan Missing'" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "08-08-2024 14-00-00" }
                    "Protection_BasesDate" { $null }
                    "Protection_LastFscan" { $null }
                }
            }
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "Signatures Missing"
            $output | Should -Contain "Fullscan Missing"
        }
    }

    Context "Protection_LastConnected present, Protection_BasesDate invalid format" {
        It "Outputs GetKasperskySignatureStatus when Protection_BasesDate is invalid" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "09-09-2024 15-00-00" }
                    "Protection_BasesDate" { "not-a-date" }
                    "Protection_LastFscan" { "09-09-2024 16-00-00" }
                }
            }
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "<<<kaspersky_av_client>>>"
            ($output | Where-Object { $_ -match "Signatures Error parsing date:.*" }) | Should -Not -BeNullOrEmpty
            ($output | Where-Object { $_ -match "Fullscan 09.09.2024 .*" }) | Should -Not -BeNullOrEmpty
        }
    }

    Context "Protection_LastConnected present, Protection_LastFscan invalid format" {
        It "Outputs GetKasperskyFullscanStatus error when Protection_LastFscan is invalid" {
            Mock GetKasperskyRegistryDateValue {
                param($Path, $Name)
                switch ($Name) {
                    "Protection_LastConnected" { "10-10-2024 17-00-00" }
                    "Protection_BasesDate" { "10-10-2024 18-00-00" }
                    "Protection_LastFscan" { "not-a-date" }
                }
            }
            $output = GetKasperskyAvClientStatus
            $output | Should -Contain "<<<kaspersky_av_client>>>"
            ($output | Where-Object { $_ -match "Signatures 10.10.2024.*" }) | Should -Not -BeNullOrEmpty
            ($output | Where-Object { $_ -match "Fullscan Error parsing date:.*" }) | Should -Not -BeNullOrEmpty
        }
    }
}
