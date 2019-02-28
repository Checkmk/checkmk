set target_dir=%1%
set target_path=%2%
set target_name=%3%
if not "$(VS_DEPLOY)" == "YES" goto DoNotCopy
pause
if not exist "%REMOTE_MACHINE%\providers" mkdir %REMOTE_MACHINE%\providers
pause
copy   "%targetdir%\%target_name%.pdb"   %LOCAL_IMAGES_PDB% 1> nul || exit 1
copy   "%target_path%"     %LOCAL_IMAGES_EXE% 1> nul || exit 2
copy   "%target_path%"    %REMOTE_MACHINE% 1> nul || exit 3
copy   "%target_path%"    %REMOTE_MACHINE%\providers\ 1> nul || exit 4
:DoNotCopy