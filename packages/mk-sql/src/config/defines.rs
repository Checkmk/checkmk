// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod keys {
    pub const MSSQL: &str = "mssql";
    pub const MAIN: &str = "main";

    pub const OPTIONS: &str = "options";
    pub const MAX_CONNECTIONS: &str = "max_connections";

    pub const AUTHENTICATION: &str = "authentication";
    pub const USERNAME: &str = "username";
    pub const PASSWORD: &str = "password";
    pub const TYPE: &str = "type";
    pub const ACCESS_TOKEN: &str = "access_token";

    pub const CONNECTION: &str = "connection";
    pub const HOSTNAME: &str = "hostname";
    pub const FORCE_LOCAL_HOST: &str = "force_local_host";
    pub const FAIL_OVER_PARTNER: &str = "failoverpartner";
    pub const TLS: &str = "tls";
    pub const PORT: &str = "port";
    pub const SOCKET: &str = "socket";
    pub const TIMEOUT: &str = "timeout";
    pub const CA: &str = "ca";
    pub const CLIENT_CERTIFICATE: &str = "client_certificate";
    pub const TRUST_SERVER_CERTIFICATE: &str = "trust_server_certificate";
    pub const BACKEND: &str = "backend";
    pub const EXCLUDE_DATABASES: &str = "exclude_databases";

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
    /// AuthType::System
    pub const SQL_SERVER: &str = "sql_server";
    /// AuthType::Windows
    #[cfg(windows)]
    pub const WINDOWS: &str = "windows";
    /// AuthType::Integrated
    #[cfg(windows)]
    pub const INTEGRATED: &str = "integrated";
    /// AuthType::Token
    pub const TOKEN: &str = "token";
    /// Mode::Port
    pub const PORT: &str = "port";
    /// Mode::Socket
    pub const SOCKET: &str = "socket";
    /// AuthType::Special
    pub const SPECIAL: &str = "special";
}

pub mod defaults {
    use super::values;
    pub const MAX_CONNECTIONS: u32 = 6;
    pub const MAX_QUERIES: u32 = 64;

    #[cfg(windows)]
    pub const AUTH_TYPE: &str = values::INTEGRATED;
    #[cfg(unix)]
    pub const AUTH_TYPE: &str = values::SQL_SERVER;
    pub const MODE: &str = values::PORT;
    pub const CONNECTION_HOST_NAME: &str = "localhost";
    pub const CONNECTION_PORT: u16 = 1433;
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
