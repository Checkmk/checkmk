; This is the NSIS configuration file for the Check_MK windows agent. This is
; the spec file how to build the installer
;--------------------------------
; Useful sources:
; http://nsis.sourceforge.net/Reusable_installer_script

!define VERSION "1.1.13i3"
!define NAME "Check_MK Agent ${VERSION}"

XPStyle on
Icon "installer.ico"

; The name of the installer
Name "${NAME}"

; The file to write
OutFile "check_mk_agent_install-${VERSION}.exe"

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

  SetOutPath "$INSTDIR"
  File check_mk_agent.exe
  File check_mk.ini
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
  ExecWait '"$INSTDIR\check_mk_agent.exe" install'
  ExecWait 'net start check_mk_agent'
SectionEnd

Section "Uninstall"
  ; Remove the service
  ExecWait 'net stop check_mk_agent'
  ExecWait '"$INSTDIR\check_mk_agent.exe" remove'

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\check_mk_agent"
  DeleteRegKey HKLM SOFTWARE\check_mk_agent

  ; Remove files and uninstaller
  Delete "$INSTDIR\check_mk_agent.exe"
  Delete "$INSTDIR\check_mk.ini"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR\local"
  RMDir "$INSTDIR\plugins"

  ; Remove directories used
  RMDir "$INSTDIR"
SectionEnd
