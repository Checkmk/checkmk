' Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
' This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
' conditions defined in the file COPYING, which is part of this source code package.

' -----------------------------------------------------------------------------
' Windows active check for monitoring a mail loop by using Outlook (via MAPI)
'
' Unlike the default check_mail_loop active check which can be configured using
' Check_MK WATO that is directly using SMTP and (IMAP/POP3), this check is 
' executed as MRPE plugin on a Windows host. It uses the Outlook installation 
' and configured profile to send and receive mails via MAPI.
'
' So you have to run the agent (this plugin) in the context of a user which has
' a Outlook profile configured.
'
' Here is an example command line you can use to run this script manually:
'
'  cscript check_mail_loop.vbs /mail-to:my-local-mail-address@my-domain.de /delete-messages
'
' To configure the MRPE plugin in the Check_MK agent, you need to do several things:
'
'   1. Configure the script execution via check_mk.ini
'   2. Ensure access to the outlook profile
'   3. Adapt the Outlook security settings to allow such script actions
'
' For the first step, yoy can add this snippet to the check_mk.ini:
' 
' [mrpe]
'     check = Mail_Loop C:\Windows\System32\cscript.exe /NoLogo "C:\Program Files (x86)\check_mk\mrpe\check_mail_loop.vbs" /mail-to:my-local-mail-address@my-domain.de /delete-messages
'
' Second step: The script needs to be executed in the context of the Outlook profiles
' user you want to use. This can be reached in different ways. One is to simply
' make the service be executed in the context of the needed user. Another option
' would be to wrap the cscript.exe command in a runas.exe call, which can be used
' to switch the user context.
' In the later case, please make sure that the user the agent is executed with has
' the permission to switch the user context without entering the other users password.
' Otherwise the agent will get stuck.
' In you test we used the first approach. Go to services management and change the
' logon credentials of the "Check_MK Agent" service and restart it.
'
' Third step: Outlook has a security feature built-in which pops up a confirm window
' when this script is trying to send out the mail using outlook. This can not be
' fixed within this script. You will have to configure your system not to raise such
' warnings. The easiest approach would be:
'
' a) Logon as the Outlook profile owner
' b) Stop all Outlook instances
' c) Start Outlook with Administrative credentials
' d) Go to the top left dropdown menu "File" and choose "Options"
' e) Then navigate to the dialog "Trust Center > Settings for Trust Center"
' f) Here you should see a menu item "Programmatic Access". Select it and
'    choose "Never warn me about suspicious activity".
' g) Save the change, confirm all other dialogs and quit Outlook.
'
' You will have to restart the Check_MK service to apply your changes.
'
' Now, if you peform a service discovery of the host you configured from your Check_MK
' installation, you should get a new service "Mail_Loop" added to the host.
'
' This plugin has been developed on Windows 10 with Outlook 2013, but should
' work with other versions too.
' -----------------------------------------------------------------------------

' +------------------------------------------------------------------+
' |             ____ _               _        __  __ _  __           |
' |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
' |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
' |           | |___| | | |  __/ (__|   <    | |  | | . \            |
' |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
' |                                                                  |
' | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
' +------------------------------------------------------------------+
'
' This file is part of Check_MK.
' The official homepage is at http://mathias-kettner.de/check_mk.
'
' check_mk is free software;  you can redistribute it and/or modify it
' under the  terms of the  GNU General Public License  as published by
' the Free Software Foundation in version 2.  check_mk is  distributed
' in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
' out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
' PARTICULAR PURPOSE. See the  GNU General Public License for more de-
' ails.  You should have  received  a copy of the  GNU  General Public
' License along with GNU Make; see the file  COPYING.  If  not,  write
' to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
' Boston, MA 02110-1301 USA.
'
' -----------------------------------------------------------------------------
' Windows active check for monitoring a mail loop by using Outlook
'
' Unlike the default check_mail_loop active check which can be configured using
' Check_MK WATO that is directly using SMTP and (IMAP/POP3), this check is 
' executed as MRPE plugin on a Windows host. It uses the Outlook installation 
' and configured profile to send and receive mails.
'
' So you have to run the agent (this plugin) in the context of a user which has
' a Outlook profile configured.
'
' Example command line to use this script:
'
'  cscript check_mail_loop.vbs /mail-to:my-local-mail-address@my-domain.de /delete-messages
'
' To configure the MRPE plugin in the Check_MK agent, you can add this snippet to
' the check_mk.ini:
'
' 
' [mrpe]
'     check = Mail_Loop C:\Windows\System32\cscript.exe /NoLogo "C:\Program Files (x86)\check_mk\mrpe\check_mail_loop.vbs" /mail-to:my-local-mail-address@my-domain.de /delete-messages
'
' In case you don't run execute the Check_MK service as the user which has the mail
' profile configured locally, you will have to either execute the agent in the context
' of that user (which can be configured in the properties of the Check_MK service) or
' add the runas command to the MRPE commad line above.
' In the later case, please make sure that the user the agent is executed with has
' the permission to switch the user context without entering the other users password.
' Otherwise the agent will get stuck.
'
' BE AWARE: Outlook has a security feature built-in which pops up a confirm window
' when this script is trying to send out the mail using outlook. This can not be
' fixed within this script. You will have to configure either your system not to
' raise such warnings or sign this script which makes the system trust the script
' and will not pop up the confirm window.
'
' See for details: http://www.msxfaq.de/code/olkvbscript.htm
'                  http://www.msxfaq.de/code/olksecurity.htm
'
' The approach to sign the script and use the signed version was not successful on
' our test system. We had to alter some outlook security settings on the test
' system. The progress was: Start Outlook as administrative user, go to
' Options > Trust Center > Settings for Trust Center > Programmatical Access
'
' This plugin has been developed on Windows 10 with Outlook 2013, but should
' work with other versions too.
' -----------------------------------------------------------------------------

Option Explicit

Dim g_state, g_output, g_perfdata, g_state_path
Dim g_to, g_subject, g_warning, g_critical, g_delete_messages, g_verbose

Dim obj_fs, obj_wsh, obj_expected_mails, obj_mails, obj_outlook, obj_mapi, obj_inbox
Dim obj_obsolete_mails

Set obj_fs = CreateObject("Scripting.FileSystemObject")
set obj_wsh = CreateObject("WScript.Shell")
Set obj_expected_mails = CreateObject("Scripting.Dictionary")
Set obj_mails = CreateObject("Scripting.Dictionary")
Set obj_obsolete_mails = CreateObject("Scripting.Dictionary")


' Debug code to get account info
'Dim oAccount
'For Each oAccount In obj_outlook.Session.Accounts
'    wscript.echo oAccount.DisplayName
'Next

' Always use the %TEMP% path, because %MK_STATEDIR% can not be written by
' regular users which have normally the Outlook profile configured.
g_state_path = obj_wsh.ExpandEnvironmentStrings("%TEMP%")

g_to = ""
g_subject = "Check_MK-Mail-Loop"
g_warning = -1
g_critical = 3600
g_verbose = false
g_delete_messages = false

g_state    = 0
g_output   = ""
g_perfdata = ""


' -----------------------------------------------------------------------------
' FUNCTIONS
' -----------------------------------------------------------------------------

Sub bail_out(msg)
    If msg <> "" Then
        wscript.echo("ERROR: " & msg)
        wscript.echo
    End If
    wscript.echo "USAGE: cscript check_mail_loop.vbs /mail-to:ADDR [OPTIONS]"
    wscript.echo ""
    wscript.echo "OPTIONS:"
    wscript.echo "  /subject:SUBJECT   Specify a custom subject keyword to use. Defaults to '"&g_subject&"'."
    wscript.echo "  /critical:SECONDS  Specify the maximum allowed time between send and receive "
    wscript.echo "                     of a mail. Defaults to " &g_critical&" seconds."
    wscript.echo "  /warning:SECONDS   Specify the maximum allowed time between send and receive "
    wscript.echo "                     of a mail. Disabled by default."
    wscript.echo "  /delete-messages   Delete all messages identified as being related to this "
    wscript.echo "                     check plugin. This is disabled by default, which"
    wscript.echo "                     might make your mailbox grow when you not clean it up"
    wscript.echo "                     manually."
    wscript.echo "  /verbose           Enable verbose output for debugging."
    wscript.echo ""
    wscript.quit(3)
End Sub


Sub verbose(msg)
    If g_verbose Then
        wscript.echo msg
    End If
End Sub


Sub get_arguments
    Dim obj_args
    Set obj_args = WScript.Arguments.Named

    g_to = obj_args.Item("mail-to")
    If g_to = "" Then
        bail_out("You need to specify the /mail-to:... parameter")
    End If
    
    If obj_args.Exists("subject") Then
        g_subject = obj_args.Item("subject")
        If g_subject = "" Then
            bail_out("You need to specify the /subject:... parameter")
        End If
    End If
    
    If InStr(g_subject, " ") <> 0 Then
        bail_out("The subject must not contain spaces")
    End If
    
    If obj_args.Exists("critical") Then
        g_critical = obj_args.Item("critical")
        If g_critical = "" Then
            bail_out("You need to specify the /critical:... parameter")
        End If
        If Not IsNumeric(g_critical) Then
            bail_out("The /criticial:... parameter needs to be a number")
        End If
        g_critical = CInt(g_critical)
    End If
    
    If obj_args.Exists("warning") Then
        g_warning = obj_args.Item("warning")
        If g_warning = "" Then
            bail_out("You need to specify the /warning:... parameter")
        End If
        If Not IsNumeric(g_warning) Then
            bail_out("The /warning:... parameter needs to be a number")
        End If
        g_warning = CInt(g_warning)
    End If
    
    If obj_args.Exists("delete-messages") Then
        g_delete_messages = true
    End If
    
    If obj_args.Exists("verbose") Then
        g_verbose = true
    End If
    
    If obj_args.Exists("help") Then
        bail_out("")
    End If
End Sub

Sub initialize_outlook
    verbose("Loading Outlook application")
    On Error Resume Next
    Set obj_outlook = CreateObject("Outlook.Application")
    If Err.Number <> 0 Then
        bail_out("Failed to load Outlook (" & Err.Number & "): " & Err.Description)
    End If
    On Error GoTo 0
    verbose("Finished loading Outlook")

    Set obj_mapi = obj_outlook.GetNameSpace("MAPI")
    verbose("Finished loading MAPI")
End Sub


Sub load_expected_mails
    Dim obj_fh, line, pair
    
    If Not obj_fs.FileExists(g_state_path & "\check_mail_loop_expected.txt") Then
        Exit Sub
    End If
    
    Set obj_fh = obj_fs.OpenTextFile(g_state_path & "\check_mail_loop_expected.txt")
    
    Do Until obj_fh.AtEndOfStream
        line = obj_fh.ReadLine()
        pair = Split(line, " ")
        add_expected_mail(pair)
    Loop
    
    obj_fh.Close
    Set obj_fh = Nothing
End Sub


Sub add_output(txt)
    g_output = g_output & txt
End Sub


Sub add_output_front(txt)
    g_output = txt & g_output
End Sub


' Argument: Array of two elements: timestamp, key
Sub add_expected_mail(pair)
    obj_expected_mails.Add pair(0) & " " & pair(1), pair
End Sub


' Argument 1: Array of two elements: timestamp, key
Sub add_mail(pair, obj_mail)
    obj_mails.Add pair(0) & " " & pair(1), obj_mail
End Sub

' Argument 1: Array of two elements: timestamp, key
Sub add_obsolete_mail(pair, obj_mail)
    obj_obsolete_mails.Add pair(0) & " " & pair(1), obj_mail
End Sub

Function mail_in_inbox(key)
    mail_in_inbox = obj_mails.Exists(key)
End Function


Function mail_is_expected(pair)
    mail_is_expected = obj_expected_mails.Exists(pair(0) & " " & pair(1))
End Function


Sub save_expected_mails
    Dim obj_fh, key
    Set obj_fh = obj_fs.CreateTextFile(g_state_path & "\check_mail_loop_expected.txt", True)
    
    For Each key In obj_expected_mails
        obj_fh.writeLine key
    Next
    
    obj_fh.Close
    Set obj_fh = Nothing
End Sub


Sub update_mailbox
    ' Update the mailbox
    'obj_mapi.Logon
    'obj_mapi.SendAndReceive(False)
    'Wscript.Sleep 2000
    
    Dim objSyncs, objSync, i
    Set objSyncs = obj_mapi.SyncObjects
    For i = 1 To objSyncs.Count
        Set objSync = objSyncs.Item(i)
        objSync.Start
    Next
    Wscript.Sleep 2000
End Sub


Sub fetch_mails
    Dim obj_mail, obj_inbox, subject_parts, subject, timestamp, key
    
    On Error Resume Next
    Set obj_inbox = obj_mapi.GetDefaultFolder(6) ' INBOX
    If Err.Number <> 0 Then
        bail_out("Failed to load inbox (" & Err.Number & "): " & Err.Description)
    End If
    On Error GoTo 0

    update_mailbox
    
    verbose("Number of mails in " & obj_inbox.Name & ": " & obj_inbox.Items.count)
    
    If obj_expected_mails.Count = 0 Then
        Exit Sub ' Not expecting any mail. Don't fetch!
    End If
    
    For Each obj_mail In obj_inbox.Items
        verbose("Processing mail with subject: " & obj_mail.subject)
        subject_parts = Split(obj_mail.subject, " ")
        
        ' at least 3 parts?
        If UBound(subject_parts)+1 >= 3 Then
            subject = subject_parts(UBound(subject_parts)-2)
            timestamp = subject_parts(UBound(subject_parts)-1)
            key = subject_parts(UBound(subject_parts))
            
            If subject = g_subject And IsNumeric(timestamp) And IsNumeric(key) Then
                If Not mail_is_expected(Array(timestamp, key)) Then
                    ' Delete any "Check_MK-Mail-Loop" messages older than 24 hours, even if they are not in our list
                    If g_delete_messages And unix_now() - unix_time(obj_mail.ReceivedTime) > 24 * 3600 Then
                        add_obsolete_mail Array(timestamp, key), obj_mail
                    End If
                Else
                    add_mail Array(timestamp, key), obj_mail
                End If
            End If
        End If
    Next
    
    Set obj_inbox = Nothing
End Sub


Function unix_now()
    unix_now = unix_time(Now())
End Function

Function unix_time(dt)
    unix_time = DateDiff("s", "01/01/1970 00:00:00", dt)
End Function


Function random_key()
    Dim min, max
    min = 1
    max = 1000
    Randomize
    random_key = Int((max-min+1)*Rnd+min)
End Function


Sub send_mail
    Dim obj_mail, key, timestamp
    Set obj_mail = obj_outlook.CreateItem(0) ' Mail
    
    timestamp = unix_now
    key = random_key

    With obj_mail
        .To = g_to
        .Subject = g_subject & " " & timestamp & " " & key
        .Body = ""
        
        verbose("Trying to send mail to " & g_to & " with subject: " & .Subject)
        
        On Error Resume Next
        .Send()
        
        If Err.Number <> 0 Then
            wscript.echo("CRITICAL - Failed to send the mail (" & Err.Number & "): " & Err.Description)
            Err.Clear()
            On Error GoTo 0
            wscript.quit(2)
        End If
        On Error GoTo 0
    End With
    
    add_expected_mail Array(timestamp, key)
    
    Set obj_mail = Nothing
End Sub


Sub check_mails
    Dim expected_mail_id, sent_timestamp, receive_timestamp, key, obj_mail
    Dim num_received, num_pending, num_lost, duration, now
    
    num_received = 0
    num_pending = 0
    num_lost = 0
    duration = -1
    now = unix_now()
    
    ' Loop all expected mails and check whether or not they have been received
    For Each expected_mail_id In obj_expected_mails.Keys
        sent_timestamp = obj_expected_mails(expected_mail_id)(0)
        key = obj_expected_mails(expected_mail_id)(1)
        
        verbose("Expecting mail " & expected_mail_id & ", is in inbox? " & mail_in_inbox(expected_mail_id))
        If mail_in_inbox(expected_mail_id) Then
            Set obj_mail = obj_mails(expected_mail_id)
            receive_timestamp = unix_time(obj_mail.ReceivedTime)

            If duration = -1 Then
                duration = receive_timestamp - sent_timestamp
            Else
                duration = (duration + (receive_timestamp - sent_timestamp)) / 2 ' average
            End If

            If g_critical <> -1 And duration >= g_critical Then
                g_state = 2
                add_output(" (>= " & g_critical & ")")
                
            ElseIf g_warning <> -1 and duration >= g_warning Then
                If g_state <= 1 Then
                    g_state = 1
                End If
                add_output(" (>= " & g_warning & ")")
                
            End If

            obj_expected_mails.Remove(expected_mail_id) ' remove message from expect list
            num_received = num_received + 1
            Set obj_mail = Nothing
        Else
            ' drop expecting messages when older than critical threshold,
            ' but keep waiting for other mails which have not yet reached it
            If now - sent_timestamp >= g_critical Then
                obj_expected_mails.Remove(expected_mail_id) ' remove message from expect list
                num_lost = num_lost + 1
                g_state = 2
            Else
                num_pending = num_pending + 1
            End If
        End If
    Next
    
    If num_received = 1 Then
        add_output_front("Mail received within " & duration & " seconds")
        g_perfdata = "duration=" & duration & ";" & g_warning & ";" & g_critical
    ElseIf num_received > 1 Then
        add_output_front("Received " & num_received & " mails within average of " & duration & " seconds")
        g_perfdata = "duration=" & duration & ";" & g_warning & ";" & g_critical
    Else
        add_output_front("Did not receive any new mail")
    End If

    If num_lost > 0 Then
        add_output(", Lost: " & num_lost & " (Did not arrive within " & g_critical & " seconds) ")
    End If

    If num_pending > 1 Then
        add_output(", Currently waiting for " & num_pending & " mails")
    End If
End Sub


Sub cleanup_mailbox
    Dim mail_id, obj_mail
    ' Do not delete all messages in the inbox. Only the ones which were
    ' processed before! In the meantime there might be occured new ones.
    For Each mail_id In obj_mails.Keys
        obj_mails(mail_id).Delete()
    Next
    
    For Each mail_id In obj_obsolete_mails.Keys
        Set obj_mail = obj_obsolete_mails(mail_id)
        obj_mail.Delete()
    Next
End Sub


' -----------------------------------------------------------------------------
' MAIN
' -----------------------------------------------------------------------------

get_arguments

initialize_outlook

load_expected_mails

fetch_mails
send_mail

check_mails

If g_delete_messages Then
    cleanup_mailbox
End If

save_expected_mails

If g_perfdata <> "" Then
    g_output = g_output & " | " & g_perfdata
End If

wscript.echo(g_output)
wscript.quit(g_state)

'
' CLEANUP
'

obj_outlook.Quit

Set obj_folder = Nothing
Set obj_mapi = Nothing
Set obj_outlook = Nothing
Set obj_mails = Nothing
Set obj_obsolete_mails = Nothing
Set obj_expected_mails = Nothing
Set obj_wsh = Nothing
Set obj_fs = Nothing
