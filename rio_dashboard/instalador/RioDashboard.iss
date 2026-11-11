; Instalador do Rio Dashboard (Inno Setup 6). Instala só para o usuário atual: não pede senha de administrador.
#define AppNome "Rio Dashboard"
#define AppVersao GetEnv("RIO_VERSAO")
#if AppVersao == ""
  #define AppVersao "1.0.0"
#endif

[Setup]
AppId={{6F1D3C5A-2B7E-4C1A-9D0B-5E3A7C2F8B14}
AppName={#AppNome}
AppVersion={#AppVersao}
AppPublisher=Observatório do Trabalho Carioca
DefaultDirName={autopf}\{#AppNome}
DefaultGroupName={#AppNome}
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=Rio-Dashboard-Instalador
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\RioDashboard.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um ícone na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\RioDashboard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppNome}"; Filename: "{app}\RioDashboard.exe"; IconFilename: "{app}\RioDashboard.exe"
Name: "{autodesktop}\{#AppNome}"; Filename: "{app}\RioDashboard.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RioDashboard.exe"; Description: "Abrir o Rio Dashboard agora"; Flags: nowait postinstall skipifsilent
