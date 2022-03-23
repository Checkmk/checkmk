' -----------------------------------------------------------------------------
' Check_MK windows agent plugin to gather information from local MSSQL servers
'
' This plugin can be used to collect information of all running MSSQL server
' on the local system.
'
' The current implementation of the check uses the "trusted authentication"
' where no user/password needs to be created in the MSSQL server instance by
' default. It is only needed to grant the user as which the Check_MK windows
' agent service is running access to the MSSQL database.
'
' Another option is to create a mssql.ini file in MK_CONFDIR and write the
' credentials of a database user to it which shal be used for monitoring:
'
' The config file mssql.ini may contain a list of instances to exclude
' from monitoring. By default, every running instance is monitored.
'
' [auth]
' type = db
' username = monitoring
' password = secret-pw
' [instance]
' exclude = inst1,inst2,inst3
'
' The following sources are asked:
' 1. Registry - To gather a list of local MSSQL-Server instances
' 2. WMI - To check for the state of the MSSQL service
' 2. MSSQL-Servers via ADO/sqloledb connection to gather infos these infos:
'      a) list and sizes of available databases
'      b) counters of the database instance
'
' This check has been developed with MSSQL Server 2008 R2. It should work with
' older versions starting from at least MSSQL Server 2005.
' -----------------------------------------------------------------------------

Option Explicit
Const CMK_VERSION = "2.0.0p23"

Dim WMI, FSO, objStdout, SHO, items, objItem, prop, instVersion, registry
Dim sources, instances, instance, instance_id, instance_name, instance_excluded, service_name
Dim cfg_dir, cfg_file, hostname, tcpport

Const HKLM = &H80000002

' Directory of all database instance names
Set instances = CreateObject("Scripting.Dictionary")
Set FSO = CreateObject("Scripting.FileSystemObject")
' Request unicode stdout and add a bom so the agent knows we send utf-16
Set objStdout = FSO.GetStandardStream(1, True)
objStdout.Write(chrW(&HFEFF))
Set SHO = CreateObject("WScript.Shell")

hostname = SHO.ExpandEnvironmentStrings("%COMPUTERNAME%")
cfg_dir = SHO.ExpandEnvironmentStrings("%MK_CONFDIR%")

Sub addOutput(text)
    objStdout.WriteLine text
End Sub

Function readIniFile(path)
    Dim parsed : Set parsed = CreateObject("Scripting.Dictionary")
    If path <> "" Then
        Dim FH
        Set FH = FSO.OpenTextFile(path)
        Dim line, sec, pair
        Do Until FH.AtEndOfStream
            line = Trim(FH.ReadLine())
            If Left(line, 1) = "[" Then
                sec = Mid(line, 2, Len(line) - 2)
                Set parsed(sec) = CreateObject("Scripting.Dictionary")
            Else
                If line <> "" Then
                    pair = Split(line, "=")
                    If 1 = UBound(pair) Then
                        parsed(sec)(Trim(pair(0))) = Trim(pair(1))
                    End If
                End If
            End If
        Loop
        FH.Close
        Set FH = Nothing
    End If
    Set readIniFile = parsed
    Set parsed = Nothing
End Function

Set registry = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\default:StdRegProv")
Set sources = CreateObject("Scripting.Dictionary")

Dim service, i, elem, version, edition, value_types, value_names, value_raw, cluster_name
Set WMI = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")

' Make sure that always all sections are present, even in case of an error.
' Note: the section <<<mssql_instance>>> section shows the general state
' of a database instance. If that section fails for an instance then all
' other sections do not contain valid data anyway.
'
' Don't move this to another place. We need the steps above to decide whether or
' not this is a MSSQL server.
Dim sections, section_id
Set sections = CreateObject("Scripting.Dictionary")
sections.add "instance", "<<<mssql_instance:sep(124)>>>"
sections.add "databases", "<<<mssql_databases:sep(124)>>>"
sections.add "counters", "<<<mssql_counters:sep(124)>>>"
sections.add "tablespaces", "<<<mssql_tablespaces>>>"
sections.add "blocked_sessions", "<<<mssql_blocked_sessions:sep(124)>>>"
sections.add "backup", "<<<mssql_backup:sep(124)>>>"
sections.add "transactionlogs", "<<<mssql_transactionlogs:sep(124)>>>"
sections.add "datafiles", "<<<mssql_datafiles:sep(124)>>>"
sections.add "clusters", "<<<mssql_cluster:sep(124)>>>"
sections.add "jobs", "<<<mssql_jobs:sep(09)>>>"
' Has been deprecated with 1.4.0i1. Keep this for nicer transition for some versions.
sections.add "versions", "<<<mssql_versions:sep(124)>>>"
sections.add "connections", "<<<mssql_connections>>>"

For Each section_id In sections.Keys
    addOutput(sections(section_id))
Next

addOutput(sections("instance"))

' Search for exclude list in mssql.ini file.
cfg_file = cfg_dir & "\mssql.ini"
If Not FSO.FileExists(cfg_file) Then
    cfg_file = ""
End If
Set CFG = readIniFile(cfg_file)

Dim INST, exclude_list
If CFG.Exists("instance") Then
    Set INST = CFG("instance")
Else
    Set INST = CreateObject("Scripting.Dictionary")
End If
If INST.Exists("exclude") Then
    exclude_list = Split(INST("exclude"), ",")
Else
    exclude_list = Array()
End If
Set INST = Nothing

' Get connection and command timeouts if configured
Dim TIMEOUTS
If CFG.Exists("timeouts") Then
    Set TIMEOUTS = CFG("timeouts")
Else
    Set TIMEOUTS = CreateObject("Scripting.Dictionary")
End If

'
' Gather instances on this host, store instance in instances and output version section for it
'

Dim regkeys, rk
regkeys = Array( "", "Wow6432Node") ' gather all instances, also 32bit ones on 64bit Windows

For Each rk In regkeys
    Do
        registry.EnumValues HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\Instance Names\SQL", _
                                  value_names, value_types

        If Not IsArray(value_names) Then
            'addOutput("ERROR: Failed to gather SQL server instances: " & rk)
            'wscript.quit(1)
            Exit Do
        End If

        For i = LBound(value_names) To UBound(value_names)
            instance_id = value_names(i)

            registry.GetStringValue HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\" & _
                                          "Instance Names\SQL", _
                                          instance_id, instance_name

            ' HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL10_50.MSSQLSERVER\Setup
            registry.GetStringValue HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\" & _
                                          instance_name & "\Setup", _
                                          "Version", version

            ' HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL10_50.MSSQLSERVER\Setup
            registry.GetStringValue HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\" & _
                                          instance_name & "\Setup", _
                                          "Edition", edition

            ' Check whether or not this instance is clustered
            registry.GetStringValue HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\" & _
                                          instance_name & "\Cluster", "ClusterName", cluster_name

            ' HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL10_50.MSSQLSERVER\MSSQLServer\SuperSocketNetLib\TCP\IPAll
            registry.GetStringValue HKLM, "SOFTWARE\" & rk & "\Microsoft\Microsoft SQL Server\" & _
                                          instance_name & "\MSSQLServer\SuperSocketNetLib\TCP\IPAll", _
                                          "tcpPort", tcpport

            If IsNull(cluster_name) Or cluster_name = "" Then
                cluster_name = ""

                ' In case of instance name "MSSQLSERVER" always use (local) as connect string
                If instance_id = "MSSQLSERVER" Then
                    sources.add instance_id, "(local)"
                Else
                    If isNull(tcpport) Or tcpport = "" Then
                        sources.add instance_id, hostname & "\" & instance_id
                    Else
                        sources.add instance_id, hostname & "," & tcpport
                    End If
                End If
            Else
                ' In case the instance name is "MSSQLSERVER" always use the virtual server name
                If instance_id = "MSSQLSERVER" Then
                    sources.add instance_id, cluster_name
                Else
                    If isNull(tcpport) Or tcpport = "" Then
                        sources.add instance_id, cluster_name & "\" & instance_id
                    Else
                        sources.add instance_id, cluster_name & "," & tcpport
                    End If
                End If
            End If

            ' The default instance is named "MSSQLSERVER" and corresponds to its service name
            ' All other instances's service names have the "MSSQL$" prefix
            If instance_id = "MSSQLSERVER" Then
                service_name = instance_id
            Else
                service_name = "MSSQL$" & instance_id
            End If

            ' Only collect results for instances which services are currently running
            Set service = WMI.ExecQuery("SELECT State FROM Win32_Service " & _
                                  "WHERE Name = '" & service_name & "'" & _
                                  "AND State = 'Running'")

            ' Check if instance is in the exclude list.
            instance_excluded = False
            For Each elem In exclude_list
                If StrComp(Trim(elem), instance_id) = 0 Then
                    instance_excluded = True
                    Exit For
                End If
            Next
            If Not instance_excluded And service.count > 0 Then
                addOutput(sections("instance"))
                addOutput("MSSQL_" & instance_id & "|config|" & version & "|" & edition & "|" & cluster_name)
                instances.add instance_id, cluster_name
            End If
        Next
    Loop While False
Next
Set instance_excluded = Nothing

If instances.Count = 0 Then
    addOutput("ERROR: Failed to gather SQL server instances")
    wscript.quit(1)
End IF

Set service  = Nothing
Set WMI      = Nothing
Set registry = Nothing

Dim CONN, RS, CFG, AUTH

' Function to check for any connection errors and return those concatenated, if any
Function checkConnErrors(conn)
    Dim error_msg, errObj
    error_msg = ""
    If conn.Errors.Count > 0 Then
        error_msg = "ERROR: "
        For Each errObj in conn.Errors
            error_msg = error_msg & errObj.Description & " (SQLState: " & _
                        errObj.SQLState & "/NativeError: " & errObj.NativeError & "). "
        Next
    End If
    Err.Clear
    checkConnErrors = error_msg
End Function

' Initialize database connection objects
Set CONN      = CreateObject("ADODB.Connection")
Set RS        = CreateObject("ADODB.Recordset")

If TIMEOUTS.Exists("timeout_connection") Then
    CONN.ConnectionTimeout = CInt(TIMEOUTS("timeout_connection"))
End If
If TIMEOUTS.Exists("timeout_command") Then
    CONN.CommandTimeout = CInt(TIMEOUTS("timeout_command"))
End If


' Loop all found server instances and connect to them
' In my tests only the connect using the "named instance" string worked
For Each instance_id In instances.Keys: Do ' Continue trick
    ' Is empty on standalone instances, and holds the name of the cluster on nodes
    cluster_name = instances(instance_id)

    ' Use either an instance specific config file named mssql_<instance-id>.ini
    ' or the default mssql.ini file.
    ' Replace '\' in instance name with '_' (needed for baked agents)
    cfg_file = cfg_dir & "\mssql_" & Replace(Replace(instance_id, "\", "_"), ",", "_") & ".ini"
    If Not FSO.FileExists(cfg_file) Then
	' Try legacy filename in case of manual deployment
	cfg_file = cfg_dir & "\mssql_" & instance_id & ".ini"
        If Not FSO.FileExists(cfg_file) Then
            cfg_file = cfg_dir & "\mssql.ini"
            If Not FSO.FileExists(cfg_file) Then
                cfg_file = ""
            End If
        End If
    End If

    Set CFG = readIniFile(cfg_file)
    If Not CFG.Exists("auth") Then
        Set AUTH = CreateObject("Scripting.Dictionary")
    Else
        Set AUTH = CFG("auth")
    End If

    ' Try to connect to the instance and catch the error when not able to connect
    ' Then add the instance to the agent output and skip over to the next instance
    ' in case the connection could not be established.
    On Error Resume Next

    Dim connProv, errMsg
    errMsg = ""

    For Each connProv in Array("msoledbsql", "sqloledb", "sqlncli11")

        CONN.Provider = connProv

        ' At this place one could implement other authentication mechanism
        ' Note that these properties have to be set after setting CONN.Provider
        If Not AUTH.Exists("type") or AUTH("type") = "system" Then
            CONN.Properties("Integrated Security").Value = "SSPI"
        Else
            CONN.Properties("User ID").Value = AUTH("username")
            CONN.Properties("Password").Value = AUTH("password")
        End If

        CONN.Properties("Data Source").Value = sources(instance_id)

        CONN.Open

        ' Note that the user will only see this message in case no connection can be established
        errMsg = errMsg & "Connecting using provider " & connProv & ". "

        ' If the provider is invalid, errors end up in Err, not in CONN.Errors
        if Err.Number <> 0 Then
            errMsg = errMsg & "ERROR: " & Err.Description
            If Right(errMsg, 1) <> "." Then
            	errMsg = errMsg & "."
            End If
            errMsg = errMsg & " "
        End If

        ' Collect errors which occurred during connecting. Hopefully there is only one
        ' error in the list of errors.
        errMsg = errMsg & checkConnErrors(CONN)

        ' In case the connection is still closed, we try with the next provider
        ' 0 - closed
        ' 1 - open
        ' 2 - connecting
        ' 4 - executing a command
        ' 8 - rows are being fetched
        If CONN.State = 1 Then
            Exit For
        End If
    Next

    addOutput(sections("instance"))
    addOutput("MSSQL_" & instance_id & "|state|" & CONN.State & "|" & errMsg)

    If CONN.State = 0 Then
        Exit Do
    End If

    ' add detailed information about version and patchrelease
    RS.Open "SELECT SERVERPROPERTY('productversion') as prodversion," & _
            "SERVERPROPERTY ('productlevel') as prodlevel," & _
            "SERVERPROPERTY ('edition') as prodedition", CONN
    addOutput("MSSQL_" & instance_id & "|details|" & RS("prodversion") & "|" & _
               RS("prodlevel") & "|" & RS("prodedition"))
    RS.Close

    ' Get counter data for the whole instance
    addOutput(sections("counters"))
    RS.Open "SELECT GETUTCDATE() as utc_date", CONN
    addOutput("None|utc_time|None|" & RS("utc_date"))
    RS.Close

    RS.Open "SELECT counter_name, object_name, instance_name, cntr_value " & _
            "FROM sys.dm_os_performance_counters " & _
            "WHERE object_name NOT LIKE '%Deprecated%'", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        addOutput("||" & instance_id & "|" & errMsg)
    Else
        Dim objectName, counterName, counters_inst_name, value
        Do While NOT RS.Eof
            objectName   = Replace(Replace(Trim(RS("object_name")), " ", "_"), "$", "_")
            counterName  = LCase(Replace(Trim(RS("counter_name")), " ", "_"))
            counters_inst_name = Replace(Trim(RS("instance_name")), " ", "_")
            If counters_inst_name = "" Then
                counters_inst_name = "None"
            End If
            value = Trim(RS("cntr_value"))
            addOutput( objectName & "|" & counterName & "|" & counters_inst_name & "|" & value )
            RS.MoveNext
        Loop
    End If
    RS.Close

    addOutput(sections("blocked_sessions"))
    RS.Open "SELECT session_id, wait_duration_ms, wait_type, blocking_session_id " & _
            "FROM sys.dm_os_waiting_tasks " & _
            "WHERE blocking_session_id <> 0 ", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        addOutput(instance_id & "|" & errMsg)
    ElseIf Not RS.Eof Then
        Dim session_id, wait_duration_ms, wait_type, blocking_session_id
        Do While NOT RS.Eof
            session_id = Trim(RS("session_id"))
            wait_duration_ms = Trim(RS("wait_duration_ms"))
            wait_type = Trim(RS("wait_type"))
            blocking_session_id = Trim(RS("blocking_session_id"))
            addOutput(instance_id & "|" & session_id & "|" & wait_duration_ms & "|" & wait_type & "|" & blocking_session_id)
            RS.MoveNext
        Loop
    Else
        addOutput(instance_id & "|No blocking sessions")
    End If
    RS.Close

    ' First only read all databases in this instance and save it to the db names dict
    RS.Open "SELECT NAME AS DATABASE_NAME FROM sys.databases", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        ' Achtung, am Besten "databases" hier hin vorziehen, denn dann wird die Prozedur
        ' hier nicht benoetigt und man kann direkt ein "exit do"bei Fehlern machen
        ' addOutput("||" & instance_id & "||" & errMsg)
    Else
        Dim x, dbName, dbNames
        Set dbNames = CreateObject("Scripting.Dictionary")
        Do While NOT RS.Eof
           dbName = RS("DATABASE_NAME")
           dbNames.add dbName, ""
           RS.MoveNext
        Loop
    End If
    RS.Close

    ' Now gather the db size and unallocated space
    addOutput(sections("tablespaces"))
    Dim dbSize, unallocated, reserved, data, indexSize, unused
    For Each dbName in dbNames.Keys
        ' Switch to other database and then ask for stats
        RS.Open "USE [" & dbName & "]", CONN
        ' sp_spaceused is a stored procedure which returns two selects
        ' which need to be looped
        RS.Open "EXEC sp_spaceused", CONN

        errMsg = checkConnErrors(CONN)
        If Not errMsg = "" Then
            addOutput("MSSQL_" & instance_id &  " " & Replace(dbName, " ", "_") & _
                      " - - - - - - - - - - - - " & errMsg)
        Else
            i = 0
            Do Until RS Is Nothing
                Do While NOT RS.Eof
                    'For Each x in RS.fields
                    '    wscript.echo x.name & " " & x.value
                    'Next
                    If i = 0 Then
                        ' Size of the current database in megabytes. database_size includes both data and log files.
                        dbSize      = Trim(RS("database_size"))
                        ' Space in the database that has not been reserved for database objects.
                        unallocated = Trim(RS("unallocated space"))
                    Elseif i = 1 Then
                        ' Total amount of space allocated by objects in the database.
                        reserved    = Trim(RS("reserved"))
                        ' Total amount of space used by data.
                        data        = Trim(RS("data"))
                        ' Total amount of space used by indexes.
                        indexSize   = Trim(RS("index_size"))
                        ' Total amount of space reserved for objects in the database, but not yet used.
                        unused      = Trim(RS("unused"))
                        End If
                    RS.MoveNext
                Loop
                Set RS = RS.NextRecordset
                i = i + 1
            Loop
            addOutput("MSSQL_" & instance_id & " " & Replace(dbName, " ", "_") & " " & dbSize & " " & _
                unallocated & " " & reserved & " " & data & " " & indexSize & " " & unused)
            Set RS = CreateObject("ADODB.Recordset")
        End If
    Next

    ' Loop all databases to get the date of the last backup. Only show databases
    ' which have at least one backup
    Dim lastBackupDate, backup_type, is_primary_replica, replica_id, backup_machine_name
    addOutput(sections("backup"))
    For Each dbName in dbNames.Keys
        RS.Open "USE [master]", CONN
        RS.Open "DECLARE @HADRStatus sql_variant; DECLARE @SQLCommand nvarchar(max); " & _
                "SET @HADRStatus = (SELECT SERVERPROPERTY ('IsHadrEnabled')); " & _
                "IF (@HADRStatus IS NULL or @HADRStatus <> 1) " & _
                "BEGIN " & _
                    "SET @SQLCommand = 'SELECT CONVERT(VARCHAR, DATEADD(s, DATEDIFF(s, ''19700101'', MAX(backup_finish_date)), ''19700101''), 120) AS last_backup_date, " & _
                    "type, machine_name, ''True'' as is_primary_replica, ''1'' as is_local, '''' as replica_id FROM msdb.dbo.backupset " & _
                    "WHERE database_name = ''" & dbName & "'' AND  machine_name = SERVERPROPERTY(''Machinename'') " & _
                    "GROUP BY type, machine_name ' " & _
                "END " & _
                "ELSE " & _
                "BEGIN " & _
                    "SET @SQLCommand = 'SELECT CONVERT(VARCHAR, DATEADD(s, DATEDIFF(s, ''19700101'', MAX(b.backup_finish_date)), ''19700101''), 120) AS last_backup_date,  " & _
                    "b.type, b.machine_name, isnull(rep.is_primary_replica,0) as is_primary_replica, rep.is_local, isnull(convert(varchar(40), rep.replica_id), '''') AS replica_id  " & _
                    "FROM msdb.dbo.backupset b  " & _
                    "LEFT OUTER JOIN sys.databases db ON b.database_name = db.name  " & _
                    "LEFT OUTER JOIN sys.dm_hadr_database_replica_states rep ON db.database_id = rep.database_id  " & _
                    "WHERE database_name = ''" & dbName & "'' AND (rep.is_local is null or rep.is_local = 1)  " & _
                    "AND (rep.is_primary_replica is null or rep.is_primary_replica = ''True'') and machine_name = SERVERPROPERTY(''Machinename'') " & _
                    "GROUP BY type, rep.replica_id, rep.is_primary_replica, rep.is_local, b.database_name, b.machine_name, rep.synchronization_state, rep.synchronization_health' " & _
                "END " & _
                "EXEC (@SQLCommand)", CONN

        errMsg = checkConnErrors(CONN)
        If Not errMsg = "" Then
            addOutput("MSSQL_" & instance_id & "|" & Replace(dbName, " ", "_") & _
                      "|-|-|-|" & errMsg)
        Else
            If RS.Eof Then
                addOutput("MSSQL_" & instance_id & "|" & Replace(dbName, " ", "_") & _
                          "|-|-|-|no backup found")
            End If

            Do While Not RS.Eof
                lastBackupDate = Trim(RS("last_backup_date"))

                backup_type = Trim(RS("type"))
                If backup_type = "" Then
                    backup_type = "-"
                End If

                replica_id = Trim(RS("replica_id"))
                is_primary_replica = Trim(RS("is_primary_replica"))
                backup_machine_name = Trim(RS("machine_name"))

                If lastBackupDate <> "" and (replica_id = "" or is_primary_replica = "True") Then
                    addOutput("MSSQL_" & instance_id & "|" & Replace(dbName, " ", "_") & _
                              "|" & Replace(lastBackupDate, " ", "|") & "|" & backup_type)
                End If

                RS.MoveNext
            Loop
        End If

        RS.Close
    Next

    ' Loop all databases to get the size of the transaction log
    addOutput(sections("transactionlogs"))
    For Each dbName in dbNames.Keys
        RS.Open "USE [" & dbName & "];", CONN
        RS.Open "SELECT name, physical_name," &_
                "  cast(max_size/128 as bigint) as MaxSize," &_
                "  cast(size/128 as bigint) as AllocatedSize," &_
                "  cast(FILEPROPERTY (name, 'spaceused')/128 as bigint) as UsedSize," &_
                "  case when max_size = '-1' then '1' else '0' end as Unlimited" &_
                " FROM sys.database_files WHERE type_desc = 'LOG'", CONN

        errMsg = checkConnErrors(CONN)
        If Not errMsg = "" Then
            addOutput(instance_id &  "|" & Replace(dbName, " ", "_") & _
                      "|-|-|-|-|-|-|" & errMsg)
        Else
            Do While Not RS.Eof
                addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & Replace(RS("name"), " ", "_") & _
                          "|" & Replace(RS("physical_name"), " ", "_") & "|" & _
                          RS("MaxSize") & "|" & RS("AllocatedSize") & "|" & RS("UsedSize")) & _
                          "|" & RS("Unlimited")
                RS.MoveNext
            Loop
            RS.Close
        End If
    Next

    ' Loop all databases to get the size of the transaction log
    addOutput(sections("datafiles"))
    For Each dbName in dbNames.Keys
        RS.Open "USE [" & dbName & "];", CONN
        RS.Open "SELECT name, physical_name," &_
                "  cast(max_size/128 as bigint) as MaxSize," &_
                "  cast(size/128 as bigint) as AllocatedSize," &_
                "  cast(FILEPROPERTY (name, 'spaceused')/128 as bigint) as UsedSize," &_
                "  case when max_size = '-1' then '1' else '0' end as Unlimited" &_
                " FROM sys.database_files WHERE type_desc = 'ROWS'", CONN

        If Not errMsg = "" Then
            addOutput(instance_id &  "|" & Replace(dbName, " ", "_") & _
                      "|-|-|-|-|-|-|" & errMsg)
        Else
            Do While Not RS.Eof
                addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & Replace(RS("name"), " ", "_") & _
                          "|" & Replace(RS("physical_name"), " ", "_") & "|" & _
                          RS("MaxSize") & "|" & RS("AllocatedSize") & "|" & RS("UsedSize")) & _
                          "|" & RS("Unlimited")
                RS.MoveNext
            Loop
            RS.Close
        End If
    Next

    ' Database properties, full list at https://msdn.microsoft.com/en-us/library/ms186823.aspx
    addOutput(sections("databases"))
    RS.Open "SELECT name, " & _
            "DATABASEPROPERTYEX(name, 'Status') AS Status, " & _
            "DATABASEPROPERTYEX(name, 'Recovery') AS Recovery, " & _
            "DATABASEPROPERTYEX(name, 'IsAutoClose') AS auto_close, " & _
            "DATABASEPROPERTYEX(name, 'IsAutoShrink') AS auto_shrink " & _
            "FROM master.dbo.sysdatabases", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        For Each dbName in dbNames.Keys
            addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & errMsg & "|-|-|-")
        Next
    Else
        Do While Not RS.Eof
            ' instance db_name status recovery auto_close auto_shrink
            addOutput(instance_id & "|" & Replace(Trim(RS("name")), " ", "_") & "|" & Trim(RS("Status")) & _
                      "|" & Trim(RS("Recovery")) & "|" & Trim(RS("auto_close")) & "|" & Trim(RS("auto_shrink")) )
            RS.MoveNext
        Loop
        RS.Close
    End If

    addOutput(sections("clusters"))
    Dim active_node, nodes
    For Each dbName in dbNames.Keys : Do
        RS.Open "USE [" & dbName & "];", CONN

        ' Skip non cluster instances
        RS.Open "SELECT SERVERPROPERTY('IsClustered') AS is_clustered", CONN
        If RS("is_clustered") = 0 Then
            RS.Close
            Exit Do
        End If
        RS.Close

        nodes = ""
        RS.Open "SELECT nodename FROM sys.dm_os_cluster_nodes", CONN
        Do While Not RS.Eof
            If nodes <> "" Then
                nodes = nodes & ","
            End If
            nodes = nodes & RS("nodename")
            RS.MoveNext
        Loop
        RS.Close

        active_node = "-"
        RS.Open "SELECT SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS active_node", CONN
        Do While Not RS.Eof
            active_node = RS("active_node")
            RS.MoveNext
        Loop
        RS.Close

        addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & active_node & "|" & nodes)
    Loop While False: Next

    addOutput(sections("connections"))
    Dim connection_count, database_name

    RS.Open "SELECT name AS DBName, ISNULL((SELECT  COUNT(dbid) AS NumberOfConnections FROM " &_
    "sys.sysprocesses WHERE dbid > 0 AND name = DB_NAME(dbid) GROUP BY dbid ),0) AS NumberOfConnections " &_
    "FROM sys.databases", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        addOutput(instance_id & " " & errMsg)
    Else
        Do While Not RS.Eof
            database_name = RS("DBName")
            connection_count = RS("NumberOfConnections")

            addOutput(instance_id & " " & Replace(database_name, " ", "_") & " " & connection_count)
            RS.MoveNext
        Loop
        RS.Close
    End If

    addOutput(sections("jobs"))
    RS.Open "USE [msdb];", CONN
    RS.Open "SELECT  " &_
            "    sj.job_id " &_
            "   ,sj.name AS job_name " &_
            "   ,sj.enabled AS job_enabled " &_
            "   ,CAST(sjs.next_run_date AS VARCHAR(8)) AS next_run_date " &_
            "   ,CAST(sjs.next_run_time AS VARCHAR(6)) AS next_run_time " &_
            "   ,sjserver.last_run_outcome " &_
            "   ,sjserver.last_outcome_message " &_
            "   ,CAST(sjserver.last_run_date AS VARCHAR(8)) AS last_run_date " &_
            "   ,CAST(sjserver.last_run_time AS VARCHAR(6)) AS last_run_time " &_
            "   ,sjserver.last_run_duration " &_
            "   ,ss.enabled AS schedule_enabled " &_
            "   ,CONVERT(VARCHAR, CURRENT_TIMESTAMP, 20) AS server_current_time " &_
            " FROM dbo.sysjobs sj " &_
            " LEFT JOIN dbo.sysjobschedules sjs ON sj.job_id = sjs.job_id " &_
            " LEFT JOIN dbo.sysjobservers sjserver ON sj.job_id = sjserver.job_id " &_
            " LEFT JOIN dbo.sysschedules ss ON sjs.schedule_id = ss.schedule_id " &_
            " ORDER BY sj.name " &_
            "          ,sjs.next_run_date ASC " &_
            "          ,sjs.next_run_time ASC " &_
            "; ", CONN

    errMsg = checkConnErrors(CONN)
    If Not errMsg = "" Then
        addOutput(instance_id & " " & errMsg)
    Else
        Do While Not RS.Eof
            'See following documentation for use of parameters and the GetString method:
            'https://docs.microsoft.com/en-us/sql/ado/reference/ado-api/getstring-method-ado?view=sql-server-ver15
            addOutput(instance_id & vbCrLf & RS.GetString(2,,vbTab,vbCrLf,""))
        Loop
        RS.Close
    End If

    CONN.Close

Loop While False: Next

Set sources = nothing
Set instances = nothing
Set sections = nothing
Set RS = nothing
Set CONN = nothing
Set FSO = nothing
Set SHO = nothing
