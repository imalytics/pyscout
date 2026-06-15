#define MyAppName      "PyScout"
#define MyAppVersion   "1.0.4"
#define MyAppPublisher "PyScout"
#define MyAppExeName   "main.exe"
#define MyAppURL       "https://polar.sh/checkout/polar_c_jFRXBrcZ7BX5NqIDRk1pItlSgOZFGP1pjf4iP0f5QWT"
#define SourceDir      "build\main.dist"

[Setup]
AppId={{7A3F2B1C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
CloseApplications=yes
RestartApplications=yes
OutputDir=dist
OutputBaseFilename=PyScout-Setup
SetupIconFile=ico.ico
WizardImageFile=lateral.png
WizardSmallImageFile=chica.png
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageStretch=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ico.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\ico.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent unchecked

[Registry]
; Escribe el idioma elegido durante la instalación en QSettings
Root: HKCU; Subkey: "Software\ScoutApp\prefs"; ValueType: string; ValueName: "language"; ValueData: "{code:GetAppLang}"; Flags: uninsdeletevalue

[Code]
function GetAppLang(Param: String): String;
begin
  if ActiveLanguage = 'english' then
    Result := 'en'
  else
    Result := 'es';
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
