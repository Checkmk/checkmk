// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

/// query MS SQL for installed instances
pub const INSTANCES_BASE_START: &str = r"
DECLARE @GetInstances TABLE
    ( Value nvarchar(100),
     InstanceNames nvarchar(100),
     Data nvarchar(100))
Insert into @GetInstances
EXECUTE xp_regread
      @rootkey = 'HKEY_LOCAL_MACHINE',
      @key = 'SOFTWARE\Microsoft\Microsoft SQL Server',
      @value_name = 'InstalledInstances'
Insert into @GetInstances
EXECUTE xp_regread
      @rootkey = 'HKEY_LOCAL_MACHINE',
      @key = 'SOFTWARE\Wow6432Node\Microsoft\Microsoft SQL Server',
      @value_name = 'InstalledInstances'
Select InstanceNames from @GetInstances
";

pub const SYS_DATABASES: &str = "SELECT name FROM sys.databases";
