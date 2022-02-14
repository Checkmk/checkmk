'----------------------------------------------------------------------------
' Script to generate TS Per-Device license usage report.
' Requires Administrator privilege on the license server.
' Works only with WS08 TS License Server, as there is no WMI
' interface for TS Licensing on earlier versions.
'----------------------------------------------------------------------------

' The entire argument block is currently not configurable via WATO
Const CMK_VERSION = "2.0.0p21"
SET Args = WScript.Arguments
NameSpace = "root\cimv2"
ClassName = "Win32_TSIssuedLicense"
IF Args.Length > 2 THEN
    Help
    WSCRIPT.QUIT(1)
END IF

IF Args.Length = 1 THEN
    Help
    WSCRIPT.QUIT(1)
END IF

IF Args.Length = 2 THEN
    ' Checking if Server Name has been provided
    CompResult = strComp(Args(0), "-server",1)
    IF CompResult = 0 THEN
        ServerName = Args(1)
    ELSE
        Help
        WSCRIPT.QUIT(1)
    END IF
ELSE
    ' if argc.length = 0, no arg supplied
    ServerName = "."
END IF

GeneratePerDeviceReport
WSCRIPT.QUIT

'----------------------------------------------------------------------------
' FUNCTIONS
'----------------------------------------------------------------------------
SUB Help()
    WSCRIPT.StdErr.Write("Usage: GeneratePerDeviceReport.vbs [-Server ServerName]\n")
    WSCRIPT.StdErr.Write(" If no ServerName is provided, then report generation\n")
    WSCRIPT.StdErr.Write(" is attempted at host machine\n")
END SUB

SUB GeneratePerDeviceReport()
    Err.Clear
    Set ObjWMIService = GetObject("winmgmts:\\" & ServerName & "\" & NameSpace )
    IF ERR.NUMBER <> 0 THEN
        WSCRIPT.StdErr.Write("Unable to connect to the Namespace")
        WSCRIPT.QUIT(2)
    END IF
    Set ObjectSet = ObjWMIService.ExecQuery ("Select * from Win32_TSLicenseKeyPack")
    ReportCountBefore = ObjectSet.Count
    ' No Reports are present
    IF ObjectSet.Count = 0 THEN
        WSCRIPT.StdErr.Write("No license key packs found")
        WScript.Quit(5)
    END IF
    WSCRIPT.ECHO "<<<rds_licenses:sep(44)>>>"
    WSCRIPT.ECHO "KeyPackId,Description,KeyPackType,ProductType,ProductVersion,ProductVersionID,TotalLicenses,IssuedLicenses,AvailableLicenses,ExpirationDate,TypeAndModel"
    FOR EACH ObjectClass IN ObjectSet
        WSCRIPT.ECHO ObjectClass.KeyPackId & "," & ObjectClass.Description & "," & ObjectClass.KeyPackType & "," & ObjectClass.ProductType & "," & ObjectClass.ProductVersion & "," & ObjectClass.ProductVersionID & "," & ObjectClass.TotalLicenses & "," & ObjectClass.IssuedLicenses & "," & ObjectClass.AvailableLicenses & "," & ObjectClass.ExpirationDate
        NEXT
END SUB



