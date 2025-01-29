# How to get certificates for testing MS SQL Server

## Setup

1. Install certificate

    either from real certificate
[msdn docu](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/configure-sql-server-encryption?view=sql-server-ver16#computers-with-sql-server-configuration-manager-for-sql-server-2017-and-earlier) positions 1..7

    or using next powershell command
```powershell
New-SelfSignedCertificate -Type SSLServerAuthentication -Subject "CN=$env:COMPUTERNAME" `
-DnsName ("{0}" -f [System.Net.Dns]::GetHostByName($env:computerName).HostName),'localhost' `
-KeyAlgorithm "RSA" -KeyLength 2048 -HashAlgorithm "SHA256" -TextExtension "2.5.29.37={text}1.3.6.1.5.5.7.3.1" `
-NotAfter (Get-Date).AddMonths(36) -KeySpec KeyExchange -Provider "Microsoft RSA SChannel Cryptographic Provider" `
-CertStoreLocation "cert:\LocalMachine\My"
```

2. In SQL Server Configuration Manager set certificate from p.1

In the MMC console, right-click the imported certificate, point to All Tasks, and select Manage Private Keys. In the Security dialog box, add read permission for the user account used by the SQL Server service account.

In SQL Server Configuration Manager, expand SQL Server Network Configuration, right-click Protocols for "server instance", and select Properties.

In the Protocols for "instance name" Properties dialog box, on the Certificate tab, select the desired certificate from the drop-down for the Certificate box, and then select OK.

3. Export certificate from p.2 in DER format and change extension to der.

You may use file from p.3 as CA certificate

## Testing on CI and or locally

You may use `CI_TEST_MS_SQL_DB_CERT` environment variable to store path to certificate
Fort example on Windows:
```batch
setx CI_TEST_MS_SQL_DB_CERT c:\common\checkmk\certificates\mssql-YOUR-MACHINE-NAME.der
```
Testing code is looks like
```rust 
        pub const MS_SQL_DB_CERT: &str = "CI_TEST_MS_SQL_DB_CERT";
        if let Ok(certificate_path) = std::env::var(MS_SQL_DB_CERT) {
            create_local(1433u16, certificate_path.to_owned().into())
                .await
                .unwrap();
        } else {
            eprintln!("Error: environment variable {} is absent no testing", MS_SQL_DB_CERT);
        }
```
