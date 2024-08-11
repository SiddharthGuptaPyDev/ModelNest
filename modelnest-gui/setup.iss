[Setup]
AppName=ModelNest-GUI
AppVersion=1.0
DefaultDirName={pf}\ModelNest-GUI
DefaultGroupName=ModelNest-GUI
OutputDir=.
OutputBaseFilename=ModelNest-GUI-Installer
Compression=lzma
SolidCompression=yes
ChangesEnvironment=yes
SetupIconFile=C:\modelnest\modelnest-gui\logo_pack\logo.ico
LicenseFile=LICENSE.txt

[Files]
Source: "dist\modelnest-gui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\modelnest\modelnest-gui\logo_pack\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ModelNest-GUI"; Filename: "{app}\modelnest-gui.exe"; IconFilename: "{app}\logo.ico"
Name: "{commondesktop}\ModelNest-GUI"; Filename: "{app}\modelnest-gui.exe"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Windows\Start Menu\Programs\ModelNest-GUI\ModelNest-GUI"; Filename: "{app}\modelnest-gui.exe"; IconFilename: "{app}\logo.ico"
Name: "{group}\License"; Filename: "{app}\LICENSE.txt"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Code]
var
  LicensePage: TOutputMsgMemoWizardPage;

procedure InitializeWizard;
var
  LicenseFilePath: string;
  LicenseFileContents: AnsiString;
begin
  LicenseFilePath := ExpandConstant('{#SetupSetting("LicenseFile")}');
  if LoadStringFromFile(LicenseFilePath, LicenseFileContents) then
  begin
    LicensePage := CreateOutputMsgMemoPage(wpLicense, 
      'License Agreement', 
      'Please read the following license agreement carefully', 
      'Press Page Down to see the rest of the agreement.',
      LicenseFileContents);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpLicense then
  begin
    Result := MsgBox('Do you accept all the terms of the preceding License Agreement?', 
                     mbConfirmation, MB_YESNO) = IDYES;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  AppPath: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Make the license file unwritable
    Exec('cmd.exe', '/c "attrib +R "' + ExpandConstant('{app}\LICENSE.txt') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // Remove the folder from Quick Access
    AppPath := ExpandConstant('{app}');
    if RegKeyExists(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{679f85cb-0220-4080-b29b-5540cc05aab6}') then
    begin
      RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{679f85cb-0220-4080-b29b-5540cc05aab6}\ShellFolder', 'Folder');
      RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{679f85cb-0220-4080-b29b-5540cc05aab6}\ShellFolder', 'Attributes');
      RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{679f85cb-0220-4080-b29b-5540cc05aab6}\ShellFolder', 'WantsFORPARSING');
    end;
    Exec('cmd.exe', '/c "powershell -Command "Add-Type -TypeDefinition ''public class RemoveFromQuickAccess { public static void RemoveFolder(string path) { [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey(''Software\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace\{679f85cb-0220-4080-b29b-5540cc05aab6}'', true).DeleteValue(''Folder''); } }'' -PassThru | Out-Null; [RemoveFromQuickAccess]::RemoveFolder(''' + AppPath + ''')""', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
