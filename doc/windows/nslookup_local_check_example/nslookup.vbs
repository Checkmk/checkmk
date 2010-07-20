'------------------------------------------------------------------------------
'
' This script can be used as local check for the Check_MK windows agent.
' The script takes several arguments:
' 1. The name of the service
' 1. The name/address of the DNS host
' 2. The address to lookup
' 3. The direction to resolve (forward or reverse)
' *. The expected answers
'
' The script executes nslookup, parses the output and returns status output
' and state information depending on the given parameters.
'
' Example:
'
' Place a small batch script e.g. nslookup_domain.de in the local/ subdirectory
' of the check_mk_agent. and add the following line:
'
'  cscript //NoLogo lib/nslookup_domain.vbs nslookup_domain.de domain.de 192.168.123.1
'
' The script checks for the domain "domain.de" and expects the answer "192.168.123.1".
' Another answer or more resolved addresses will result in a CRITICAL state.
'
'
' Author: Lars Michelsen <lm@mathias-kettner.de>, 2010-07-20
'------------------------------------------------------------------------------

Option Explicit

Dim strName, strHost, checkName, status, output, i
Dim objShell, objExec, strOutput, arrLines, strLine
Dim addresses, address, expected, direction, label
Dim aExpected()

status = 0
output = ""

If Wscript.Arguments.Count < 3 Then
    wscript.echo "Wrong launch options."
    wscript.quit 2
End If

checkName = Wscript.Arguments(0)
strHost = Wscript.Arguments(1)
strName = Wscript.Arguments(2)
direction = Wscript.Arguments(3)

For i = 4 to Wscript.Arguments.Count - 1
    Redim Preserve aExpected(i)
    aExpected(i) = Wscript.Arguments(i)
Next

label = "address"
If direction = "reverse" Then
    label = "name"
End If

Set objShell = CreateObject("WScript.Shell")
Set objExec = objShell.Exec("cmd /c nslookup " & strName & " " & strHost)
While objExec.Status
    WScript.Sleep 100
Wend

strOutput = objExec.StdOut.ReadAll
arrLines = Split(strOutput, VbCrLf)

addresses = Array()
For Each strLine In arrLines
    If direction = "forward" AND Left(strLine, 10) = "Addresses:" Then
        addresses = Split(Trim(Mid(strLine, 11)), ", ")
    ElseIf direction = "reverse" AND Left(strLine, 5) = "Name:" Then
        addresses = Split(Trim(Mid(strLine, 6)), ", ")
    End If
Next

' Are all found addresses expected?
If UBound(addresses) > -1 Then
    For Each address in addresses
        If InStr(1, vbNullChar & Join(aExpected, vbNullChar) , vbNullChar & address) = 0 Then
            status = 2
            output = output & label & " is NOT expected """ & address & """, "
        End If
    Next
End If

' Are all expected addresses found?
For Each expected in aExpected
    If InStr(1, vbNullChar & Join(addresses, vbNullChar) , vbNullChar & expected) = 0 Then
        status = 2
        output = output & "Expected " & label & " NOT found """ & expected & """, "
    End If
Next

If output = "" Then
    If direction = "forward" Then
        output = "OK - All expected addresses were found in ""nslookup " & strName & """"
    Else
        output = "OK - All expected names were found in ""nslookup " & strName & """"
    End If
Else
    output = Mid(output, 1, Len(output)-2)
End If

wscript.echo status & " " & checkName & " - " & output
wscript.quit status
