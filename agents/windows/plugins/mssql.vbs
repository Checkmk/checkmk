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
Const CMK_VERSION = "2.4.0p21"

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

Function appendElement(array_, element)
   Dim incremented_index

   incremented_index = UBound(array_) + 1
   ReDim Preserve array_(incremented_index)
   array_(incremented_index) = element
   appendElement = array_
End Function

Function sanitiseString(valueString)
   If IsNull(valueString) Then
      sanitiseString = ""
      Exit Function
   End If

   sanitiseString = valueString
End Function

Function isInList(list, element)
   Dim value
   For Each value in list
      If value = element Then
         isInList = True
         Exit Function
      End If
   Next
   isInList = False
End Function

Class connectionResponse
   Private connectionState
   Private connectionErrorLog
   Private connectionDebugLog

   Public Default Function Init(state, errorLog, debugLog)
      connectionState = state
      connectionErrorLog = errorLog
      connectionDebugLog = debugLog

      Set Init = Me
   End Function

   Public Property Get State
      ' 0 - closed
      ' 1 - open
      ' 2 - connecting
      ' 4 - executing a command
      ' 8 - rows are being fetched
      State = connectionState
   End Property

   Public Property Get logMessage
      If connectionState = 1 Then
         logMessage = ""
         Exit Property
      End If

      Dim message
      message = "INFO: " & Join(connectionDebugLog, "; ")
      If UBound(connectionErrorLog) + 1 > 0 Then
         message = message & " ;; " & "ERROR: " & Join(connectionErrorLog, "; ")
      End If

      logMessage = message
   End Property

End Class

Class errorResponse
   Private queryErrors

   Public Default Function Init(connectionHandler)
      queryErrors = Array()

      Dim error_, index
      For Each error_ in connectionHandler.Errors
         index = UBound(queryErrors) + 1
         ReDim Preserve queryErrors(index) ' resize and keep existing elements
         Set queryErrors(index) = error_
      Next

      Set Init = Me
   End Function

   Public Property Get errorMessage
       Dim errorText, errorObject
       errorText = "ERROR: "
       For Each errorObject in queryErrors
           errorText = errorText & errorObject.Description & " (SQLState: " & _
                       errorObject.SQLState & "/NativeError: " & errorObject.NativeError & "). "
       Next
       errorMessage = errorText
   End Property

   Public Property Get hasError
      hasError = True
   End Property

End Class

Class queryResponse
   Private queryRows

   Public Default Function Init(recordHandler)
      queryRows = Array()

      Dim row, field_, index

      Do Until recordHandler Is Nothing
         Do Until recordHandler.EOF
            Set row = CreateObject("Scripting.Dictionary")
            For Each field_ in recordHandler.Fields
               row.Add field_.Name, sanitiseString(field_.value)
            Next
            index = UBound(queryRows) + 1
            ReDim Preserve queryRows(index) ' resize and keep existing elements
            Set queryRows(index) = row
            recordHandler.MoveNext
         Loop
         Set recordHandler = RecordHandler.NextRecordSet
      Loop

      Set Init = Me
   End Function

   Public Property Get Rows
      Rows = queryRows
   End Property

   Public Property Get hasError
      hasError = False
   End Property

End Class

Class DbSession
   Private dbConnectionHandler

   Public Default Function Init(timeouts)
      Set dbConnectionHandler = CreateObject("ADODB.Connection")

      If timeouts.Exists("timeout_connection") Then
          dbConnectionHandler.ConnectionTimeout = CInt(timeouts("timeout_connection"))
      End If
      If timeouts.Exists("timeout_command") Then
          dbConnectionHandler.CommandTimeout = CInt(timeouts("timeout_command"))
      End If

      Set Init = Me
   End Function

   Public Function connect(instance, authenticationConfig, providers)
      On Error Resume Next

      Dim connectionProvider, errorLog, debugLog

      errorLog = Array()
      debugLog = Array()

      For Each connectionProvider in providers
          dbConnectionHandler.Provider = connectionProvider

          debugLog = appendElement(debugLog, "Connecting using provider " & connectionProvider)

          ' Note that these properties have to be set after setting the provider

          If Not authenticationConfig.Exists("type") or authenticationConfig("type") = "system" Then
              dbConnectionHandler.Properties("Integrated Security").Value = "SSPI"
          Else
              dbConnectionHandler.Properties("User ID").Value = authenticationConfig("username")
              dbConnectionHandler.Properties("Password").Value = authenticationConfig("password")
          End If

          dbConnectionHandler.Properties("Data Source").Value = instance

          dbConnectionHandler.Open

          ' 1 = connected
          If dbConnectionHandler.State = 1 Then
              Exit For
          End If
      Next

      If Err.Number <> 0 Then
         errorLog = appendElement(errorLog, Err.Description)
      End If

      Dim errorObject
      If dbConnectionHandler.Errors.Count > 0 Then
         For Each errorObject in dbConnectionHandler.Errors
            errorLog = appendElement(errorLog, errorObject.Description)
         Next
      End If

      Set connect = (New connectionResponse)(dbConnectionHandler.State, errorLog, debugLog)

   End Function

   Public Function querySystem(sqlString)
      ' System wide queries
      On Error Resume Next
      Dim dbRecordHandler

      Set dbRecordHandler = CreateObject("ADODB.Recordset")

      dbRecordHandler.Open sqlString, dbConnectionHandler

      Set querySystem = constructQueryResponse(dbRecordHandler)

      dbRecordHandler.Close
      Set dbRecordHandler = Nothing
   End Function

   Public Function queryDatabase(databaseName, sqlString)
      ' Database specific queries
      On Error Resume Next
      Dim dbRecordHandler

      Set dbRecordHandler = CreateObject("ADODB.Recordset")

      dbRecordHandler.Open "USE [" & databaseName & "]", dbConnectionHandler
      If hasErrors() Then
         ' If the database returns an error while attempting to swtich to it,
         ' e.g. due to access reasons, it does not make sense to proceed
         Set queryDatabase = (New errorResponse)(dbConnectionHandler)
         If dbRecordHandler.State <> 0 Then
            dbRecordHandler.Close
         End If
         Set dbRecordHandler = Nothing
         Exit Function
      End If

      dbRecordHandler.Open sqlString, dbConnectionHandler

      Set queryDatabase = constructQueryResponse(dbRecordHandler)

      dbRecordHandler.Close
      Set dbRecordHandler = Nothing
   End Function

   Private Function constructQueryResponse(dbRecordHandler)
      If hasErrors() Then
         Set constructQueryResponse = (New errorResponse)(dbConnectionHandler)
      Else
         Set constructQueryResponse = (New queryResponse)(dbRecordHandler)
      End If
   End Function

   Private Function hasErrors( )
      If dbConnectionHandler.Errors.Count = 0 Then
         hasErrors = False
         Exit Function
      End If

      Dim knownWarnings, warning, error_
      knownWarnings = Array(5701) ' Infotext that says it has been successfully switched to a different DB
      For Each error_ in dbConnectionHandler.Errors
         If Not isInList(knownWarnings, error_.NativeError) Then
            ' Errors may not be real errors, but warnings or other informational
            ' text disguised as errors
            hasErrors = True
            Exit Function
         End If
      Next
      hasErrors = False
   End Function

   Public Function terminateConnection( )
      If dbConnectionHandler.State <> 0 Then
         dbConnectionHandler.Close
      End If
   End Function

   Public Function terminateSession( )
      terminateConnection
      Set dbConnectionHandler = Nothing
   End Function

End Class

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
sections.add "mirroring", "<<<mssql_mirroring:sep(09)>>>"
sections.add "availability_groups", "<<<mssql_availability_groups:sep(09)>>>"
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

Dim CFG, AUTH, DATABASE_CONNECTION_PROVIDERS

' Initialize database connection objects
DATABASE_CONNECTION_PROVIDERS = Array("msoledbsql", "sqloledb", "sqlncli11")

Dim databaseSession
Set databaseSession = (New DbSession)(TIMEOUTS)

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

    Dim connectionState, databaseResponse, record, sqlString

    ' Try to connect to the instance and catch the error when not able to connect
    ' Then add the instance to the agent output and skip over to the next instance
    ' in case the connection could not be established.
    On Error Resume Next

    Set connectionState = databaseSession.connect(sources(instance_id), AUTH, DATABASE_CONNECTION_PROVIDERS)

    addOutput(sections("instance"))
    addOutput("MSSQL_" & instance_id & "|state|" & connectionState.State & "|" & connectionState.logMessage)

    ' 0 = closed
    If connectionState.State = 0 Then
        Exit Do
    End If

    ' add detailed information about version and patchrelease
    sqlString = "SELECT SERVERPROPERTY('productversion') as prodversion, " & _
                "  SERVERPROPERTY ('productlevel') as prodlevel, " & _
                "  SERVERPROPERTY ('edition') as prodedition"
    Set databaseResponse = databaseSession.querySystem(sqlString)
    If databaseResponse.hasError Then
       addOutput("||||" & databaseResponse.errorMessage)
    Else
       For Each record in databaseResponse.Rows
          addOutput("MSSQL_" & instance_id & "|details|" & record("prodversion") & "|" & _
                    record("prodlevel") & "|" & record("prodedition"))
       Next
    End If

    ' Get counter data for the whole instance
    addOutput(sections("counters"))
    Set databaseResponse = databaseSession.querySystem("SELECT CONVERT(varchar, GETUTCDATE(), 20) as utc_date")
    If databaseResponse.hasError Then
       addOutput("||" & instance_id & "|" & databaseResponse.errorMessage)
    Else
       For Each record in databaseResponse.Rows
          addOutput("None|utc_time|None|" & record("utc_date"))
       Next
    End If

    sqlString = "SELECT counter_name, object_name, instance_name, cntr_value " & _
                " FROM sys.dm_os_performance_counters " & _
                " WHERE object_name NOT LIKE '%Deprecated%'"
    Set databaseResponse = databaseSession.querySystem(sqlString)

    If databaseResponse.hasError Then
        addOutput("||" & instance_id & "|" & databaseResponse.errorMessage)
    Else
        Dim objectName, counterName, counters_inst_name, value
        For Each record in databaseResponse.Rows
            objectName   = Replace(Replace(Trim(record("object_name")), " ", "_"), "$", "_")
            counterName  = LCase(Replace(Trim(record("counter_name")), " ", "_"))
            counters_inst_name = Replace(Trim(record("instance_name")), " ", "_")
            If counters_inst_name = "" Then
                counters_inst_name = "None"
            End If
            value = Trim(record("cntr_value"))
            addOutput( objectName & "|" & counterName & "|" & counters_inst_name & "|" & value )
        Next
    End If

    addOutput(sections("blocked_sessions"))
    sqlString = "SELECT session_id, wait_duration_ms, wait_type, blocking_session_id " & _
                " FROM sys.dm_os_waiting_tasks " & _
                " WHERE blocking_session_id <> 0 "
    Set databaseResponse = databaseSession.querySystem(sqlString)

    If databaseResponse.hasError Then
        addOutput(instance_id & "|" & databaseResponse.errorMessage)
    Elseif UBound(databaseResponse.Rows) + 1 > 0 Then
        Dim session_id, wait_duration_ms, wait_type, blocking_session_id
        For Each record in databaseResponse.Rows
            session_id = Trim(record("session_id"))
            wait_duration_ms = Trim(record("wait_duration_ms"))
            wait_type = Trim(record("wait_type"))
            blocking_session_id = Trim(record("blocking_session_id"))
            addOutput(instance_id & "|" & session_id & "|" & wait_duration_ms & "|" & wait_type & "|" & blocking_session_id)
        Next
    Else
        addOutput(instance_id & "|No blocking sessions")
    End If

    ' First only read all databases in this instance and save it to the db names dict
    Set databaseResponse = databaseSession.querySystem("SELECT NAME AS DATABASE_NAME FROM sys.databases")

    Dim dbName, dbNames
    Set dbNames = CreateObject("Scripting.Dictionary")
    If Not databaseResponse.hasError then
        For Each record in databaseResponse.Rows
           dbName = record("DATABASE_NAME")
           dbNames.add dbName, ""
        Next
    End If

    ' Now gather the db size and unallocated space
    addOutput(sections("tablespaces"))
    Dim dbSize, unallocated, reserved, data, indexSize, unused
    For Each dbName in dbNames.Keys
        Set databaseResponse = databaseSession.queryDatabase(dbName, "EXEC sp_spaceused")

        If databaseResponse.hasError Then
            addOutput("MSSQL_" & instance_id &  " " & Replace(dbName, " ", "_") & _
                      " - - - - - - - - - - - - " & databaseResponse.errorMessage)
        Else
           i = 0
           For Each record in databaseResponse.Rows
              If i = 0 Then
                  ' Size of the current database in megabytes. database_size includes both data and log files.
                  dbSize      = Trim(record("database_size"))
                  ' Space in the database that has not been reserved for database objects.
                  unallocated = Trim(record("unallocated space"))
              Elseif i = 1 Then
                  ' Total amount of space allocated by objects in the database.
                  reserved    = Trim(record("reserved"))
                  ' Total amount of space used by data.
                  data        = Trim(record("data"))
                  ' Total amount of space used by indexes.
                  indexSize   = Trim(record("index_size"))
                  ' Total amount of space reserved for objects in the database, but not yet used.
                  unused      = Trim(record("unused"))
              End If
              i = i + 1
           Next
           addOutput("MSSQL_" & instance_id & " " & Replace(dbName, " ", "_") & " " & dbSize & " " & _
               unallocated & " " & reserved & " " & data & " " & indexSize & " " & unused)
        End If
    Next

    ' Loop all databases to get the date of the last backup. Only show databases
    ' which have at least one backup
    ' The last backup date is converted to UTC in the process by removing the timezone offset, given in 15 min
    ' intervals (or as 127 if unknown)
    Dim lastBackupDate, backup_type, is_primary_replica, replica_id, backup_machine_name, backup_database, found_db_backups
    addOutput(sections("backup"))
    sqlString = "" & _
        "DECLARE @HADRStatus sql_variant; " & _
        "DECLARE @SQLCommand nvarchar(max); " & _
        "SET @HADRStatus = (SELECT SERVERPROPERTY ('IsHadrEnabled')); " & _
        "IF (@HADRStatus IS NULL or @HADRStatus <> 1) " & _
        "BEGIN " & _
        "SET @SQLCommand = ' " & _
            "SELECT " & _
            "  CONVERT(VARCHAR, DATEADD(s, MAX(DATEDIFF(s, ''19700101'', backup_finish_date) - (CASE WHEN time_zone IS NOT NULL AND time_zone <> 127 THEN 60 * 15 * time_zone ELSE 0 END)), ''19700101''), 120) AS last_backup_date, " & _
            "  type, " & _
            "  machine_name, " & _
            "  ''True'' as is_primary_replica, " & _
            "  ''1'' as is_local, " & _
            "  '''' as replica_id, " & _
            "  sys.databases.name AS database_name " & _
            "FROM " & _
            "  msdb.dbo.backupset " & _
            "  LEFT OUTER JOIN sys.databases ON sys.databases.name = msdb.dbo.backupset.database_name " & _
            "WHERE " & _
            "  UPPER(machine_name) = UPPER(CAST(SERVERPROPERTY(''Machinename'') AS VARCHAR)) " & _
            "GROUP BY " & _
            "  type, " & _
            "  machine_name, " & _
            "  sys.databases.name " & _
        "' " & _
        "END " & _
        "ELSE " & _
        "BEGIN " & _
        "SET @SQLCommand = ' " & _
            "SELECT " & _
            "  CONVERT(VARCHAR, DATEADD(s, MAX(DATEDIFF(s, ''19700101'', b.backup_finish_date) - (CASE WHEN time_zone IS NOT NULL AND time_zone <> 127 THEN 60 * 15 * time_zone ELSE 0 END)), ''19700101''), 120) AS last_backup_date," & _
            "  b.type, " & _
            "  b.machine_name, " & _
            "  isnull(rep.is_primary_replica, 0) as is_primary_replica, " & _
            "  rep.is_local, " & _
            "  isnull(convert(varchar(40), rep.replica_id), '''') AS replica_id, " & _
            "  db.name AS database_name " & _
            "FROM " & _
            "  msdb.dbo.backupset b " & _
            "  LEFT OUTER JOIN sys.databases db ON b.database_name = db.name " & _
            "  LEFT OUTER JOIN sys.dm_hadr_database_replica_states rep ON db.database_id = rep.database_id " & _
            "WHERE " & _
            "  (rep.is_local is null or rep.is_local = 1) " & _
            "  AND (rep.is_primary_replica is null or rep.is_primary_replica = ''True'') " & _
            "  AND UPPER(machine_name) = UPPER(CAST(SERVERPROPERTY(''Machinename'') AS VARCHAR)) " & _
            "GROUP BY " & _
            "  type, " & _
            "  rep.replica_id, " & _
            "  rep.is_primary_replica, " & _
            "  rep.is_local, " & _
            "  db.name, " & _
            "  b.machine_name, " & _
            "  rep.synchronization_state, " & _
            "  rep.synchronization_health " & _
        "' " & _
        "END " & _
        "EXEC (@SQLCommand)"
    Set databaseResponse = databaseSession.queryDatabase("master", sqlString)

    Set found_db_backups = CreateObject("Scripting.Dictionary")
    If Not databaseResponse.hasError Then
       ' It's easier to go to each line and take a look to which DB a backup
       ' belongs to than go to every line for each DB as the list of DBs is
       ' most likely shorter than the list of found backups. We track the DB
       ' for which we found a backup to execute the last backup section below.
       For Each record in databaseResponse.Rows
           backup_database = record("database_name")
           If dbNames.Exists(backup_database) Then
               backup_database = Replace(backup_database, " ", "_")
               found_db_backups.add LCase(backup_database), ""

               lastBackupDate = Trim(record("last_backup_date"))
               backup_type = Trim(record("type"))
               If backup_type = "" Then
                   backup_type = "-"
               End If

               replica_id = Trim(record("replica_id"))
               is_primary_replica = Trim(record("is_primary_replica"))
               backup_machine_name = Trim(record("machine_name"))

               If lastBackupDate <> "" and (replica_id = "" or is_primary_replica = "True") Then
                   addOutput("MSSQL_" & instance_id & "|" & backup_database & _
                             "|" & Replace(lastBackupDate, " ", "|") & "+00:00" & "|" & backup_type)
               End If
           End If
       Next
    End If

    ' Since the data is only fetched one time and we may run into an error, we
    ' need to take care, that every DB gets the error message or the hint that
    ' no backup has been found if the RS has been empty or simply no backup for
    ' a DB exists.
    For Each dbName in DbNames.Keys
        backup_database = Replace(dbName, " ", "_")
        If databaseResponse.hasError Then
            addOutput("MSSQL_" & instance_id & "|" & backup_database & "|-|-|-|" & databaseResponse.errorMessage)
        End If
        If Not found_db_backups.Exists(LCase(backup_database)) Then
            addOutput("MSSQL_" & instance_id & "|" & backup_database & "|-|-|-|no backup found")
        End If
    Next


    ' Loop all databases to get the size of the transaction log
    addOutput(sections("transactionlogs"))
    sqlString = "SELECT name, physical_name," &_
                "  cast(max_size/128 as bigint) as MaxSize," &_
                "  cast(size/128 as bigint) as AllocatedSize," &_
                "  cast(FILEPROPERTY (name, 'spaceused')/128 as bigint) as UsedSize," &_
                "  case when max_size = '-1' then '1' else '0' end as Unlimited" &_
                " FROM sys.database_files WHERE type_desc = 'LOG'"
    For Each dbName in dbNames.Keys
       Set databaseResponse = databaseSession.queryDatabase(dbName, sqlString)

        If databaseResponse.hasError Then
            addOutput(instance_id &  "|" & Replace(dbName, " ", "_") & _
                      "|-|-|-|-|-|-|" & databaseResponse.errorMessage)
        Else
           For Each record in databaseResponse.Rows
                addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & Replace(record("name"), " ", "_") & _
                          "|" & Replace(record("physical_name"), " ", "_") & "|" & _
                          record("MaxSize") & "|" & record("AllocatedSize") & "|" & record("UsedSize")) & _
                          "|" & record("Unlimited")
           Next
        End If
    Next

    ' Loop all databases to get the size of the transaction log
    addOutput(sections("datafiles"))
    sqlString = "SELECT name, physical_name," &_
                "  cast(max_size/128 as bigint) as MaxSize," &_
                "  cast(size/128 as bigint) as AllocatedSize," &_
                "  cast(FILEPROPERTY (name, 'spaceused')/128 as bigint) as UsedSize," &_
                "  case when max_size = '-1' then '1' else '0' end as Unlimited" &_
                " FROM sys.database_files WHERE type_desc = 'ROWS'"
    For Each dbName in dbNames.Keys
       Set databaseResponse = databaseSession.queryDatabase(dbName, sqlString)

        If databaseResponse.hasError Then
            addOutput(instance_id &  "|" & Replace(dbName, " ", "_") & _
                      "|-|-|-|-|-|-|" & databaseResponse.errorMessage)
        Else
           For Each record in databaseResponse.Rows
                addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & Replace(record("name"), " ", "_") & _
                          "|" & Replace(record("physical_name"), " ", "_") & "|" & _
                          record("MaxSize") & "|" & record("AllocatedSize") & "|" & record("UsedSize")) & _
                          "|" & record("Unlimited")
           Next
        End If
    Next

    ' Database properties, full list at https://msdn.microsoft.com/en-us/library/ms186823.aspx
    addOutput(sections("databases"))
    sqlString = "SELECT name, " & _
                "  DATABASEPROPERTYEX(name, 'Status') AS Status, " & _
                "  DATABASEPROPERTYEX(name, 'Recovery') AS Recovery, " & _
                "  DATABASEPROPERTYEX(name, 'IsAutoClose') AS auto_close, " & _
                "  DATABASEPROPERTYEX(name, 'IsAutoShrink') AS auto_shrink " & _
                " FROM master.dbo.sysdatabases"
    Set databaseResponse = databaseSession.querySystem(sqlString)
    If databaseResponse.hasError Then
        For Each dbName in dbNames.Keys
            addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & databaseResponse.errorMessage & "|-|-|-")
        Next
    Else
       For Each record in databaseResponse.Rows
            ' instance db_name status recovery auto_close auto_shrink
            addOutput(instance_id & "|" & Replace(record("name"), " ", "_") & "|" & Trim(record("Status")) & _
                      "|" & Trim(record("Recovery")) & "|" & Trim(record("auto_close")) & "|" & Trim(record("auto_shrink")) )
        Next
    End If

    addOutput(sections("clusters"))
    Dim active_node, nodes
    For Each dbName in dbNames.Keys : Do
       Set databaseResponse = databaseSession.queryDatabase(dbName, "SELECT SERVERPROPERTY('IsClustered') AS is_clustered")
       If databaseResponse.hasError Then
          addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|||" & databaseResponse.errorMessage)
          Exit Do
       End If

       ' Skip non cluster instances
       For Each record in databaseResponse.Rows
          If record("is_clustered") = 0 Then
             Exit Do
          End If
       Next

       Set databaseResponse = databaseSession.queryDatabase(dbName, "SELECT nodename FROM sys.dm_os_cluster_nodes")
       If databaseResponse.hasError Then
          addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|||" & databaseResponse.errorMessage)
          Exit Do
       End If

       nodes = ""
       For Each record in databaseResponse.Rows
           If nodes <> "" Then
               nodes = nodes & ","
           End If
           nodes = nodes & record("nodename")
       Next

       Set databaseResponse = databaseSession.queryDatabase(dbName, "SELECT SERVERPROPERTY('ComputerNamePhysicalNetBIOS') AS active_node")
       If databaseResponse.hasError Then
          addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|||" & databaseResponse.errorMessage)
          Exit Do
       End If

       active_node = "-"
       For Each record in databaseResponse.Rows
           active_node = record("active_node")
       Next

       addOutput(instance_id & "|" & Replace(dbName, " ", "_") & "|" & active_node & "|" & nodes)
    Loop While False: Next

    addOutput(sections("connections"))
    Dim connection_count, database_name

    sqlString = "SELECT name AS DBName, ISNULL((SELECT  COUNT(dbid) AS NumberOfConnections FROM " &_
                " sys.sysprocesses WHERE dbid > 0 AND name = DB_NAME(dbid) GROUP BY dbid ),0) AS NumberOfConnections " &_
                " FROM sys.databases"
    Set databaseResponse = databaseSession.querySystem(sqlString)

    If databaseResponse.hasError Then
        addOutput(instance_id & " " & databaseResponse.errorMessage)
    Else
       For Each record in databaseResponse.Rows
           database_name = record("DBName")
           connection_count = record("NumberOfConnections")

           addOutput(instance_id & " " & Replace(database_name, " ", "_") & " " & connection_count)
       Next
    End If

    addOutput(sections("jobs"))
    sqlString = "SELECT " &_
                "   sj.job_id " &_
                "  ,sj.name AS job_name " &_
                "  ,sj.enabled AS job_enabled " &_
                "  ,CAST(sjs.next_run_date AS VARCHAR(8)) AS next_run_date " &_
                "  ,CAST(sjs.next_run_time AS VARCHAR(6)) AS next_run_time " &_
                "  ,sjserver.last_run_outcome " &_
                "  ,sjserver.last_outcome_message " &_
                "  ,CAST(sjserver.last_run_date AS VARCHAR(8)) AS last_run_date " &_
                "  ,CAST(sjserver.last_run_time AS VARCHAR(6)) AS last_run_time " &_
                "  ,sjserver.last_run_duration " &_
                "  ,ss.enabled AS schedule_enabled " &_
                "  ,CONVERT(VARCHAR, CURRENT_TIMESTAMP, 20) AS server_current_time " &_
                " FROM dbo.sysjobs sj " &_
                " LEFT JOIN dbo.sysjobschedules sjs ON sj.job_id = sjs.job_id " &_
                " LEFT JOIN dbo.sysjobservers sjserver ON sj.job_id = sjserver.job_id " &_
                " LEFT JOIN dbo.sysschedules ss ON sjs.schedule_id = ss.schedule_id " &_
                " ORDER BY sj.name " &_
                "          ,sjs.next_run_date ASC " &_
                "          ,sjs.next_run_time ASC " &_
                "; "
    Set databaseResponse = databaseSession.queryDatabase("msdb", sqlString)

    If databaseResponse.hasError Then
        addOutput(instance_id & " " & databaseResponse.errorMessage)
    Else
       addOutput(instance_id)
       For Each record in databaseResponse.rows
           addOutput(Join(record.Items, vbTab))
       Next
    End If

    addOutput(sections("mirroring"))
    sqlString = "SELECT @@SERVERNAME as server_name, " &_
                "  DB_NAME(database_id) AS [database_name], " &_
                "  mirroring_state, " &_
                "  mirroring_state_desc, " &_
                "  mirroring_role, " &_
                "  mirroring_role_desc, " &_
                "  mirroring_safety_level, " &_
                "  mirroring_safety_level_desc, " &_
                "  mirroring_partner_name, " &_
                "  mirroring_partner_instance, " &_
                "  mirroring_witness_name, " &_
                "  mirroring_witness_state, " &_
                "  mirroring_witness_state_desc " &_
                " FROM sys.database_mirroring " &_
                " WHERE mirroring_state IS NOT NULL " &_
                "; "
    Set databaseResponse = databaseSession.queryDatabase("master", sqlString)

    If databaseResponse.hasError Then
        addOutput(instance_id & " " & databaseResponse.errorMessage)
    Else
       addOutput(instance_id)
       For Each record in databaseResponse.Rows
           addOutput(Join(record.Items, vbTab))
       Next
    End If

    addOutput(sections("availability_groups"))
    sqlString = "SELECT " &_
                "  GroupsName.name, " &_
                "  Groups.primary_replica, " &_
                "  Groups.synchronization_health, " &_
                "  Groups.synchronization_health_desc, " &_
                "  Groups.primary_recovery_health_desc " &_
                " FROM sys.dm_hadr_availability_group_states Groups " &_
                " INNER JOIN master.sys.availability_groups GroupsName ON Groups.group_id = GroupsName.group_id "
    Set databaseResponse = databaseSession.querySystem(sqlString)

    If databaseResponse.hasError Then
        addOutput(instance_id & " " & databaseResponse.errorMessage)
    Else
       For Each record in databaseResponse.Rows
           addOutput(Join(record.Items, vbTab) & vbCrLf)
       Next
    End If

    databaseSession.terminateConnection

Loop While False: Next

databaseSession.terminateSession

Set sources = nothing
Set instances = nothing
Set sections = nothing
Set FSO = nothing
Set SHO = nothing
Set DATABASE_CONNECTION_PROVIDERS = Nothing
Set databaseSession = Nothing
Set databaseResponse = Nothing
Set record = Nothing
Set sqlString = Nothing
