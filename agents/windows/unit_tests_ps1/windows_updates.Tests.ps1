BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot "..\plugins\windows_updates.ps1"
    . $scriptPath
}

Describe "ReadFromRegistry" {
    Context "When registry key exists" {
        It "returns the registry value" {
            Mock Get-ItemProperty { @{ '(default)' = 'test_value' } }
            ReadFromRegistry -RegistryKey "HKLM:\Test" -Default "default_val" | Should -Be "test_value"
        }
    }
    Context "When registry key does not exist" {
        It "returns the default value" {
            Mock Get-ItemProperty { throw "Not found" }
            ReadFromRegistry -RegistryKey "HKLM:\Test" -Default "default_val" | Should -Be "default_val"
        }
    }
}

Describe "ProcessSearchResult" {
    It "Outputs error when ResultCode is not 2" {
        $sr = [PSCustomObject]@{ ResultCode = 4; Updates = @() }
        $output = ProcessSearchResult -SearchResult $sr -RebootRequired $false -RebootTime "no_key"
        $output | Should -Contain "<<<windows_updates>>>"
        $output | Should -Contain "x x x"
        $output | Should -Contain "There was an error getting update information. Maybe Windows Update is not activated."
    }

    It "Outputs correct update info when updates are present" {
        $updates = @(
            [PSCustomObject]@{ AutoSelectOnWebSites = $true; Title = "Important1" },
            [PSCustomObject]@{ AutoSelectOnWebSites = $false; Title = "Optional1" },
            [PSCustomObject]@{ AutoSelectOnWebSites = $true; Title = "Important2" }
        )
        $sr = [PSCustomObject]@{ ResultCode = 2; Updates = $updates }
        $output = ProcessSearchResult -SearchResult $sr -RebootRequired $true -RebootTime "2024-01-01T00:00:00"
        $output | Should -Contain "<<<windows_updates>>>"
        $output | Should -Contain "True 2 1"
        $output | Should -Contain "Important1; Important2"
        $output | Should -Contain "Optional1"
        $output | Should -Contain "2024-01-01T00:00:00"
    }

    It "Handles no updates gracefully" {
        $sr = [PSCustomObject]@{ ResultCode = 2; Updates = @() }
        $output = ProcessSearchResult -SearchResult $sr -RebootRequired $false -RebootTime "no_key"
        $output | Should -Contain "<<<windows_updates>>>"
        $output | Should -Contain "False 0 0"
        $output | Should -Contain ""
        $output | Should -Contain "no_key"
    }
}
