Assorted Windows Utilities

1. perf_reader.exe
Synopsis: 
    Prevents Handle Leaks on some ( usually old ) Windows OS 
Usage: 
    1. Create in check_mk folder subfolder "utils". For example:
        mkdir "c:\Program Files (x86)\check_mk\utils"
    2. Copy perf_reader.exe to above mentioned folder. For example:
        copy perf_reader.exe "c:\Program Files (x86)\check_mk\utils"
    3. Optionally you may test functionality:
        goto folder "check_mk" and run check_mk_agent perfread
        Note: you may need administrative privileges.

2. openhardwaremonitor-clean.cmd
Synopsis: 
    Solves problems with OpenHardwareMonitor section. 
Usage: 
    Run the script from Windows command line as Administrator

3. uninstall_agent.cmd
Synopsis: 
    Removes New Windows Agent(since 1.6). 
Usage: 
    Run the script from Windows command line as Administrator
    Possible options: 
        yes - to remove silently
        all - to clean all folders and all files
