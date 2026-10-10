#ifndef AppVersion
  #define AppVersion "0.6.4"
#endif
#ifndef BuildDirectory
  #define BuildDirectory "..\Latest build\Devices"
#endif

[Setup]
AppId={{C8564F88-8639-44D5-A6C9-4F514386679F}
AppName=Devices
AppVersion={#AppVersion}
AppPublisher=Devices
DefaultDirName={localappdata}\Programs\Devices
DefaultGroupName=Devices
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\Latest build
OutputBaseFilename=Devices-{#AppVersion}-Setup
SetupIconFile=..\assets\devices.ico
UninstallDisplayIcon={app}\Devices.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
UsePreviousTasks=yes

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
Name: startup; Description: "Start Devices when I sign in"; Flags: unchecked

[Files]
Source: "{#BuildDirectory}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PROTOCOL_NOTES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\RELEASE_STATUS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Devices"; Filename: "{app}\Devices.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Devices"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Devices"; Filename: "{app}\Devices.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Devices"; ValueData: """{app}\Devices.exe"" --tray"; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Devices.exe"; Description: "Open Devices"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\Devices.exe"; Parameters: "--quit"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "QuitDevices"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  StartupCommand: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    { Also remove startup enabled later through the app's tray menu. }
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Devices', StartupCommand) then
      if CompareText(StartupCommand, ExpandConstant('"{app}\Devices.exe" --tray')) = 0 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Devices');
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  if FileExists(ExpandConstant('{app}\Devices.exe')) then
  begin
    Exec(ExpandConstant('{app}\Devices.exe'), '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(500);
  end;
end;
