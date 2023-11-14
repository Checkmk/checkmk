// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const QUERY_COMPUTER_NAME: &str = r"DECLARE @ComputerName NVARCHAR(200);
DECLARE @main_key NVARCHAR(200) = 'SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName';
EXECUTE xp_regread
    @rootkey = 'HKEY_LOCAL_MACHINE',
    @key = @main_key,
    @value_name = 'ComputerName',
    @value = @ComputerName OUTPUT;
  Select @ComputerName as 'ComputerName'
";

/// Script to be run in SQL instance
const QUERY_ALL_BASE: &str = r"
DECLARE @GetInstances TABLE
( Value nvarchar(100),
 InstanceNames nvarchar(100),
 Data nvarchar(100))

DECLARE @GetAll TABLE
( Value nvarchar(100),
 InstanceNames nvarchar(100),
 InstanceIds nvarchar(100),
 EditionNames nvarchar(100),
 VersionNames nvarchar(100),
 ClusterNames nvarchar(100),
 Ports nvarchar(100),
 DynamicPorts nvarchar(100),
 Data nvarchar(100))

Insert into @GetInstances
EXECUTE xp_regread
  @rootkey = 'HKEY_LOCAL_MACHINE',
  @key = 'SOFTWARE\Microsoft\Microsoft SQL Server',
  @value_name = 'InstalledInstances'

DECLARE @InstanceName NVARCHAR(100);

-- Cursor to iterate through the instance names
DECLARE instance_cursor CURSOR FOR
SELECT InstanceNames FROM @GetInstances;

OPEN instance_cursor;

-- Loop through all instances
FETCH NEXT FROM instance_cursor INTO @InstanceName;

WHILE @@FETCH_STATUS = 0
BEGIN
    DECLARE @InstanceId NVARCHAR(100);
    DECLARE @main_key NVARCHAR(200) = 'SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL';
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @main_key,
        @value_name = @InstanceName,
        @value = @InstanceId OUTPUT;

    -- You'll need to construct the key path using the instance name
    DECLARE @setup_key NVARCHAR(200) = 'SOFTWARE\Microsoft\Microsoft SQL Server\' + @InstanceId + '\Setup';
    DECLARE @cluster_key NVARCHAR(200) = 'SOFTWARE\Microsoft\Microsoft SQL Server\' + @InstanceId + '\Cluster';
    DECLARE @port_key NVARCHAR(200) = 'SOFTWARE\Microsoft\Microsoft SQL Server\' + @InstanceId + '\MSSQLServer\SuperSocketNetLib\TCP\IPAll';

    DECLARE @Edition NVARCHAR(100);
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @setup_key,
        @value_name = 'Edition',
        @value = @Edition OUTPUT;

    DECLARE @Version NVARCHAR(100);
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @setup_key,
        @value_name = 'Version',
        @value = @Version OUTPUT;

    DECLARE @ClusterName NVARCHAR(100);
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @cluster_key,
        @value_name = 'ClusterName',
        @value = @ClusterName OUTPUT;

    DECLARE @Port NVARCHAR(100);
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @port_key,
        @value_name = 'tcpPort',
        @value = @Port OUTPUT;

    DECLARE @DynamicPort NVARCHAR(100);
    EXECUTE xp_regread
        @rootkey = 'HKEY_LOCAL_MACHINE',
        @key = @port_key,
        @value_name = 'TcpDynamicPorts',
        @value = @DynamicPort OUTPUT;
    
    insert into @GetAll(InstanceNames, InstanceIds, EditionNames, VersionNames, ClusterNames, Ports, DynamicPorts) Values( @InstanceName, @InstanceId, @Edition, @Version, @ClusterName, @Port, @DynamicPort )
    
    -- Get the next instance
    FETCH NEXT FROM instance_cursor INTO @InstanceName;
END

CLOSE instance_cursor;
DEALLOCATE instance_cursor;

SELECT InstanceNames, InstanceIds, EditionNames, VersionNames, ClusterNames,Ports, DynamicPorts FROM @GetAll;";

pub const SYS_DATABASES: &str = "SELECT name FROM sys.databases";

pub fn get_instances_query() -> String {
    QUERY_ALL_BASE.to_string()
}

pub fn get_32bit_instances_query() -> String {
    QUERY_ALL_BASE
        .to_string()
        .replace(r"SOFTWARE\Microsoft\", r"SOFTWARE\WOW6432Node\Microsoft\")
}
