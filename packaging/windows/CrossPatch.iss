; Windows installer for CrossPatch (Inno Setup 6).
;
; Packs the PyInstaller output staged by packaging\windows\build.ps1, which calls:
;
;   ISCC.exe /DAppVersion=1.4.0 /DSourceDir=<staged CrossPatch folder> /DOutputDir=<folder> CrossPatch.iss
;
; Installs for the current user by default (%LOCALAPPDATA%\Programs\CrossPatch, no
; admin prompt); the first page lets the user install for everyone instead.
;
; The app updates itself by running the next installer with /SILENT /UPDATE=1:
; setup waits for the CrossPatch.Running mutex to go away, installs over the
; current copy and starts CrossPatch again (see Updater.py).

#ifndef AppVersion
  #error Pass the version: /DAppVersion=x.y.z
#endif
#ifndef SourceDir
  #error Pass the staged folder: /DSourceDir=...
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define AppName "CrossPatch"
#define AppExe "CrossPatch.exe"
#define AppPublisher "Robocnop"
#define AppUrl "https://github.com/Robocnop/CrossPatch"

[Setup]
; Never change AppId: it is how Windows recognises upgrades and the uninstaller.
AppId={{D30E61D8-DEBA-4415-8B88-985983C89EAA}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; The app holds the CrossPatch.Running mutex while it runs, see EnsureAppClosed
; below. AppMutex is not used because it would abort a silent update started a
; moment before the app finishes closing.
CloseApplications=yes
RestartApplications=no
SetupIconFile=..\..\assets\CrossP.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=..\..\LICENSE
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
OutputDir={#OutputDir}
OutputBaseFilename=CrossPatch-{#AppVersion}-win-x64-setup
ShowLanguageDialog=auto

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[CustomMessages]
en.RemoveUserData=Also delete CrossPatch's settings, profiles and backups?%n%nThis includes the default mods folder (%APPDATA%\CrossPatch\mods) and every mod stored in it. A mods folder you picked elsewhere is not touched.%n%nMods already copied into the game stay there: use "Launch without mods" before uninstalling if you want the game back to vanilla.
fr.RemoveUserData=Supprimer aussi les paramètres, profils et sauvegardes de CrossPatch ?%n%nCela inclut le dossier de mods par défaut (%APPDATA%\CrossPatch\mods) et tous les mods qu'il contient. Un dossier de mods choisi ailleurs n'est pas touché.%n%nLes mods déjà copiés dans le jeu y restent : utilisez « Lancer sans mods » avant de désinstaller pour remettre le jeu d'origine.
en.LaunchApp=Launch {#AppName}
fr.LaunchApp=Lancer {#AppName}
en.AppRunning={#AppName} is running. Close it, then click Retry.
fr.AppRunning={#AppName} est ouvert. Fermez-le, puis cliquez sur Réessayer.
en.OneClick=Open GameBanana 1-Click Install links with CrossPatch
fr.OneClick=Ouvrir les liens 1-Click Install de GameBanana avec CrossPatch

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "oneclick"; Description: "{cm:OneClick}"

[InstallDelete]
; Upgrades: PyInstaller's runtime folder is replaced as a whole, so a library
; dropped by the new version cannot linger and shadow the new ones.
Type: filesandordirs; Name: "{app}\_internal"
; Leftover of the zip based updater used by portable copies.
Type: filesandordirs; Name: "{app}\update_temp"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; CrossPatch also registers this itself at startup; doing it here as well means
; 1-Click links work before the first launch and are cleaned up on uninstall.
Root: HKA; Subkey: "Software\Classes\crosspatch"; ValueType: string; ValueName: ""; ValueData: "URL:CrossPatch Protocol"; Flags: uninsdeletekey; Tasks: oneclick
Root: HKA; Subkey: "Software\Classes\crosspatch"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Tasks: oneclick
Root: HKA; Subkey: "Software\Classes\crosspatch\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: oneclick

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
; Update started from the app: restart it once installed (as the user, even if setup was elevated).
Filename: "{app}\{#AppExe}"; Flags: nowait runasoriginaluser; Check: IsUpdateMode

[UninstallDelete]
Type: filesandordirs; Name: "{app}\update_temp"

[Code]
const
  RunningMutex = 'CrossPatch.Running';

function IsUpdateMode: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;

// Waits up to Seconds for the app to exit; True once it is closed.
function WaitForAppToClose(Seconds: Integer): Boolean;
var
  Attempts: Integer;
begin
  Attempts := 0;
  while CheckForMutexes(RunningMutex) and (Attempts < Seconds * 4) do
  begin
    Sleep(250);
    Attempts := Attempts + 1;
  end;
  Result := not CheckForMutexes(RunningMutex);
end;

// Files cannot be replaced while the app runs: wait for it (silent/update) or ask the user to close it.
function EnsureAppClosed(Silent: Boolean): Boolean;
begin
  if Silent or IsUpdateMode then
  begin
    Result := WaitForAppToClose(30);
    exit;
  end;

  Result := True;
  while CheckForMutexes(RunningMutex) do
  begin
    if MsgBox(CustomMessage('AppRunning'), mbError, MB_RETRYCANCEL) = IDCANCEL then
    begin
      Result := False;
      exit;
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := EnsureAppClosed(WizardSilent);
end;

function InitializeUninstall(): Boolean;
begin
  Result := EnsureAppClosed(UninstallSilent);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Settings, profiles and the default mods folder live in the user profile
  // (Config.py); they are only removed when the user asks for it.
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
  begin
    if MsgBox(CustomMessage('RemoveUserData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\CrossPatch'), True, True, True);
  end;
end;
