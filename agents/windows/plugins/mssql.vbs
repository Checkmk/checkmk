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
' [auth]
' type = db
' username = monitoring
' password = secret-pw
'
' The following sources are asked:
' 1. WMI - to gather a list of local MSSQL-Server instances
' 2. MSSQL-Servers via ADO/sqloledb connection to gather infos these infos:
'      a) list and sizes of available databases
'      b) counters of the database instance
'
' This check has been developed with MSSQL Server 2008 R2. It should work with
' older versions starting from at least MSSQL Server 2005.
' -----------------------------------------------------------------------------

Option Explicit

Dim WMI, FSO, SHO, items, objItem, prop, instId, instIdx, instVersion
Dim instIds, instName, output, isClustered, instServers
Dim WMIservice, colRunningServices, objService, cfg_dir, cfg_file, hostname

' Directory of all database instance names
Set instIds = CreateObject("Scripting.Dictionary")
Set FSO = CreateObject("Scripting.FileSystemObject")
Set SHO = CreateObject("WScript.Shell")

hostname = SHO.ExpandEnvironmentStrings("%COMPUTERNAME%")
cfg_dir = SHO.ExpandEnvironmentStrings("%MK_CONFDIR%")

output = ""
Sub addOutput(text)
    output = output & text & vbLf
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
    End If
    Set readIniFile = parsed
End Function

' Detect whether or not the script is called in a clustered environment.
' Saves the virtual server names of the DB instances
Set instServers = CreateObject("Scripting.Dictionary")
On Error Resume Next
Set WMI = GetObject("WINMGMTS:\\.\root\mscluster")
Set items = WMI.execQuery("SELECT Name, Status, State, Type, PrivateProperties " & _
                          "FROM MsCluster_Resource WHERE Type = 'SQL Server'")
For Each objItem in items
    instName = objItem.PrivateProperties.InstanceName
    instServers(instName) = objItem.PrivateProperties.VirtualServerName
Next

If Err.Number <> 0 Then
    Err.Clear()
    isClustered = FALSE
Else
    isClustered = TRUE
End If
On Error Goto 0

' Dummy empty output.
' Contains timeout error if this scripts runtime exceeds the timeout
WScript.echo "<<<mssql_versions>>>"

' Loop all found local MSSQL server instances
' Try different trees to handle different versions of MSSQL
On Error Resume Next
' try SQL Server 2016:
Set WMI = GetObject("WINMGMTS:\\.\root\Microsoft\SqlServer\ComputerManagement13")
If Err.Number <> 0 Then
    Err.Clear()
	' try SQL Server 2014:
	Set WMI = GetObject("WINMGMTS:\\.\root\Microsoft\SqlServer\ComputerManagement12")
	If Err.Number <> 0 Then
		Err.Clear()
		' try SQL Server 2012:
		Set WMI = GetObject("WINMGMTS:\\.\root\Microsoft\SqlServer\ComputerManagement11")
		If Err.Number <> 0 Then
			Err.Clear()

			' try SQL Server 2008
			Set WMI = GetObject("WINMGMTS:\\.\root\Microsoft\SqlServer\ComputerManagement10")
			If Err.Number <> 0 Then
				Err.Clear()

				' try MSSQL < 10
				Set WMI = GetObject("WINMGMTS:\\.\root\Microsoft\SqlServer\ComputerManagement")
				If Err.Number <> 0 Then
					WScript.echo "Error: " & Err.Number & " " & Err.Description
					Err.Clear()
					wscript.quit()
				End If
			End If
		End If
	End If
End If
On Error Goto 0

Set WMIservice = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")

For Each prop In WMI.ExecQuery("SELECT * FROM SqlServiceAdvancedProperty WHERE " & _
                               "SQLServiceType = 1 AND PropertyName = 'VERSION'")


    Set colRunningServices = WMIservice.ExecQuery("SELECT State FROM Win32_Service " & _
                                                  "WHERE Name = '" & prop.ServiceName & "'")
    instId      = Replace(prop.ServiceName, "$", "__")
    instVersion = prop.PropertyStrValue
    instIdx = Replace(instId, "__", "_")
    addOutput( "<<<mssql_versions>>>" )
    addOutput( instIdx & "  " & instVersion )

    ' Now query the server instance for the databases
    ' Use name as key and always empty value for the moment
    For Each objService In colRunningServices
        If objService.State = "Running" Then
            instIds.add instId, ""
        End If
    Next
Next

Set WMI = nothing

Dim CONN, RS, CFG, AUTH

' Initialize connection objects
Set CONN = CreateObject("ADODB.Connection")
Set RS = CreateObject("ADODB.Recordset")
CONN.Provider = "sqloledb"

' Loop all found server instances and connect to them
' In my tests only the connect using the "named instance" string worked
For Each instId In instIds.Keys
    ' Use either an instance specific config file named mssql_<instance-id>.ini
    ' or the default mysql.ini file.
    cfg_file = cfg_dir & "\mssql_" & instId & ".ini"
    If Not FSO.FileExists(cfg_file) Then
        cfg_file = cfg_dir & "\mssql.ini"
        If Not FSO.FileExists(cfg_file) Then
            cfg_file = ""
        End If
    End If

    Set CFG = readIniFile(cfg_file)
    If Not CFG.Exists("auth") Then
        Set AUTH = CreateObject("Scripting.Dictionary")
    Else
        Set AUTH = CFG("auth")
    End If

    ' At this place one could implement to use other authentication mechanism
    If Not AUTH.Exists("type") or AUTH("type") = "system" Then
        CONN.Properties("Integrated Security").Value = "SSPI"
    Else
        CONN.Properties("User ID").Value = AUTH("username")
        CONN.Properties("Password").Value = AUTH("password")
    End If

    If InStr(instId, "__") <> 0 Then
        instName = Split(instId, "__")(1)
    instId = Replace(instId, "__", "_")
    Else
        instName = instId
    End If

    ' In case of instance name "MSSQLSERVER" always use (local) as connect string
    If Not isClustered Then
        If instName = "MSSQLSERVER" Then
            CONN.Properties("Data Source").Value = "(local)"
        Else
            CONN.Properties("Data Source").Value = hostname & "\" & instName
        End If
    Else
        ' In case the instance name is "MSSQLSERVER" always use the virtual server name
        If instName = "MSSQLSERVER" Then
            CONN.Properties("Data Source").Value = instServers(instName)
        Else
            CONN.Properties("Data Source").Value = instServers(instName) & "\" & instName
        End If
    End If

    CONN.Open

    ' Get counter data for the whole instance
    RS.Open "SELECT counter_name, object_name, instance_name, cntr_value " & _
            "FROM sys.dm_os_performance_counters " & _
            "WHERE object_name NOT LIKE '%Deprecated%'", CONN
    addOutput( "<<<mssql_counters>>>" )
    Dim objectName, counterName, instanceName, value
    Do While NOT RS.Eof
        objectName   = Replace(Replace(Trim(RS("object_name")), " ", "_"), "$", "_")
        counterName  = LCase(Replace(Trim(RS("counter_name")), " ", "_"))
        instanceName = Replace(Trim(RS("instance_name")), " ", "_")
        If instanceName = "" Then
            instanceName = "None"
        End If
        value        = Trim(RS("cntr_value"))
        addOutput( objectName & " " & counterName & " " & instanceName & " " & value )
        RS.MoveNext
    Loop
    RS.Close

    RS.Open "SELECT session_id, wait_duration_ms, wait_type, blocking_session_id " & _
            "FROM sys.dm_os_waiting_tasks " & _
            "WHERE blocking_session_id <> 0 ", CONN
    addOutput( "<<<mssql_blocked_sessions>>>" )
    Dim session_id, wait_duration_ms, wait_type, blocking_session_id
    Do While NOT RS.Eof
        session_id = Trim(RS("session_id"))
        wait_duration_ms = Trim(RS("wait_duration_ms"))
        wait_type = Trim(RS("wait_type"))
        blocking_session_id = Trim(RS("blocking_session_id"))
        addOutput( session_id & " " & wait_duration_ms & " " & wait_type & " " & blocking_session_id  )
        RS.MoveNext
    Loop
    RS.Close

    ' First only read all databases in this instance and save it to the db names dict
    RS.Open "EXEC sp_databases", CONN
    Dim x, dbName, dbNames
    Set dbNames = CreateObject("Scripting.Dictionary")
    Do While NOT RS.Eof
        dbName = RS("DATABASE_NAME")
        dbNames.add dbName, ""
       RS.MoveNext
    Loop
    RS.Close

    ' Now gather the db size and unallocated space
    addOutput( "<<<mssql_tablespaces>>>" )
    Dim i, dbSize, unallocated, reserved, data, indexSize, unused
    For Each dbName in dbNames.Keys
        ' Switch to other database and then ask for stats
        RS.Open "USE [" & dbName & "]", CONN
        ' sp_spaceused is a stored procedure which returns two selects
        ' which need to be looped
        RS.Open "EXEC sp_spaceused", CONN
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
        addOutput( instId & " " & Replace(dbName, " ", "_") & " " & dbSize & " " & unallocated & " " & reserved & " " & _
                     data & " " & indexSize & " " & unused )
        Set RS = CreateObject("ADODB.Recordset")
    Next

    ' Loop all databases to get the date of the last backup. Only show databases
    ' which have at least one backup
    Dim lastBackupDate
    addOutput( "<<<mssql_backup>>>" )
    For Each dbName in dbNames.Keys
        RS.open "SELECT CONVERT(VARCHAR, DATEADD(s, DATEDIFF(s, '19700101', MAX(backup_finish_date)), '19700101'), 120) AS last_backup_date " & _
                "FROM msdb.dbo.backupset " & _
                "WHERE database_name = '" & dbName & "'", CONN
        Do While Not RS.Eof
            lastBackupDate = Trim(RS("last_backup_date"))
            If lastBackupDate <> "" Then
                addOutput( instId & " " & Replace(dbName, " ", "_") & " " & lastBackupDate )
            End If
            RS.MoveNext
        Loop
        RS.Close
    Next

    CONN.Close
Next

Set RS = nothing
Set CONN = nothing
Set FSO = nothing
Set SHO = nothing

' finally output collected data
WScript.echo output
