; Inno Setup script for the doc4ai desktop installer.
; Build (after PyInstaller has produced desktop/dist/doc4ai/):
;   ISCC desktop\installer.iss
; Output: desktop/dist/doc4ai-setup.exe
;
; Installs per-user under %LOCALAPPDATA%\Programs\doc4ai — no admin rights,
; no UAC prompt, the same model VS Code / Discord use. A regular installed
; app (onedir, loaded in place) is far less likely to trip antivirus
; heuristics than a onefile exe that unpacks itself into %TEMP% each run.

#define AppName "doc4ai"
#define AppExe "doc4ai.exe"
#define AppVersion Trim(FileRead(FileOpen(AddBackslash(SourcePath) + "VERSION")))

[Setup]
; Fixed AppId so upgrades replace the previous install instead of adding a
; second copy. Never change it.
AppId={{6B0E2C0D-5A7E-4F52-9C4B-D0C4A1D0C4A1}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Claudio Ulisse
AppPublisherURL=https://github.com/claulis/doc4ai
AppSupportURL=https://github.com/claulis/doc4ai/issues
AppUpdatesURL=https://github.com/claulis/doc4ai/releases
AppCopyright=Copyright (c) 2026 Claudio Ulisse
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=dist
OutputBaseFilename=doc4ai-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\doc4ai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Drop files left over from an older build's _internal folder on upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Temp uploads live in the user's data folder (see MEDIA_ROOT in settings.py).
Type: filesandordirs; Name: "{localappdata}\{#AppName}"
