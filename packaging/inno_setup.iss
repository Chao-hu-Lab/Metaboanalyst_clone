; Inno Setup 腳本 — Windows 安裝程式
; 使用方式:
;   1. 先執行 pyinstaller packaging/pymetabo.spec --noconfirm --clean
;   2. 用 Inno Setup Compiler 開啟此 .iss 編譯

[Setup]
AppName=PyMetaboAnalyst
AppVersion=1.0.0
AppPublisher=PyMetaboAnalyst
DefaultDirName={autopf}\PyMetaboAnalyst
DefaultGroupName=PyMetaboAnalyst
OutputBaseFilename=PyMetaboAnalyst_Setup_v1.0.0
SetupIconFile=..\resources\icons\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\PyMetaboAnalyst\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
Name: "{autodesktop}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\PyMetaboAnalyst.exe"; Description: "Launch PyMetaboAnalyst"; Flags: nowait postinstall skipifsilent
