// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use lazy_static::lazy_static;

const DECLARE_INSTANCES_VAR: &str = r"
DECLARE @GetInstances TABLE
    ( Value nvarchar(100),
     InstanceNames nvarchar(100),
     Data nvarchar(100))
";

const SELECT_INSTANCES_EXEC: &str = r"
Select InstanceNames from @GetInstances
";

/// query MS SQL for installed 64 bit instances
const INSERT_64BIT_INSTANCES: &str = r"
Insert into @GetInstances
EXECUTE xp_regread
      @rootkey = 'HKEY_LOCAL_MACHINE',
      @key = 'SOFTWARE\Microsoft\Microsoft SQL Server',
      @value_name = 'InstalledInstances'
";

/// query MS SQL for installed 32 bit instances
const INSERT_32BIT_INSTANCES: &str = r"
Insert into @GetInstances
EXECUTE xp_regread
      @rootkey = 'HKEY_LOCAL_MACHINE',
      @key = 'SOFTWARE\Wow6432Node\Microsoft\Microsoft SQL Server',
      @value_name = 'InstalledInstances'
";

pub const SYS_DATABASES: &str = "SELECT name FROM sys.databases";

lazy_static! {
    pub static ref QUERY_64BIT_INSTANCES: String = format!(
        "{}{}{}",
        DECLARE_INSTANCES_VAR, INSERT_64BIT_INSTANCES, SELECT_INSTANCES_EXEC
    );
    pub static ref QUERY_32BIT_INSTANCES: String = format!(
        "{}{}{}",
        DECLARE_INSTANCES_VAR, INSERT_32BIT_INSTANCES, SELECT_INSTANCES_EXEC
    );
}
