// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use std::borrow::Borrow;
use std::collections::HashMap;

pub const UTC_DATE_FIELD: &str = "utc_date";

#[derive(Hash, PartialEq, Eq, Debug, Copy, Clone)]
pub enum Id {
    ComputerName,
    Mirroring,
    Jobs,
    AvailabilityGroups,
    InstanceProperties,
    UtcEntry,
    ClusterActiveNodes,
    ClusterNodes,
    IsClustered,
    DatabaseNames,
    Databases,
    Datafiles,
    Backup,
    TableSpaces,
    CounterEntries,
    Connections,
    TransactionLogs,
    BadQuery,
    WaitingTasks,
    BlockedSessions,
    Counters,
    Clusters,
}

pub mod query {
    pub const COMPUTER_NAME: &str =
        "SELECT Upper(Cast(SERVERPROPERTY( 'MachineName' ) AS varchar)) AS MachineName";
    /// Script to be run in SQL instance
    pub const WINDOWS_REGISTRY_INSTANCES_BASE: &str = r#"
IF OBJECT_ID('xp_regread', 'X') IS NOT NULL
BEGIN
    DECLARE @GetInstances TABLE
    ( Value NVARCHAR(100),
    InstanceNames NVARCHAR(100),
    Data NVARCHAR(100))

    DECLARE @GetAll TABLE
    ( Value NVARCHAR(100),
    InstanceNames NVARCHAR(100),
    InstanceIds NVARCHAR(100),
    EditionNames NVARCHAR(100),
    VersionNames NVARCHAR(100),
    ClusterNames NVARCHAR(100),
    Ports NVARCHAR(100),
    DynamicPorts NVARCHAR(100),
    Data NVARCHAR(100))

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

    SELECT InstanceNames, InstanceIds, EditionNames, VersionNames, ClusterNames,Ports, DynamicPorts FROM @GetAll
END"#;

    pub const UTC_ENTRY: &str = "SELECT CONVERT(NVARCHAR, GETUTCDATE(), 20) AS utc_date";

    pub const COUNTERS_ENTRIES_NORMAL: &str = r"
        SELECT CAST(counter_name AS NVARCHAR(100)) AS counter_name,
                CAST(object_name AS NVARCHAR(100)) AS object_name,
                CAST(instance_name AS NVARCHAR(100)) AS instance_name,
                cntr_value
     FROM sys.dm_os_performance_counters WHERE object_name NOT LIKE '%Deprecated%'";

    pub const COUNTERS_ENTRIES_AZURE: &str = r"
SELECT CAST(counter_name AS NVARCHAR(100)) AS counter_name,
       CAST((CASE
               WHEN object_name like 'MSSQL$%:%' THEN
                    UPPER(CAST(SERVERPROPERTY('ServerName') AS NVARCHAR)) +
                    SUBSTRING(object_name, CHARINDEX(':', object_name), len(object_name))
                 ELSE object_name
             END) as NVARCHAR(100)) as object_name,
       CAST(instance_name as NVARCHAR(100)) as instance_name,
       cntr_value
FROM sys.dm_os_performance_counters
WHERE object_name NOT LIKE '%Deprecated%'
";

    /// used only for testing: it is difficult to get blocked tasks in reality
    pub const WAITING_TASKS: &str = r"SELECT CAST(session_id AS varchar) AS session_id,
            CAST(wait_duration_ms AS bigint) AS wait_duration_ms,
            wait_type,
            CAST(blocking_session_id AS varchar) AS blocking_session_id
    FROM sys.dm_os_waiting_tasks";

    pub const DATABASE_NAMES: &str = "SELECT name FROM sys.databases";

    /// Executes `sp_spaceused` for each database parsing output AS resuult set
    /// Requires NVARCHAR support
    pub const SPACE_USED: &str = r#"
BEGIN TRY
    EXEC sp_spaceused
        WITH RESULT SETS (
            (database_name NVARCHAR(128),database_size NVARCHAR(128), "unallocated space" NVARCHAR(128)),
            (reserved NVARCHAR(128),data NVARCHAR(128), index_size NVARCHAR(128), unused NVARCHAR(128))
        )
END TRY
BEGIN CATCH
    EXEC sp_spaceused
END CATCH"#;

    pub const SPACE_USED_SIMPLE: &str = "EXEC sp_spaceused";

    pub const BACKUP: &str = r"
DECLARE @HADRStatus sql_variant;
DECLARE @SQLCommand NVARCHAR(MAX);
SET @HADRStatus = (SELECT SERVERPROPERTY ('IsHadrEnabled'));
IF (@HADRStatus IS NULL or @HADRStatus <> 1)
BEGIN
    SET @SQLCommand = '
    SELECT
      CONVERT(NVARCHAR, DATEADD(s, MAX(DATEDIFF(s, ''19700101'', backup_finish_date) - (CASE WHEN time_zone IS NOT NULL AND time_zone <> 127 THEN 60 * 15 * time_zone ELSE 0 END)), ''19700101''), 120) AS last_backup_date,
      CAST(type AS NVARCHAR(128)) AS type,
      CAST(machine_name AS NVARCHAR(128)) AS machine_name,
      CAST(''True'' AS NVARCHAR(12))as is_primary_replica,
      CAST(''1'' AS NVARCHAR(12)) AS is_local,
      CAST('''' AS NVARCHAR(12)) AS replica_id,
      CAST(sys.databases.name AS NVARCHAR(MAX)) AS database_name
    FROM
      msdb.dbo.backupset
      LEFT OUTER JOIN sys.databases ON CAST(sys.databases.name AS NVARCHAR(MAX)) = CAST(msdb.dbo.backupset.database_name AS NVARCHAR(MAX))
    WHERE
      UPPER(machine_name) = UPPER(CAST(SERVERPROPERTY(''Machinename'') AS NVARCHAR(MAX)))
    GROUP BY
      type,
      machine_name,
      CAST(sys.databases.name AS NVARCHAR(MAX))
    '
END
ELSE
BEGIN
    SET @SQLCommand = '
    SELECT
    CONVERT(NVARCHAR, DATEADD(s, MAX(DATEDIFF(s, ''19700101'', b.backup_finish_date) -
                     (CASE WHEN time_zone IS NOT NULL AND time_zone <> 127 THEN 60 * 15 * time_zone ELSE 0 END)), ''19700101''), 120)
                     AS last_backup_date,
      CAST(b.type AS NVARCHAR(MAX)) AS type,
      CAST(b.machine_name AS NVARCHAR(MAX)) AS machine_name,
      ISNULL(CONVERT(NVARCHAR(40), rep.is_primary_replica), '''') AS is_primary_replica,
      rep.is_local,
      ISNULL(CONVERT(NVARCHAR(40), rep.replica_id), '''') AS replica_id,
      CAST(db.name AS NVARCHAR(MAX)) AS database_name
    FROM
      msdb.dbo.backupset b
      LEFT OUTER JOIN sys.databases db ON CAST(b.database_name AS NVARCHAR(MAX)) = CAST(db.name AS NVARCHAR(MAX))
      LEFT OUTER JOIN sys.dm_hadr_database_replica_states rep ON db.database_id = rep.database_id
    WHERE
      (rep.is_local is null or rep.is_local = 1)
      AND (rep.is_primary_replica is null or rep.is_primary_replica = ''True'')
      AND UPPER(machine_name) = UPPER(CAST(SERVERPROPERTY(''Machinename'') AS NVARCHAR(120)))
    GROUP BY
      type,
      rep.replica_id,
      rep.is_primary_replica,
      rep.is_local,
      CAST(db.name AS NVARCHAR(MAX)),
      CAST(b.machine_name AS NVARCHAR(MAX)),
      rep.synchronization_state,
      rep.synchronization_health
    '
END
EXEC (@SQLCommand)
";

    //Script to create a table with 'unsupported' collation
    //master;
    //GO
    //IF DB_ID (N'MyOptionsTest') IS NOT NULL
    //    DROP DATABASE MyOptionsTest;
    //GO
    // CREATE DATABASE MyOptionsTest
    //    COLLATE SQL_Latin1_General_CP850_CI_AS; -- French_CI_AS;
    // GO
    //
    // SELECT name, collation_name
    // FROM sys.databases
    // WHERE name = N'MyOptionsTest';
    //

    /// NOTE: CAST( ... AS NVARCHAR) is a workaround gainst unsupported collations
    pub const TRANSACTION_LOGS: &str = r"SELECT name, physical_name,
  CAST(max_size/128 AS bigint) AS MaxSize,
  CAST(size/128 AS bigint) AS AllocatedSize,
  CAST(FILEPROPERTY (name, 'spaceused')/128 AS bigint) AS UsedSize,
  CAST(case when max_size = '-1' then '1' else '0' end AS NVARCHAR) AS Unlimited
 FROM sys.database_files WHERE type_desc = 'LOG'";

    /// NOTE: CAST( ... AS NVARCHAR) is a workaround gainst unsupported collations
    pub const DATAFILES: &str = r"SELECT name, physical_name,
  CAST(max_size/128 AS bigint) AS MaxSize,
  CAST(size/128 AS bigint) AS AllocatedSize,
  CAST(FILEPROPERTY (name, 'spaceused')/128 AS bigint) AS UsedSize,
  CAST(case when max_size = '-1' then '1' else '0' end  AS NVARCHAR) AS Unlimited
FROM sys.database_files WHERE type_desc = 'ROWS'";

    pub const DATABASES: &str = r"SELECT name,
  CAST(DATABASEPROPERTYEX(name, 'Status') AS NVARCHAR(MAX)) AS Status,
  CAST(DATABASEPROPERTYEX(name, 'Recovery') AS NVARCHAR(MAX)) AS Recovery,
  CAST(DATABASEPROPERTYEX(name, 'IsAutoClose') AS bigint) AS auto_close,
  CAST(DATABASEPROPERTYEX(name, 'IsAutoShrink') AS bigint) AS auto_shrink
FROM master.dbo.sysdatabases";

    pub const IS_CLUSTERED: &str =
        "SELECT CAST( SERVERPROPERTY('IsClustered') AS NVARCHAR(MAX)) AS is_clustered";

    pub const CLUSTER_NODES_NORMAL: &str =
        "SELECT CAST(nodename AS NVARCHAR(MAX)) AS nodename FROM sys.dm_os_cluster_nodes";

    pub const CLUSTER_NODES_AZURE: &str = r"
        IF OBJECT_ID('sys.dm_os_cluster_nodes') IS NOT NULL
            SELECT CAST(nodename AS NVARCHAR(MAX)) AS nodename FROM sys.dm_os_cluster_nodes
        ";

    pub const CLUSTER_ACTIVE_NODES: &str =
        "SELECT CAST(SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS NVARCHAR(MAX)) AS active_node";

    pub const CONNECTIONS: &str = r"SELECT name AS DbName,
      CAST((SELECT COUNT(dbid) AS Num_Of_Connections FROM sys.sysprocesses WHERE dbid > 0 AND name = DB_NAME(dbid) GROUP BY dbid ) AS bigint) AS NumberOfConnections 
FROM sys.databases";

    // TODO: check use msdb.dbo instead of dbo
    pub const JOBS: &str = r"
SELECT
  sj.job_id AS job_id,
  CAST(sj.name AS NVARCHAR(MAX)) AS job_name,
  sj.enabled AS job_enabled,
  CAST(sjs.next_run_date AS NVARCHAR(8)) AS next_run_date,
  CAST(sjs.next_run_time AS NVARCHAR(6)) AS next_run_time,
  sjserver.last_run_outcome,
  CAST(sjserver.last_outcome_message AS NVARCHAR(128)) AS last_outcome_message,
  CAST(sjserver.last_run_date AS NVARCHAR(8)) AS last_run_date,
  CAST(sjserver.last_run_time AS NVARCHAR(6)) AS last_run_time,
  sjserver.last_run_duration,
  ss.enabled AS schedule_enabled,
  CONVERT(NVARCHAR, CURRENT_TIMESTAMP, 20) AS server_current_time
FROM dbo.sysjobs sj
LEFT JOIN dbo.sysjobschedules sjs ON sj.job_id = sjs.job_id
LEFT JOIN dbo.sysjobservers sjserver ON sj.job_id = sjserver.job_id
LEFT JOIN dbo.sysschedules ss ON sjs.schedule_id = ss.schedule_id
ORDER BY job_name,
         next_run_date ASC,
         next_run_time ASC
";

    pub const MIRRORING_NORMAL: &str = r"SELECT @@SERVERNAME AS server_name,
  DB_NAME(database_id) AS [database_name],
  mirroring_state,
  mirroring_state_desc,
  mirroring_role,
  mirroring_role_desc,
  mirroring_safety_level,
  mirroring_safety_level_desc,
  mirroring_partner_name,
  mirroring_partner_instance,
  mirroring_witness_name,
  mirroring_witness_state,
  mirroring_witness_state_desc
FROM sys.database_mirroring
WHERE mirroring_state IS NOT NULL";

    pub const MIRRORING_AZURE: &str = r"
IF OBJECT_ID('sys.database_mirroring') IS NOT NULL
    SELECT @@SERVERNAME AS server_name,
      DB_NAME(database_id) AS [database_name],
      mirroring_state,
      mirroring_state_desc,
      mirroring_role,
      mirroring_role_desc,
      mirroring_safety_level,
      mirroring_safety_level_desc,
      mirroring_partner_name,
      mirroring_partner_instance,
      mirroring_witness_name,
      mirroring_witness_state,
      mirroring_witness_state_desc
    FROM sys.database_mirroring
    WHERE mirroring_state IS NOT NULL
";

    pub const AVAILABILITY_GROUP_NORMAL: &str = r"SELECT
  GroupsName.name,
  Groups.primary_replica,
  Groups.synchronization_health,
  Groups.synchronization_health_desc,
  Groups.primary_recovery_health_desc
FROM sys.dm_hadr_availability_group_states Groups
INNER JOIN master.sys.availability_groups GroupsName ON Groups.group_id = GroupsName.group_id";

    pub const AVAILABILITY_GROUP_AZURE: &str = r"
IF OBJECT_ID('sys.dm_hadr_availability_group_states') IS NOT NULL   
    SELECT
      GroupsName.name,
      Groups.primary_replica,
      Groups.synchronization_health,
      Groups.synchronization_health_desc,
      Groups.primary_recovery_health_desc
    FROM sys.dm_hadr_availability_group_states Groups
    INNER JOIN master.sys.availability_groups GroupsName ON Groups.group_id = GroupsName.group_id";

    pub const INSTANCE_PROPERTIES: &str = r"SELECT
    CAST(ISNULL(ISNULL(SERVERPROPERTY('InstanceName'), SERVERPROPERTY('FilestreamShareName')), SERVERPROPERTY('ServerName')) AS NVARCHAR(MAX)) AS InstanceName,
    CAST(SERVERPROPERTY( 'ProductVersion' ) AS NVARCHAR(MAX)) AS ProductVersion,
    CAST(SERVERPROPERTY( 'MachineName' ) AS NVARCHAR(MAX)) AS MachineName,
    CAST(SERVERPROPERTY( 'Edition' ) AS NVARCHAR(MAX)) AS Edition,
    CAST(SERVERPROPERTY( 'ProductLevel' ) AS NVARCHAR(MAX)) AS ProductLevel,
    CAST(SERVERPROPERTY( 'ComputerNamePhysicalNetBIOS' ) AS NVARCHAR(MAX)) AS NetBios";

    #[allow(dead_code)]
    pub const BAD_QUERY: &str = "SELEC name FROM sys.databases";
}

pub fn get_win_registry_instances_query() -> String {
    query::WINDOWS_REGISTRY_INSTANCES_BASE.to_string()
}

pub fn get_wow64_32_registry_instances_query() -> String {
    query::WINDOWS_REGISTRY_INSTANCES_BASE
        .to_string()
        .replace(r"SOFTWARE\Microsoft\", r"SOFTWARE\WOW6432Node\Microsoft\")
}
pub fn _get_blocking_sessions_query() -> String {
    format!("{} WHERE blocking_session_id <> 0 ", query::WAITING_TASKS).to_string()
}

lazy_static::lazy_static! {
    static ref BLOCKING_SESSIONS: String = format!("{} WHERE blocking_session_id <> 0 ", query::WAITING_TASKS).to_string();
    static ref COUNTERS_NORMAL: String = format!("{};{};", query::UTC_ENTRY, query::COUNTERS_ENTRIES_NORMAL  ).to_string();
    static ref CLUSTERS_NORMAL: String = format!("{};{};", query::CLUSTER_NODES_NORMAL, query::CLUSTER_ACTIVE_NODES  ).to_string();
    static ref QUERY_MAP: HashMap<Id, &'static str > = HashMap::from([
        (Id::ComputerName, query::COMPUTER_NAME),
        (Id::Mirroring, query::MIRRORING_NORMAL),
        (Id::Jobs, query::JOBS),
        (Id::AvailabilityGroups, query::AVAILABILITY_GROUP_NORMAL),
        (Id::InstanceProperties, query::INSTANCE_PROPERTIES),
        (Id::UtcEntry, query::UTC_ENTRY),
        (Id::ClusterActiveNodes, query::CLUSTER_ACTIVE_NODES),
        (Id::ClusterNodes, query::CLUSTER_NODES_NORMAL),
        (Id::IsClustered, query::IS_CLUSTERED),
        (Id::DatabaseNames, query::DATABASE_NAMES),
        (Id::Databases, query::DATABASES),
        (Id::Datafiles, query::DATAFILES),
        (Id::Backup, query::BACKUP),
        (Id::TableSpaces, query::SPACE_USED),
        (Id::CounterEntries, query::COUNTERS_ENTRIES_NORMAL),
        (Id::Connections, query::CONNECTIONS),
        (Id::TransactionLogs, query::TRANSACTION_LOGS),
        (Id::BadQuery, query::BAD_QUERY),
        (Id::WaitingTasks, query::WAITING_TASKS), // used only in tests no None))w
        (Id::BlockedSessions, BLOCKING_SESSIONS.as_str()),
        (Id::Counters, COUNTERS_NORMAL.as_str()),
        (Id::Clusters, CLUSTERS_NORMAL.as_str()),
    ]);
}

pub fn find_known_query<T: Borrow<Id>>(query_id: T) -> Result<&'static str> {
    QUERY_MAP
        .get(query_id.borrow())
        .copied()
        .ok_or(anyhow::anyhow!(
            "Query for {:?} not found",
            query_id.borrow()
        ))
}
