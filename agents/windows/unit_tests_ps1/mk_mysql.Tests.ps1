BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot "..\plugins\mk_mysql.ps1"
    . $scriptPath
}
Context "mk_mysql.ps1 Tests" {

    Describe "ReplaceSqlExeForMysql Function" {
        It "Should replace <cmd> with <expected>" -ForEach @(
            @{
                cmd      = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80";
                expected = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80"
            }
            @{
                cmd      = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld-nt.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80";
                expected = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80"
            }
        ) {
            ReplaceSqlExeForMysql -cmd  $cmd | Should -Be $expected
        }
    }

    Describe "BuildPrintDefaultsCmd Function" {
        It "Should replace <instanceCmd> with <expected>" -ForEach @(
            @{
                instanceName = "MySQL80";
                instanceCmd  = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80"
                expected     = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" --print-defaults"
            }
            @{
                instanceName = "AnyMySQLName12356";
                instanceCmd  = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" AnyMySQLName12356"
                expected     = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" --print-defaults"
            }
        ) {
            BuildPrintDefaultsCmd -instanceName $instanceName -instanceCmd $instanceCmd | Should -Be $expected
        }
    }

    Describe "GetSqlExePathFromCmd Function" {
        It "Should replace <inputCmd> with <expected>" -ForEach @(
            @{
                inputCmd = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`" --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" MySQL80"
                expected = "`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`""
            }
            @{
                inputCmd = "C:\ProgramFiles\MySQL\MySQLServer8.0\bin\mysql.exe --defaults-file=`"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`" AnyMySQLName12356"
                expected = "C:\ProgramFiles\MySQL\MySQLServer8.0\bin\mysql.exe"
            }
        ) {
            GetSqlExePathFromCmd -inputCmd $inputCmd | Should -Be $expected
        }
    }

    Describe "InitCfgFile Function" {
        BeforeAll {
            Mock GetCfgDir { return "C:\ProgramData\checkmk\agent\config" }
        }
        It "Should return the empty config file path" {
            Mock Test-Path { return $false }

            $cfgFile = InitCfgFile "MySQL80"
            $cfgFile | Should -Be ""
        }

        It "Should return the correct config file path with instance" {
            Mock Test-Path { return $true }

            $cfgFile = InitCfgFile "MySQL80"
            $cfgFile | Should -Be "C:\ProgramData\checkmk\agent\config\mysql_MySQL80.ini"
        }
    }

    Describe "CreateMysqlLocalIni Function" {
        BeforeAll {
            Mock GetCfgDir { return "C:\ProgramData\checkmk\agent\config" }
            Mock Test-Path { return $false }
            Mock Set-Content { return }
        }
        It "Should invoke file creation command once" {
            CreateMysqlLocalIni
            Should -Invoke Set-Content -Times 1
        }
    }

    Describe "GetConnectionArgsForTheInstance Function" {
        BeforeAll {
            Mock Run {
                $output = @(
                    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe would have been started with the following arguments:",
                    "--port=3306 --no-beep")
                return $output
            }
        }
        It "Should return the correct connection arguments" {
            $result = GetConnectionArgsForTheInstance "" "" # empty args because we mock output str
            $result | Should -Be "--port=3306"
        }
    }
}
