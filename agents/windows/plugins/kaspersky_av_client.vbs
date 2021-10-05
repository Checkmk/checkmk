' -----------------------------------------------------------------------------
' Check_MK windows agent plugin to gather information abount fullscan age and
' signature date and connection date to Kaspersky Management Server of
' Kaspersky Anti-Virus Client.
' All Keys in format dd-MM-yyyy HH-mm-ss
'
' To be able to use CDate functions, we have to convert the Kaspersky input
' to a datetime format recognized by the local system, which can vary in
' separators, order, leading zeros, and 12/24hrs. Once we have a CDate
' compatible datetime string we can do date/time calculations. Afterwards,
' we have to convert the output one more time, to the format expected by
' checkmk (server-side): dd.MM.yyyy HH:mm:ss
' -----------------------------------------------------------------------------

Option Explicit
Const CMK_VERSION = "2.1.0i1"
Dim strStatisticsLoc, strProtection_BasesDate, strProtection_LastFscan, strProtection_LastConnected
Dim strBIASLoc, strBIAS
Dim strInternationalLoc, strDateSeparator, strTimeSeparator, strDateFormat, strTimeFormat, blnAmPm
Dim arrDateFormat, arrTimeFormat
Dim objShell
Dim strSignaturesDate, strLastFullScanDate

Set objShell = CreateObject("WScript.Shell")

Function UTC2Local(TimeStamp)
   UTC2Local = DateAdd("n", strBIAS, CDate(TimeStamp))
End Function

' VBS lacks the abilty to easy extend an array. The
' workaround is this `ReDim Preserve` based function.
Function AddItemToArray(arr, val)
    ReDim Preserve arr(UBound(arr) + 1)
    arr(UBound(arr)) = val
    AddItemToArray = arr
End Function

'VBS lacks a 'like' kinda function to compare strings.
' The workaround is this little regex function.
Dim objregExp, objMatches, objMatch
Function regExpTest(TestString, TestPattern)
  Set objRegExp = CreateObject("VBScript.RegExp")
  With objRegExp
    .IgnoreCase = False
    .Pattern = TestPattern
  End With

  Set objMatches = objRegExp.execute(TestString)
  For Each objMatch In objMatches
    regExpTest = True
	Exit Function
  Next
  regExpTest = False
  Exit Function
End Function

Dim arrDateTimeStamp, arrDateStamp, arrTimeStamp
Dim arrDateRepl, arrTimeRepl, DatePart, TimePart, strValue, strAmPm
Dim strCDateCompDateTime, i
Function Kasp2Win(DateTimeStamp)
  ' Split the Kaspersky string (dd-MM-yyyy HH-mm-ss) in a date
  ' and a time part, and split the date and time parts into
  ' separate elements.
  arrDateTimeStamp = Split(DateTimeStamp, " ")
  arrDateStamp = Split(arrDateTimeStamp(0), "-")
  arrTimeStamp = Split(arrDateTimeStamp(1), "-")
  ' The order in the array with dateSTAMP elements is known:
  ' (0) is days, (1) is month, and (2) is the year. By looping
  ' through the array with the date FORMAT elements (from the
  ' registry), the matching stamps can be stored in a new array
  ' in the same order as the date format.
  ' A single character format (e.g. d instead of dd for days)
  ' requires no leading 0 for values < 10. These have to be removed
  ' from the Kaspersky input.
  arrDateRepl = Array()
  For Each DatePart In arrDateFormat
    If regExpTest(DatePart, "d|dd") Then
	  strValue = arrDateStamp(0)
	  If (Len(DatePart) = 1) And (Left(arrDateStamp(0), 1) = "0") Then
	    strValue = Right(strValue, Len(strValue - 1))
	  End If
      arrDateRepl = AddItemToArray(arrDateRepl, strValue)
    ElseIf regExpTest(DatePart, "M|MM") Then
	  strValue = arrDateStamp(1)
	  If (Len(DatePart) = 1) And (Left(arrDateStamp(1), 1) = "0") Then
	    strValue = Right(strValue, Len(strValue - 1))
	  End If
      arrDateRepl = AddItemToArray(arrDateRepl, strValue)
    ElseIf regExpTest(DatePart, "yy|yyyy") Then
	  strValue = arrDateStamp(2)
	  If (Len(DatePart) = 2) Then
	    strValue = Right(strValue, 2)
	  End If
      arrDateRepl = AddItemToArray(arrDateRepl, strValue)
    End If
  Next
  
  ' Repeat the same logic for time.
  arrTimeRepl = Array()
  For Each TimePart In arrTimeFormat
    If regExpTest(TimePart, "h|hh|H|HH") Then
	  strValue = arrTimeStamp(0)
	  ' Store the correct AM/PM value, in case the time format
	  ' contains tt.
      If CInt(strValue) < 12 Then
	    strAmPm = "AM"
	  Else
	    strAmPm = "PM"
      End If
	  ' An uppercase H(H) means 24h format, lowercase h(h) 12h format.
	  ' Covert 24h to 12h if necessary.
	  If (Left(TimePart, 1) = "h") And (CInt(strValue) > 12) Then
	    strValue = Cstr(CInt(strValue) - 12)
	  ElseIf (Len(TimePart) = 1) And (Left(arrTimeStamp(0), 1) = "0") Then
	    strValue = Right(strValue, Len(strValue - 1))
	  End If
      arrTimeRepl = AddItemToArray(arrTimeRepl, strValue)
    ElseIf regExpTest(TimePart, "m|mm") Then
	  strValue = arrTimeStamp(1)
	  If (Len(TimePart) = 1) And (Left(arrTimeStamp(1), 1) = "0") Then
	    strValue = Right(strValue, Len(strValue - 1))
	  End If
      arrTimeRepl = AddItemToArray(arrTimeRepl, strValue)
    ElseIf regExpTest(TimePart, "s|ss") Then
	  strValue = arrTimeStamp(2)
	  If (Len(TimePart) = 1) And (Left(arrTimeStamp(2), 1) = "0") Then
	    strValue = Right(strValue, Len(strValue - 1))
	  End If
      arrTimeRepl = AddItemToArray(arrTimeRepl, strValue)	
    End If
  Next

  ' Construct a CDate compatible datetime string by combining the
  ' already ordered date and time elements, separated with the
  ' correct separators read from the registry.
  strCDateCompDateTime = ""
  For i=0 To UBound(arrDateRepl)
    strCDateCompDateTime = strCDateCompDateTime & arrDateRepl(i)
    If i < UBound(arrDateRepl) Then
      strCDateCompDateTime = strCDateCompDateTime & strDateSeparator
    Else
      strCDateCompDateTime = strCDateCompDateTime & " "
    End If
  Next
 
  For i=0 To UBound(arrTimeRepl)
    strCDateCompDateTime = strCDateCompDateTime & arrTimeRepl(i)
    If i < UBound(arrTimeRepl) Then
      strCDateCompDateTime = strCDateCompDateTime & strTimeSeparator
    ElseIf blnAmPm Then
      strCDateCompDateTime = strCDateCompDateTime & " " & strAmPm
    End If
  Next
 
  Kasp2Win = strCDateCompDateTime

End Function

Dim strDatePart
Function AddPrefixZero(strDatePart)
  If (Len(strDatePart) = 1) Then
    AddPrefixZero = "0" & strDatePart
  Else
    AddPrefixZero = strDatePart
  End if
End Function

' Construct a checkmk compatible datetime string: 
' dd.MM.yyyy HH:mm:ss
Dim strYear, strMonth, strDay, strHour, strMinute, strSecond
Function CDate2checkmk(strCDateCompDateTime)
  strYear = Year(strCDateCompDateTime)
  strMonth = AddPrefixZero(Month(strCDateCompDateTime))
  strDay = AddPrefixZero(Day(strCDateCompDateTime))
  ' Add 12 hours after midday (post merīdiem / PM), if a 12hrs notation is used.
  If (CInt(Hour(strCDateCompDateTime)) < 12) And (Right(strCDateCompDateTime,2) = UCase("PM")) Then
    strHour = Cstr(CInt(Hour(strCDateCompDateTime)) + 12)
  Else
    strHour = AddPrefixZero(Hour(strCDateCompDateTime))
  End If
  strMinute = AddPrefixZero(Minute(strCDateCompDateTime))
  strSecond = AddPrefixZero(Second(strCDateCompDateTime))

  CDate2checkmk = strDay & "." & strMonth & "." & strYear & " " & strHour & ":" & strMinute & ":" & strSecond
End Function

' The ActiveTimeBias determines the offset of local time
' from UTC and is a dynamic value.
strBIASLoc = "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\TimeZoneInformation\ActiveTimeBias"
strBIAS = -objShell.RegRead(strBIASLoc)
strStatisticsLoc = "HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\KasperskyLab\Components\34\1103\1.0.0.0\Statistics\AVState\"
strInternationalLoc = "HKEY_CURRENT_USER\Control Panel\International\"

strDateSeparator = objShell.RegRead(strInternationalLoc & "sDate")
strTimeSeparator = objShell.RegRead(strInternationalLoc & "sTime")
strDateFormat = objShell.RegRead(strInternationalLoc & "sShortDate")
strTimeFormat = objShell.RegRead(strInternationalLoc & "sTimeFormat")
' If the system uses a 12hrs time notation with am/pm suffix (a "tt" in the registry),
' then we strip this part from the time string.
If Right(strTimeFormat, 2) = "tt" Then
  blnAmPm = True
  strTimeFormat = Trim(Left(strTimeFormat, Len(strTimeFormat)-2))
Else
  blnAmPm = False
End If
' Create arrays with the date and time format. The elements of the array are
' ordened according to a CDate compatible format. We use these arrays to 
' compare the order with the Kasparsky date/time formats (see Kasp2Win function).
arrDateFormat = Split(strDateFormat, strDateSeparator)
arrTimeFormat = Split(strTimeFormat, strTimeSeparator)

'Protection_LastConnected key set with date of last connection to management server
strProtection_LastConnected = strStatisticsLoc & "Protection_LastConnected"
On Error Resume Next
strProtection_LastConnected = objShell.RegRead(strProtection_LastConnected)

'If the strProtection_LastConnected key can be read Kaspersky AV is assumed to be installed
If err.number = 0 Then
	WScript.Echo("<<<kaspersky_av_client>>>")

	'Protection_BasesDate key is set with old signatures from installer
	strProtection_BasesDate = strStatisticsLoc & "Protection_BasesDate"
	strProtection_BasesDate = objShell.RegRead(strProtection_BasesDate)
	If strProtection_BasesDate = "" Then
		WScript.Echo("Signatures Missing")
	Else
	    strSignaturesDate = UTC2Local(Kasp2Win(strProtection_BasesDate))
		WScript.Echo("Signatures " & CDate2checkmk(strSignaturesDate))
	End if

	'Protection_LastFscan key deployed empty on installation
	strProtection_LastFscan = strStatisticsLoc & "Protection_LastFscan"
	strProtection_LastFscan = objShell.RegRead(strProtection_LastFscan)
	If strProtection_LastFscan = "" Or err.number <> 0 Then
		WScript.Echo("Fullscan Missing")
	Else
	    strLastFullScanDate = UTC2Local(Kasp2Win(strProtection_LastFscan))
		WScript.Echo("Fullscan " & CDate2checkmk(strLastFullScanDate))
	End If

'Else
    'WScript.Echo("<<<kaspersky_av_client>>>")
	'WScript.Echo("Signatures Missing")
	'WScript.Echo("Fullscan Missing")
	'WScript.Echo("Missing Kaspersky Client")

End If
