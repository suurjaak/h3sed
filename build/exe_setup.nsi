; Script for NullSoft Scriptable Install System, producing an executable
; installer for h3sed.
;
; Expected command-line parameters:
; /DPRODUCT_VERSION=<program version>
; /DSUFFIX64=<"_x64" for 64-bit installer>
;
; @created   12.04.2020
; @modified  24.02.2021

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Heroes3 Savegame Editor"
!ifndef PRODUCT_VERSION
  ; PRODUCT_VERSION should come from command-line parameter
  !define PRODUCT_VERSION "0.1"
!endif
!define PRODUCT_PUBLISHER "Erki Suurjaak"
!define PRODUCT_WEB_SITE "https://suurjaak.github.io/h3sed"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\h3sed.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; MUI 1.67 compatible ------
!include "MUI.nsh"
!include x64.nsh

!define MUI_TEXT_WELCOME_INFO_TEXT "This wizard will guide you through the installation of $(^NameDA).$\r$\n$\r$\n$_CLICK"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "h3sed.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\h3sed.exe"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

RequestExecutionLevel admin

InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
OutFile "h3sed_${PRODUCT_VERSION}${SUFFIX64}_setup.exe"
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Function .OnInit
  ${If} SUFFIX64 != ''
    StrCpy $INSTDIR "$PROGRAMFILES64\${PRODUCT_NAME}"
  ${EndIf}
FunctionEnd


Section "MainSection" SEC01
  ; Fixes potential problems with uninstalling shortcuts in Windows 7
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "h3sed.exe"
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\h3sed.exe"
  SetOverwrite off
  File "h3sed.ini"
  SetOverwrite ifnewer
  File /oname=README.txt "README for Windows.txt"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\README.lnk" "$INSTDIR\README.txt"
  File "3rd-party licenses.txt"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall ${PRODUCT_NAME}.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\h3sed.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\h3sed.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to uninstall $(^Name)?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  ; Fixes potential problems with uninstalling shortcuts in Windows 7
  SetShellVarContext all
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\README.txt"
  Delete "$INSTDIR\3rd-party licenses.txt"
  Delete "$INSTDIR\h3sed.ini"
  Delete "$INSTDIR\h3sed.exe"

  Delete "$SMPROGRAMS\h3sed\h3sed.lnk"
  Delete "$SMPROGRAMS\h3sed\README.lnk"
  Delete "$SMPROGRAMS\h3sed\Website.lnk"
  Delete "$SMPROGRAMS\h3sed\Uninstall h3sed.lnk"

  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd
