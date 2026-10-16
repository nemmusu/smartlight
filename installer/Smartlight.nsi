; Smartlight per-user installer. Built with NSIS 3.11+ and installer/build.ps1.
Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"

!ifndef DIST_DIR
  !error "Pass /DDIST_DIR=<absolute path to PyInstaller dist>"
!endif
!ifndef PROJECT_DIR
  !error "Pass /DPROJECT_DIR=<absolute path to project>"
!endif
!ifndef VERSION
  !define VERSION "0.4.2"
!endif
!ifndef ICON_PATH
  !define ICON_PATH "${PROJECT_DIR}\ui\smartlight.ico"
!endif

Name "Smartlight"
OutFile "${PROJECT_DIR}\dist\Smartlight-Setup-${VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Smartlight"
InstallDirRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show
BrandingText "$(Branding)"

!define MUI_ICON "${ICON_PATH}"
!define MUI_UNICON "${ICON_PATH}"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${PROJECT_DIR}\installer\welcome.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${PROJECT_DIR}\installer\header.bmp"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "$(WelcomeTitle)"
!define MUI_WELCOMEPAGE_TEXT "$(WelcomeText)"
!define MUI_FINISHPAGE_RUN "$INSTDIR\Smartlight\Smartlight.exe"
!define MUI_FINISHPAGE_RUN_TEXT "$(FinishRun)"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\Smartlight\_internal\ui\help.html"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "$(FinishGuide)"

!insertmacro MUI_PAGE_WELCOME
Page custom CompatibilityPage
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!define MUI_LANGDLL_ALWAYSSHOW
!define MUI_LANGDLL_REGISTRY_ROOT "HKCU"
!define MUI_LANGDLL_REGISTRY_KEY "Software\Smartlight"
!define MUI_LANGDLL_REGISTRY_VALUENAME "InstallerLanguage"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Italian"

LangString Branding ${LANG_ENGLISH} "Smartlight • PC and Tapo lights in one place"
LangString Branding ${LANG_ITALIAN} "Smartlight • luci PC e Tapo in un solo posto"
LangString WelcomeTitle ${LANG_ENGLISH} "Bring your lights together."
LangString WelcomeTitle ${LANG_ITALIAN} "La luce prende forma."
LangString WelcomeText ${LANG_ENGLISH} "Smartlight brings Tapo and PC lighting, scenes and MCP control together. This setup installs the app for the current user and helps prepare the components needed for your hardware."
LangString WelcomeText ${LANG_ITALIAN} "Smartlight riunisce luci Tapo e PC, scene e controllo MCP. Questa procedura installa l’app per l’utente corrente e guida nella preparazione dei componenti necessari al tuo hardware."
LangString FinishRun ${LANG_ENGLISH} "Open Smartlight"
LangString FinishRun ${LANG_ITALIAN} "Apri Smartlight"
LangString FinishGuide ${LANG_ENGLISH} "Open the getting started guide"
LangString FinishGuide ${LANG_ITALIAN} "Apri la guida al primo avvio"
LangString ExistingInstall ${LANG_ENGLISH} "Smartlight is already installed.$\r$\n$\r$\nYes: open the existing app.$\r$\nNo: repair or update the installation.$\r$\nCancel: exit without changes."
LangString ExistingInstall ${LANG_ITALIAN} "Smartlight è già installato.$\r$\n$\r$\nSì: apri il programma esistente.$\r$\nNo: ripara o aggiorna l’installazione.$\r$\nAnnulla: esci senza modifiche."
LangString CompatTitle ${LANG_ENGLISH} "Hardware compatibility"
LangString CompatTitle ${LANG_ITALIAN} "Compatibilità hardware"
LangString CompatSubtitle ${LANG_ENGLISH} "Choose components for your lights; Smartlight detects the available integrations."
LangString CompatSubtitle ${LANG_ITALIAN} "Scegli i componenti per le tue luci: Smartlight rileva le integrazioni disponibili."
LangString CompatTapo ${LANG_ENGLISH} "Tapo lights use your local network and Tapo account. Available controls depend on the model and firmware."
LangString CompatTapo ${LANG_ITALIAN} "Le luci Tapo usano la rete locale e l’account Tapo. I controlli disponibili dipendono dal modello e dal firmware."
LangString CompatPc ${LANG_ENGLISH} "PC RGB uses OpenRGB and, on Windows, Corsair iCUE. Automatic selection can use OpenRGB for Corsair when iCUE finds no devices."
LangString CompatPc ${LANG_ITALIAN} "Gli RGB del PC usano OpenRGB e, su Windows, Corsair iCUE. La selezione automatica può usare OpenRGB per Corsair se iCUE non trova dispositivi."
LangString CompatModes ${LANG_ENGLISH} "Keep Automatic selected, or choose one integration in Settings. An integration is available only after actual controllable lights are detected."
LangString CompatModes ${LANG_ITALIAN} "Lascia Automatico, oppure scegli una singola integrazione nelle impostazioni. Un collegamento è disponibile solo dopo il rilevamento di luci realmente controllabili."
LangString CompatMsi ${LANG_ENGLISH} "MSI Mystic Light is experimental on Windows, with no physical MSI validation yet. Smartlight checks its prerequisites and can obtain the verified official SDK automatically; no DLL selection is needed."
LangString CompatMsi ${LANG_ITALIAN} "MSI Mystic Light è sperimentale su Windows, senza verifica fisica MSI. Smartlight controlla i prerequisiti e può recuperare automaticamente l’SDK ufficiale verificato; non serve scegliere DLL."
LangString CompatCatalog ${LANG_ENGLISH} "Help includes a searchable OpenRGB catalog. Listing a model does not mean it was individually tested with Smartlight. Linux uses OpenRGB only, including Corsair."
LangString CompatCatalog ${LANG_ITALIAN} "L’Aiuto include un catalogo OpenRGB ricercabile. Un modello elencato non equivale a una prova individuale con Smartlight. Linux usa solo OpenRGB, anche per Corsair."
LangString SectionApp ${LANG_ENGLISH} "Smartlight (required)"
LangString SectionApp ${LANG_ITALIAN} "Smartlight (obbligatorio)"
LangString CloseRunning ${LANG_ENGLISH} "Smartlight is running. To update files and open the new version, setup must close Smartlight and any MCP sessions. Running animations will stop. Continue?"
LangString CloseRunning ${LANG_ITALIAN} "Smartlight è in esecuzione. Per aggiornare i file e aprire la nuova versione, il setup deve chiudere Smartlight e le sessioni MCP. Le animazioni si fermeranno. Continuare?"
LangString CloseFailed ${LANG_ENGLISH} "Smartlight did not close. No files were replaced. Close it from the tray and run setup again."
LangString CloseFailed ${LANG_ITALIAN} "Smartlight non si è chiuso. Nessun file è stato sostituito. Chiudilo dall’area di notifica e riesegui il setup."
LangString ProcessCheckFailed ${LANG_ENGLISH} "Smartlight processes could not be checked. No files were replaced. Run setup again."
LangString ProcessCheckFailed ${LANG_ITALIAN} "Non è stato possibile verificare i processi Smartlight. Nessun file è stato sostituito. Riesegui il setup."
LangString ShortcutGuide ${LANG_ENGLISH} "Getting started"
LangString ShortcutGuide ${LANG_ITALIAN} "Guida al primo avvio"
LangString ShortcutCompat ${LANG_ENGLISH} "Hardware compatibility"
LangString ShortcutCompat ${LANG_ITALIAN} "Compatibilità hardware"
LangString SectionWebview ${LANG_ENGLISH} "Microsoft WebView2 (if missing)"
LangString SectionWebview ${LANG_ITALIAN} "Microsoft WebView2 (se assente)"
LangString CheckWebview ${LANG_ENGLISH} "WebView2: checking availability and installing only if needed..."
LangString CheckWebview ${LANG_ITALIAN} "WebView2: controllo presenza e installazione solo se necessaria..."
LangString WebviewUnverified ${LANG_ENGLISH} "WebView2 not verified (result $0)."
LangString WebviewUnverified ${LANG_ITALIAN} "WebView2 non verificato (esito $0)."
LangString WebviewWarning ${LANG_ENGLISH} "WebView2 was not verified. Smartlight may be unable to open its window. Check your connection and run setup again."
LangString WebviewWarning ${LANG_ITALIAN} "WebView2 non è stato verificato. Smartlight potrebbe non aprire la finestra. Controlla la connessione e riesegui il setup."
LangString SectionOpenrgb ${LANG_ENGLISH} "OpenRGB 1.0rc2 (PC lighting connection)"
LangString SectionOpenrgb ${LANG_ITALIAN} "OpenRGB 1.0rc2 (collegamento luci PC)"
LangString CheckOpenrgb ${LANG_ENGLISH} "OpenRGB: checking availability and installing only if needed..."
LangString CheckOpenrgb ${LANG_ITALIAN} "OpenRGB: controllo presenza e installazione solo se necessaria..."
LangString OpenrgbUnverified ${LANG_ENGLISH} "OpenRGB not verified (result $0)."
LangString OpenrgbUnverified ${LANG_ITALIAN} "OpenRGB non verificato (esito $0)."
LangString OpenrgbWarning ${LANG_ENGLISH} "OpenRGB was not verified. If its installation was cancelled, run setup again and select OpenRGB."
LangString OpenrgbWarning ${LANG_ITALIAN} "OpenRGB non è stato verificato. Se la procedura è stata annullata, riesegui il setup e seleziona OpenRGB."
LangString SectionIcue ${LANG_ENGLISH} "iCUE 5 for Corsair lights (official installer)"
LangString SectionIcue ${LANG_ITALIAN} "iCUE 5 per luci Corsair (installer ufficiale)"
LangString CheckIcue ${LANG_ENGLISH} "iCUE 5: checking availability and installing only if needed..."
LangString CheckIcue ${LANG_ITALIAN} "iCUE 5: controllo presenza e installazione solo se necessaria..."
LangString IcueUnverified ${LANG_ENGLISH} "iCUE 5 not verified (result $0)."
LangString IcueUnverified ${LANG_ITALIAN} "iCUE 5 non verificato (esito $0)."
LangString IcueWarning ${LANG_ENGLISH} "iCUE 5 was not verified. If the Corsair installation was cancelled, run setup again and select iCUE."
LangString IcueWarning ${LANG_ITALIAN} "iCUE 5 non è stato verificato. Se la procedura Corsair è stata annullata, riesegui il setup e seleziona iCUE."
LangString DescApp ${LANG_ENGLISH} "Installs the interface, MCP server and included Python runtime."
LangString DescApp ${LANG_ITALIAN} "Installa l’interfaccia, il server MCP e il runtime Python incluso."
LangString DescWebview ${LANG_ENGLISH} "Downloads the signed Microsoft runtime only if missing."
LangString DescWebview ${LANG_ITALIAN} "Scarica il runtime Microsoft firmato solo se manca."
LangString DescOpenrgb ${LANG_ENGLISH} "Installs official OpenRGB 1.0rc2 if missing. Smartlight starts its connection and detects supported devices."
LangString DescOpenrgb ${LANG_ITALIAN} "Installa OpenRGB 1.0rc2 ufficiale se manca. Smartlight avvia il collegamento e rileva i dispositivi compatibili."
LangString DescIcue ${LANG_ENGLISH} "Downloads and opens the Corsair-signed iCUE 5 installer if missing. Complete the steps in the Corsair window."
LangString DescIcue ${LANG_ITALIAN} "Scarica e avvia l’installer iCUE 5 firmato da Corsair se manca. Completa i passaggi nella finestra Corsair."

Function .onInit
  StrCpy $LANGUAGE ${LANG_ENGLISH}
  IfSilent language_ready
  !insertmacro MUI_LANGDLL_DISPLAY
language_ready:
  !ifndef TEST_MODE
  IfFileExists "$INSTDIR\Smartlight\Smartlight.exe" 0 done_existing_check
  ${GetParameters} $R0
  ${GetOptions} $R0 "/REPAIR" $R1
  IfErrors 0 done_existing_check
  MessageBox MB_YESNOCANCEL|MB_ICONQUESTION "$(ExistingInstall)" /SD IDCANCEL IDYES open_existing IDNO done_existing_check
  SetErrorLevel 2
  Abort
open_existing:
  ExecShell "open" "$INSTDIR\Smartlight\Smartlight.exe"
  Abort
done_existing_check:
  !endif
FunctionEnd

Function CompatibilityPage
  !insertmacro MUI_HEADER_TEXT "$(CompatTitle)" "$(CompatSubtitle)"
  nsDialogs::Create 1018
  Pop $0
  ${NSD_CreateLabel} 0 0 100% 26u "$(CompatTapo)"
  Pop $1
  ${NSD_CreateLabel} 0 31u 100% 29u "$(CompatPc)"
  Pop $1
  ${NSD_CreateLabel} 0 65u 100% 29u "$(CompatModes)"
  Pop $1
  ${NSD_CreateLabel} 0 99u 100% 39u "$(CompatMsi)"
  Pop $1
  ${NSD_CreateLabel} 0 143u 100% 40u "$(CompatCatalog)"
  Pop $1
  nsDialogs::Show
FunctionEnd

Section "$(SectionApp)" SEC_APP
  SectionIn RO
  ; A running app or MCP client keeps PyInstaller DLLs open. Ask before
  ; closing only processes loaded from this exact installation directory.
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "${PROJECT_DIR}\installer\prepare-upgrade.ps1"
  ; NSIS is 32-bit. Sysnative forces 64-bit PowerShell so Get-Process.Path
  ; can identify our 64-bit PyInstaller process and its locked DLLs.
  nsExec::ExecToLog '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$PLUGINSDIR\prepare-upgrade.ps1" -InstallDir "$INSTDIR" -SetupDir "$EXEDIR" -Action check'
  Pop $0
  ${If} $0 == "10"
    MessageBox MB_ICONEXCLAMATION|MB_OKCANCEL "$(CloseRunning)" /SD IDCANCEL IDOK close_running IDCANCEL cancel_upgrade
    Goto cancel_upgrade
close_running:
    nsExec::ExecToLog '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$PLUGINSDIR\prepare-upgrade.ps1" -InstallDir "$INSTDIR" -SetupDir "$EXEDIR" -Action stop'
    Pop $0
    ${If} $0 != "0"
      MessageBox MB_ICONSTOP "$(CloseFailed)" /SD IDOK
      SetErrorLevel 3
      Quit
    ${EndIf}
    Goto preflight_done
cancel_upgrade:
    SetErrorLevel 2
    Quit
  ${ElseIf} $0 != "0"
    MessageBox MB_ICONSTOP "$(ProcessCheckFailed)" /SD IDOK
    SetErrorLevel 3
    Quit
  ${EndIf}
preflight_done:
  ; Include only Windows runtime folders. Linux packages and source archives
  ; share dist/, and must never be bundled into the Windows installer.
  SetOutPath "$INSTDIR\Smartlight"
  File /r "${DIST_DIR}\Smartlight\*.*"
  SetOutPath "$INSTDIR\Smartlight-MCP"
  File /r "${DIST_DIR}\Smartlight-MCP\*.*"
  SetOutPath "$INSTDIR"
  File "${PROJECT_DIR}\FIRST_RUN.md"
  File "${PROJECT_DIR}\LINUX.md"
  File "${PROJECT_DIR}\version.txt"
  SetOutPath "$INSTDIR\installer"
  File "${PROJECT_DIR}\installer\bootstrap.ps1"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  !ifndef TEST_MODE
  CreateDirectory "$SMPROGRAMS\Smartlight"
  CreateShortcut "$SMPROGRAMS\Smartlight\Smartlight.lnk" "$INSTDIR\Smartlight\Smartlight.exe"
  CreateShortcut "$SMPROGRAMS\Smartlight\$(ShortcutGuide).lnk" "$INSTDIR\Smartlight\_internal\ui\help.html"
  CreateShortcut "$SMPROGRAMS\Smartlight\$(ShortcutCompat).lnk" "$INSTDIR\Smartlight\_internal\ui\help.html"
  CreateShortcut "$DESKTOP\Smartlight.lnk" "$INSTDIR\Smartlight\Smartlight.exe"

  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "DisplayName" "Smartlight"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "Publisher" "Smartlight"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "DisplayIcon" "$INSTDIR\Smartlight\Smartlight.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight" "NoRepair" 1
  !endif
SectionEnd

Section "$(SectionWebview)" SEC_WEBVIEW
  DetailPrint "$(CheckWebview)"
  nsExec::ExecToLog '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$INSTDIR\installer\bootstrap.ps1" -Language "$LANGUAGE" -InstallWebView2'
  Pop $0
  ${If} $0 != "0"
    DetailPrint "$(WebviewUnverified)"
    MessageBox MB_ICONEXCLAMATION "$(WebviewWarning)" /SD IDOK
  ${EndIf}
SectionEnd

Section "$(SectionOpenrgb)" SEC_OPENRGB
  DetailPrint "$(CheckOpenrgb)"
  nsExec::ExecToLog '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$INSTDIR\installer\bootstrap.ps1" -Language "$LANGUAGE" -InstallOpenRGB'
  Pop $0
  ${If} $0 != "0"
    DetailPrint "$(OpenrgbUnverified)"
    MessageBox MB_ICONEXCLAMATION "$(OpenrgbWarning)" /SD IDOK
  ${EndIf}
SectionEnd

Section "$(SectionIcue)" SEC_ICUE
  DetailPrint "$(CheckIcue)"
  nsExec::ExecToLog '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "$INSTDIR\installer\bootstrap.ps1" -Language "$LANGUAGE" -InstallICUE'
  Pop $0
  ${If} $0 != "0"
    DetailPrint "$(IcueUnverified)"
    MessageBox MB_ICONEXCLAMATION "$(IcueWarning)" /SD IDOK
  ${EndIf}
SectionEnd

Function un.onInit
  StrCpy $LANGUAGE ${LANG_ENGLISH}
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd

Section "Uninstall"
  !ifndef TEST_MODE
  Delete "$DESKTOP\Smartlight.lnk"
  Delete "$SMPROGRAMS\Smartlight\Smartlight.lnk"
  Delete "$SMPROGRAMS\Smartlight\Getting started.lnk"
  Delete "$SMPROGRAMS\Smartlight\Hardware compatibility.lnk"
  Delete "$SMPROGRAMS\Smartlight\Guida al primo avvio.lnk"
  Delete "$SMPROGRAMS\Smartlight\Compatibilita hardware.lnk"
  Delete "$SMPROGRAMS\Smartlight\Compatibilità hardware.lnk"
  DeleteRegValue HKCU "Software\Smartlight" "InstallerLanguage"
  RMDir "$SMPROGRAMS\Smartlight"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Smartlight"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Smartlight"
  !endif
  RMDir /r "$INSTDIR"
  ; Deliberately preserve %APPDATA%\Smartlight, where profiles and backups live.
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_APP} "$(DescApp)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_WEBVIEW} "$(DescWebview)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_OPENRGB} "$(DescOpenrgb)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_ICUE} "$(DescIcue)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END
