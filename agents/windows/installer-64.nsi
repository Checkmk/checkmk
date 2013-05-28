; This is the NSIS configuration file for the Check_MK windows agent. This is
; the spec file how to build the installer
;--------------------------------
; Useful sources:
; http://nsis.sourceforge.net/Reusable_installer_script

!define CHECK_MK_VERSION "1.2.3i1"
!define NAME "Check_MK Agent ${CHECK_MK_VERSION}"

XPStyle on
Icon "installer.ico"

; The name of the installer
Name "${NAME}"

; The file to write
OutFile "install_agent-64.exe"

SetDateSave on
SetDatablockOptimize on
CRCCheck on
SilentInstall normal

; The default installation directory
InstallDir "$PROGRAMFILES\check_mk"

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\check_mk_agent" "Install_Dir"

; Request application privileges for Windows >Vista
RequestExecutionLevel admin

ShowInstDetails show

;--------------------------------
; Pages

Page directory
Page components
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------

Section "Check_MK_Agent"
    ; Can not be disabled
    SectionIn RO

    !include LogicLib.nsh
    ExpandEnvStrings $0 "%comspec%"
    nsExec::ExecToStack '"$0" /k "net start | FIND /C /I "check_mk_agent""'
    Pop $0
    Pop $1
    StrCpy $1 $1 1
    Var /GLOBAL stopped
    ${If} "$0$1" == "01"
        DetailPrint "Stop running check_mk_agent..."
        StrCpy $stopped "1"
        nsExec::Exec 'cmd /C "net stop check_mk_agent"'
    ${Else}
        StrCpy $stopped "0"
    ${EndIf}

    SetOutPath "$INSTDIR"
    File /oname=check_mk_agent.exe check_mk_agent-64.exe
    File check_mk.example.ini
    CreateDirectory "$INSTDIR\local"
    CreateDirectory "$INSTDIR\plugins"
  
    ; Write the installation path into the registry
    WriteRegStr HKLM SOFTWARE\check_mk_agent "Install_Dir" "$INSTDIR"
  
    ; Write the uninstall keys for Windows
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent" "DisplayName" "${NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent" "NoRepair" 1
    WriteUninstaller "uninstall.exe"
SectionEnd

Section "Install & start service"
    DetailPrint "Installing and starting the check_mk_agent service..."
    nsExec::Exec 'cmd /C "$INSTDIR\check_mk_agent.exe" install'
    nsExec::Exec 'cmd /C "net start check_mk_agent"'
SectionEnd

Section "Uninstall"
    ; Remove the service
    DetailPrint "Stopping service..."
    nsExec::Exec 'cmd /C "net stop check_mk_agent"'
    DetailPrint "Removing service..."
    nsExec::Exec 'cmd /C "$INSTDIR\check_mk_agent.exe" remove'
  
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent"
    DeleteRegKey HKLM SOFTWARE\check_mk_agent
  
    ; Remove files and uninstaller
    Delete "$INSTDIR\check_mk_agent.exe"
    Delete "$INSTDIR\check_mk.example.ini"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR\local"
    RMDir "$INSTDIR\plugins"
  
    ; Remove directories used
    RMDir "$INSTDIR"
SectionEnd
