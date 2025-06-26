// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod keys {
    pub const ORACLE: &str = "oracle";
    pub const MAIN: &str = "main";

    pub const OPTIONS: &str = "options";
    pub const MAX_CONNECTIONS: &str = "max_connections";

    pub const AUTHENTICATION: &str = "authentication";
    pub const USERNAME: &str = "username";
    pub const PASSWORD: &str = "password";
    pub const TYPE: &str = "type";
    pub const ROLE: &str = "role";
    pub const ACCESS_TOKEN: &str = "access_token";

    pub const CONNECTION: &str = "connection";
    pub const HOSTNAME: &str = "hostname";
    pub const INSTANCE: &str = "instance";
    pub const SERVICE_NAME: &str = "service_name";
    pub const SERVICE_TYPE: &str = "service_type";
    pub const PORT: &str = "port";
    pub const SOCKET: &str = "socket";
    pub const TIMEOUT: &str = "timeout";
    pub const CA: &str = "ca";
    pub const CLIENT_CERTIFICATE: &str = "client_certificate";
    pub const TRUST_SERVER_CERTIFICATE: &str = "trust_server_certificate";
    pub const ENGINE: &str = "engine";

    pub const SECTIONS: &str = "sections";
    pub const CACHE_AGE: &str = "cache_age";
    pub const IS_ASYNC: &str = "is_async";
    pub const DISABLED: &str = "disabled";
    pub const SEP: &str = "sep";

    pub const PIGGYBACK_HOST: &str = "piggyback_host";
    pub const DISCOVERY: &str = "discovery";
    pub const DETECT: &str = "detect";
    pub const INCLUDE: &str = "include";
    pub const EXCLUDE: &str = "exclude";

    pub const MODE: &str = "mode";

    pub const INSTANCES: &str = "instances";

    pub const SID: &str = "sid";
    pub const ALIAS: &str = "alias";
    pub const PIGGYBACK: &str = "piggyback";

    pub const CONFIGS: &str = "configs";
}

pub mod values {
    /// AuthType::Standard
    pub const STANDARD: &str = "standard";
    /// AuthType::Os
    pub const OS: &str = "os";
    /// AuthType::Kerberos
    pub const WALLET: &str = "wallet";

    /// AuthType::Role
    pub const SYS_DBA: &str = "sysdba";
    pub const SYS_OPER: &str = "sysoper";
    pub const SYS_BACKUP: &str = "sysbackup";
    pub const SYS_DG: &str = "sysdg";
    pub const SYS_KM: &str = "syskm";
    pub const SYS_ASM: &str = "sysasm";

    /// Mode::Port
    pub const PORT: &str = "port";
}

pub mod defaults {
    use super::values;
    pub const MAX_CONNECTIONS: u32 = 6;
    pub const MAX_QUERIES: u32 = 64;

    pub const AUTH_TYPE: &str = values::OS;
    pub const MODE: &str = values::PORT;
    pub const CONNECTION_HOST_NAME: &str = "localhost";

    pub const INSTANCE_NAME: &str = "XE";
    pub const CONNECTION_PORT: u16 = 1521;
    pub const CONNECTION_TIMEOUT: u64 = 5;
    pub const SECTIONS_CACHE_AGE: u32 = 600;
    pub const SECTIONS_ALWAYS: &[&str] = &[
        "instance",
        "databases",
        "counters",
        "blocked_sessions",
        "transactionlogs",
        "clusters",
        "mirroring",
        "availability_groups",
        "connections",
    ];
    pub const SECTIONS_CACHED: &[&str] = &["tablespaces", "datafiles", "backup", "jobs"];

    pub const DISCOVERY_DETECT: bool = true;

    pub const TRUST_SERVER_CERTIFICATE: bool = true;
    pub const DEFAULT_SEP: char = ' ';
}
