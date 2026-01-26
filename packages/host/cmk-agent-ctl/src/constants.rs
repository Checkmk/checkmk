// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const VERSION: &str = "2.4.0p21";

// CONFIGURATION
pub const DEFAULT_PULL_PORT: u16 = 6556;
pub const MAX_CONNECTIONS: usize = 3;
pub const CONNECTION_TIMEOUT: u64 = 20;
pub const CERT_VALIDITY_LOWER_LIMIT: u64 = 3888000; // 45 days = 45*24*60*60
pub const CERT_VALIDITY_UPPER_LIMIT: u64 = 15768000000; // approx. 500 years = 500*365*24*60*60
pub const CERT_RSA_KEY_SIZE: u32 = 4096;
#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
#[cfg(unix)]
pub const UNIX_AGENT_SOCKET: &str = "/run/check-mk-agent.socket";

// FILES
pub const PRE_CONFIGURED_CONNECTIONS_FILE: &str = "pre_configured_connections.json";
pub const REGISTRY_FILE: &str = "registered_connections.json";
pub const CONFIG_FILE: &str = "cmk-agent-ctl.toml";

// ENVIRONMENT
#[cfg(windows)]
pub const ENV_AGENT_LOG_DIR: &str = "MK_LOGDIR";
#[cfg(windows)]
pub const ENV_LOG_TO_FILE: &str = "CMK_AGENT_CTL_LOG_TO_FILE";

// DIRS
#[cfg(windows)]
pub const WIN_AGENT_HOME_DIR: &str = "\\checkmk\\agent";

// ENV VARS
pub const ENV_HOME_DIR: &str = "DEBUG_HOME_DIR";
pub const ENV_MAX_CONNECTIONS: &str = "DEBUG_MAX_CONNECTIONS";
pub const ENV_CONNECTION_TIMEOUT: &str = "DEBUG_CONNECTION_TIMEOUT";
#[cfg(windows)]
pub const ENV_PROGRAM_DATA: &str = "ProgramData";

// Windows version
// https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
// We support only relative new version of Windows because of Rust toolchain:
// Server 2008 R2 & Windows 7, i.e. 6.1
#[cfg(windows)]
pub const MIN_WIN_VERSION_MAJOR: u64 = 6;
#[cfg(windows)]
pub const MIN_WIN_VERSION_MINOR: u64 = 1;

// Log Rotation default parameters
#[cfg(windows)]
pub mod log {
    use flexi_logger::{Cleanup, Criterion, Naming};
    pub const FILE_MAX_SIZE: Criterion = Criterion::Size(500000);
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_CLEANUP: Cleanup = Cleanup::KeepLogFiles(5);
}

// CA
#[cfg(test)]
pub const TEST_ROOT_CERT: &str = "-----BEGIN CERTIFICATE-----\nMIIDFTCCAf2gAwIBAgIUaDlr/3eN2SmBMlpmW9cICSVzcEwwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzEw\nMTQyNVoYDzMwMjAxMDE0MTAxNDI1WjAgMR4wHAYDVQQDDBVTaXRlICdoZXV0ZScg\nbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDwvHoHuD6E\naQNpEaznTKd/6M/jkiopZ8It+zSEi93zBwu2ZsJlv8Kl1KkWim0s6o/YuQx//USQ\nfVR3lAazRr2k4xxwbThzXh+0S2dp5RWRBZCuJElwQ+u+PVmVsq/Zusj+YVl1Jo3F\nZ5xGUwjS+G9+ZElDnGpDi0NG5GNoozE5L0EEnQArsC+V7MoTUKebN+x9zlcc7bPb\nfphcwLrA/IGuJe7Ab6oLbEm/pA3X1LxyY98/pBoUeVXlEjJMo/8SrW+1Y02GyHCJ\nysVWC2+PwFdm4GXMsZVFMy/FE5lElwjgLHiTUDdytClP3yKHvyeJD3E1pw8Dm7QP\nxb9kCOCslRm3AgMBAAGjRTBDMB0GA1UdDgQWBBSyZwy7Z0SxqhbyXTilbcnJJNGP\nkTASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjANBgkqhkiG9w0B\nAQsFAAOCAQEA0zbSOS+9QgB3VcBkiRY5/ZGv+l+MCRoxeBm6rsj76dJyu5KYAEvW\nFg0zzg0xdgFMqcd1WBwVP4w1mqmvLXW0+C899F8GNsP089PfRg1qIzbLKP6P/CNv\nUowHzTqEnI0IDcD1RnuJj+Q4Ao04unFSllTO/OWu+wbfqiNKf/RHdiVs91KWS7XU\nFgG5s3A5p91N1JfDboWk/pQDHQihhjxgaOlfjWp8b0KxShMgnRdxTkqbS/APN/9f\nhcmq7hQrXVq2VUknRzrrlv2wBNn83aqFpw54Gnjor91EUbsB0gXWj6Ki/afvyAwi\ndt+OCdh9sbgEVsdwDYowscUHKcmGI3qoGg==\n-----END CERTIFICATE-----\n";
// standard site certificate signed by CA
#[cfg(test)]
pub const TEST_CERT_OK: &str = "-----BEGIN CERTIFICATE-----\nMIIC4jCCAcqgAwIBAgIUToJSkbhbRwHjr/9Uu3FEoidwCWMwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzEw\nMTQyNVoYDzMwMjAxMDE0MTAxNDI1WjAQMQ4wDAYDVQQDDAVoZXV0ZTCCASIwDQYJ\nKoZIhvcNAQEBBQADggEPADCCAQoCggEBAL6Upc1udGIMPymBF8m+Z6PvQA/KPYF/\ne3g9gClSg73376XXdSqO9VkOR80lUM1mW2ZtK+ApF6/gDFaFmUPxThcq5PECgajd\nSug1sdC9GYfd6KQfAxseSR2x59UNYbG3Gt33+lurWHxCy61RL3sGW72CDoqqCGrK\n5hTbkOyNcaVrtXFSFE0N7cFFOK36MLuzopOFHNUeC1S/O0clUwA54kBAA37ARE5B\nfy2myp3A4YAMtD5dbva1WDJ1A9Hg+ivtjBxgrfTOdZF00/AB1vfzOZVktd14eBHZ\nXfmfEwndFmvYe7LsQ4/g9G5P4C1FXEqxcKyJg7EGDAtEZScbwU/6/PcCAwEAAaMi\nMCAwEAYDVR0RBAkwB4IFaGV1dGUwDAYDVR0TAQH/BAIwADANBgkqhkiG9w0BAQsF\nAAOCAQEAjvWil5wjCHz4dYj4Jbwn71/78J/1puX5Uzq2qVp7/UlVGLXeTYYgw9Ax\nH+cbO5Hf7gb7X1pwmjktMru7Utds4RAoQCvHLcJn1rQ0sQAgSN/Piq97ToQfD65+\nfsA5WAQBnlWRgiUhx5YR54La5mRrWbPOUnBddiEt/AOM5emNUEMNLYn0eGG/5cKi\nqC+ygO8KKmhVakFiXOtZjOf2w4DEl+rtEbIXmfGR3MD7oRoEWlfvYkz/mh5TstYr\nLupAH+jnrHlYGSw7tbR2X1LdSykBZgro7SPPSsWyqNxDCIckZbQ0ahYxNO1oCvs0\nPZWBjnJQjlaJVG1iIQBJS8UaZ+hJ5A==\n-----END CERTIFICATE-----\n";
// certificate signed by CA where CN is a valid UUID
#[cfg(test)]
pub const TEST_CERT_CN_UUID: &str = "-----BEGIN CERTIFICATE-----\nMIIDIDCCAgigAwIBAgIUSXJpdJHE2CUaq0x0zO2EEEngX9cwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzE3\nMTA0NloYDzMwMjAxMDE0MTcxMDQ2WjAvMS0wKwYDVQQDDCRjZjc3MWVlYi1iNjY2\nLTQ2NzMtOTVjOS02ODM5NjBmYjI5MzkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw\nggEKAoIBAQCt9G35b5L3/K9AfaFLNGxS46yvbm2rd9FvzbOUospGsvHpN/cHiF8V\nV/fryGhtXWMzns0bB93gxEHd8qs8kvWuBg8FLYkn+H1XEiw7E7Ce80rrq61gaHDt\n3DCi6XID0a3gSQ7LQc2rWQ+Wpg0DjtyNFFXbUI0LV/YKWG6tfWXEFOy4tFUYbCW+\nz/kGshpjzYiK4aVCrYL54U4TAoUp8xvggOo4IXf04QABy7QWpmEDSRajhRtLkmcN\nx4HJ9/fKz7u6mymh4gI62kQWhxXtcVw+54dklp2Xt0ucbALp6T0XdaYFHWUTR1Yq\nSNLIcf79CRzf61vJjHQWVHoulXNpPNZVAgMBAAGjQTA/MC8GA1UdEQQoMCaCJGNm\nNzcxZWViLWI2NjYtNDY3My05NWM5LTY4Mzk2MGZiMjkzOTAMBgNVHRMBAf8EAjAA\nMA0GCSqGSIb3DQEBCwUAA4IBAQDo5JIsjXYAE11w9y1T7d+LzRj6HT7FYt1NLyHm\nMsZJh2y+gExd+k/E6Dlv494PW2/AX/prVG+UsBw+B0aDnrEm32BO3/ottwrdeL9b\nRmX1SQru89UgmfCsbgVpl66P7UGzltI/2vIyWzkcbcwMWP8UA1qAfPoMqnvGAMgu\n+bARCGaTWDT8uO6OCJm4JKMLXLk32kPL54Nd/Pp3lGrwWFOMFnjSbGtiAY2u9UeV\n+3uaganYjbLZkCQ0DP+DKDl6NBz3mrzI5wc+Fcpz8uDNV+UbtrGzreseBulJDLcl\ncr3aR+ZPgQPJDdVD56jXrdlU6hemc58NHJ+cPbw2ISaU9Rop\n-----END CERTIFICATE-----\n";
// certificate signed by a different CA
#[cfg(test)]
pub const TEST_CERT_INVALID_SIGNATURE: &str = "-----BEGIN CERTIFICATE-----\nMIIC3zCCAcegAwIBAgIUdRy8we2If2wSVioU+nu1420ZD4UwDQYJKoZIhvcNAQEL\nBQAwHzEdMBsGA1UEAwwUU2l0ZSAndGVtcCcgbG9jYWwgQ0EwIBcNMjIwNjEzMTcx\nNzUyWhgPMzAyMDEwMTQxNzE3NTJaMA8xDTALBgNVBAMMBHRlbXAwggEiMA0GCSqG\nSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDZMYl6ZTgmeonGMLizBNtAJNrH8O4rOvV3\nX8EvnWOmM26RCixGwy9MVteOlIptcZUa8QHo1EZ58T+1aS5G01LRtkx9OPK0bvPD\n4nnUGwIeUt12W5tHFH8DKpivl9oql/kJYzPTzGjsjeNXfPHGVUXVvq3pmL3U7d0o\nrC7s30fmRH0M0CArNykuJ9OO6kA52pplQmTbXRCceKTwtN7w0tWh7YYuw2343Rd/\nDQh8XvUduLWiMqkb0PC7otvgkQHFV6GylrE+FAxRvIY+2aqaUBziPHR+JU7Uxkpq\nYblNbOWRT3wjtxjBt0iYRrsMvhD8eD9T4sP51EZNk1S9jo2+PXDvAgMBAAGjITAf\nMA8GA1UdEQQIMAaCBHRlbXAwDAYDVR0TAQH/BAIwADANBgkqhkiG9w0BAQsFAAOC\nAQEASBTxFm2BQGQmmfwdouXT/nf071r5PCbr8Bj9AxKAzCiuJ/G8QBhwtTC01HmR\nL5vA1yi1Iiqm3wZTSetuNYQdi30HHDvJlHE3ADnKa1fo4vJFZTb4v+oKF8DUnaML\npmTkaldJuy3Ksl0tgeJlv6eM9/Rx47/XHMeD+0m72vKte13wBmMac18UNT/FNqM5\nM4H8Qvdxxbjfa/907ZPYnXg1baimqmNHvoELQzJNl8fza7fnDRRBn9XCSJoWiAcx\nu3ebRbIdPL3/BVQYHzBJV11zq4RN1IujYjRRTGWFr+zEVuuKmnbNK6hNAe8zwfLN\nJ7+UOWbsApe3/LIGhGJfGxtD+A==\n-----END CERTIFICATE-----\n";
