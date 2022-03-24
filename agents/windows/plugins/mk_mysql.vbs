' Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
' This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
' conditions defined in the file COPYING, which is part of this source code package.

' This agent plugin is meant to be used on a windows server which
' is running one or multiple MySQL server instances locally.

Option Explicit
Const CMK_VERSION = "2.1.0b4"

Dim SHO, FSO, WMI, PROC
Dim cfg_dir, cfg_file, service_list, service, instances, instance, cmd
Dim output, pos, conn_args

Set instances = CreateObject("Scripting.Dictionary")
Set FSO = CreateObject("Scripting.FileSystemObject")
Set SHO = CreateObject("WScript.Shell")

cfg_dir = SHO.ExpandEnvironmentStrings("%MK_CONFDIR%")

'
' First detect all local instances. We only add services of instances
' which service is currently reported as running
'

Set WMI = GetObject("winmgmts:{impersonationLevel=impersonate}!\\.\root\cimv2")
Set service_list = WMI.ExecQuery("SELECT * FROM Win32_Service WHERE (Name LIKE '%MySQL%' or Name LIKE '%MariaDB') and State = 'Running'")
For Each service in service_list
    ' add the internal service name as key and the launch command line as value
    instances.add service.Name, service.PathName
Next

Set WMI = Nothing

'
' Now query these instances
'

' don't blame me for the stupid tempfile. I am aware of SHO.Exec, but in context of
' the agent this lead into strang hanging process problems. Propably because of some
' filled buffer or whatever. Could not get this working. But SHO.Run works fine.
Sub Run(cmd)
    Dim FILE, tmp_file
    tmp_file = "mk_mysql.out"
    SHO.Run "cmd.exe /s /c "" " & cmd & " 1>>" & tmp_file & " 2>&1 """, 0, 1
    Set FILE = FSO.GetFile(tmp_file)
    If FILE.size <> 0 Then
        wscript.echo FSO.OpenTextFile(tmp_file, 1).ReadAll()
    End If
    FILE.Delete()
    Set FILE = Nothing
End Sub

For Each instance In instances.Keys
    ' Use either an instance specific config file named mysql_<instance-id>.ini
    ' or the default mysql.ini file.
    cfg_file = cfg_dir & "\mysql_" & instance & ".ini"
    If Not fso.FileExists(cfg_file) Then
        cfg_file = cfg_dir & "\mysql.ini"
        If Not fso.FileExists(cfg_file) Then
            cfg_file = ""
        End If
    End If

    ' Now detect the correct socket / port to connect to this instance. This can be done by executing
    ' mysql.exe with the --defaults-file found in the command line of the windows process together
    ' with the option --print-defaults
    cmd = instances.Item(instance)
    cmd = Replace(cmd, "mysqld.exe", "mysql.exe")
    cmd = Replace(cmd, "mysqld-nt.exe", "mysql.exe")
    cmd = Left(cmd, InStrRev(cmd, " ")) & " --print-defaults"
    Set PROC = SHO.Exec(cmd)
    PROC.StdIn.Close()
    PROC.StdErr.Close()
    output = PROC.StdOut.ReadAll()
    pos = InStrRev(output, vbCrLf, Len(output)-1)
    conn_args = Mid(output, pos+2, Len(output)-pos-4)

    Dim RegEx : Set RegEx = New RegExp
    RegEx.Pattern = "(--port=.*?) "

    If RegEx.Test(conn_args) Then
        conn_args = RegEx.Execute(conn_args)(0).SubMatches(0)
    Else
        conn_args = ""
    End If

    ' Now we try to construct a mysql.exe client command which is able to connect to this database
    ' based on the command uses by the database service.
    ' In our development setup, where MySQL 5.6 has been used, the server command is:
    ' "C:\Programme\MySQL\MySQL Server 5.6\bin\mysqld.exe" --defaults-file="C:\Dokumente und Einstellungen\All Users\Anwendungsdaten\MySQL\MySQL Server 5.6\my.ini" MySQL56
    ' To get the client command we simply need to replace mysqld.exe with mysql.exe, remove the
    ' my.ini and instance name from the end of the command and add our config as --defaults-extra-file.
    cmd = instances.Item(instance)
    cmd = Replace(cmd, "mysqld""", "mysql""")
    cmd = Replace(cmd, "mysqld-nt""", "mysql""")
    cmd = Replace(cmd, "mysql""", "mysql.exe""")
    cmd = Replace(cmd, "mysqld.exe""", "mysql.exe""")
    If InStr(cmd, "mysql.exe""") = 0 Then
        ' replace failed, probably we have no double quotes in the string
        cmd = Replace(cmd, "mysqld.exe", "mysql.exe")
        cmd = Left(cmd, InStr(cmd, "mysql.exe")+8)
    else
        cmd = Left(cmd, InStr(cmd, "mysql.exe""")+9)
    End If
    If cfg_file <> "" Then
        cmd = cmd & " --defaults-extra-file=""" & cfg_file & """"
    End If
    cmd = cmd & " " & conn_args

    wscript.echo "<<<mysql_ping>>>"
    wscript.echo "[[" & instance & "]]"
    Run Replace(cmd, "mysql.exe", "mysqladmin.exe") & " ping"

    wscript.echo "<<<mysql>>>"
    wscript.echo "[[" & instance & "]]"
    Run cmd & " -B -sN -e ""show global status ; show global variables ;"""

    wscript.echo "<<<mysql_capacity>>>"
    wscript.echo "[[" & instance & "]]"
    Run cmd & " -B -sN -e ""SELECT table_schema, sum(data_length + index_length), sum(data_free)" & _
               "FROM information_schema.TABLES GROUP BY table_schema"""

    wscript.echo "<<<mysql_slave>>>"
    wscript.echo "[[" & instance & "]]"
    Run cmd & " -B -s -e ""show slave status\G"""
Next

Set SHO = Nothing
Set FSO = Nothing
