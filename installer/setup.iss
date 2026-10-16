; Inno Setup 安装脚本（可选方案：纯 Inno Setup 打包，不依赖 Electron）
; 使用方式：安装 Inno Setup 6 后编译本脚本
; 说明：也可使用 electron-builder 的 NSIS 目标（见 electron/package.json）

#define MyAppName "班主任学生管理系统"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "ClassManager"
#define MyAppExeName "backend.exe"

[Setup]
AppId={{8A3D1F5C-2B4E-4A9B-8C7D-5E6F7A8B9C0D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ClassManager
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=ClassManager_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "..\backend\dist\backend\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent
