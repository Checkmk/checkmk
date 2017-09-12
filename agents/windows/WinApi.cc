#include "WinApi.h"

// WINADVAPI:
WINBOOL WinApi::CloseEventLog(HANDLE hEventLog) const {
    return ::CloseEventLog(hEventLog);
}

WINBOOL WinApi::CloseServiceHandle(SC_HANDLE hSCObject) const {
    return ::CloseServiceHandle(hSCObject);
}

WINBOOL WinApi::ControlService(SC_HANDLE hService, DWORD dwControl,
                               LPSERVICE_STATUS lpServiceStatus) const {
    return ::ControlService(hService, dwControl, lpServiceStatus);
}

SC_HANDLE WinApi::CreateService(
    SC_HANDLE hSCManager, LPCSTR lpServiceName, LPCSTR lpDisplayName,
    DWORD dwDesiredAccess, DWORD dwServiceType, DWORD dwStartType,
    DWORD dwErrorControl,
    LPCSTR
        lpBinaryPathName /*,LPCSTR lpLoadOrderGroup,LPDWORD lpdwTagId,LPCSTR lpDependencies,LPCSTR lpServiceStartName,LPCSTR lpPassword*/)
    const {
    return ::CreateServiceA(
        hSCManager, lpServiceName, lpDisplayName, dwDesiredAccess,
        dwServiceType, dwStartType, dwErrorControl, lpBinaryPathName,
        0 /*lpLoadOrderGroup*/, 0 /*lpdwTagId*/, 0 /*lpDependencies*/,
        0 /*lpServiceStartName*/, 0 /*lpPassword*/);
}

WINBOOL WinApi::DeleteService(SC_HANDLE hService) const {
    return ::DeleteService(hService);
}

WINBOOL WinApi::EnumServicesStatusExW(
    SC_HANDLE hSCManager, SC_ENUM_TYPE InfoLevel, DWORD dwServiceType,
    DWORD dwServiceState, LPBYTE lpServices, DWORD cbBufSize,
    LPDWORD pcbBytesNeeded, LPDWORD lpServicesReturned, LPDWORD lpResumeHandle,
    LPCWSTR pszGroupName) const {
    return ::EnumServicesStatusExW(
        hSCManager, static_cast<::SC_ENUM_TYPE>(InfoLevel), dwServiceType,
        dwServiceState, lpServices, cbBufSize, pcbBytesNeeded,
        lpServicesReturned, lpResumeHandle, pszGroupName);
}

WINBOOL WinApi::GetNumberOfEventLogRecords(HANDLE hEventLog,
                                           PDWORD NumberOfRecords) const {
    return ::GetNumberOfEventLogRecords(hEventLog, NumberOfRecords);
}

WINBOOL WinApi::GetOldestEventLogRecord(HANDLE hEventLog,
                                        PDWORD OldestRecord) const {
    return ::GetOldestEventLogRecord(hEventLog, OldestRecord);
}

WINBOOL WinApi::GetTokenInformation(
    HANDLE TokenHandle, TOKEN_INFORMATION_CLASS TokenInformationClass,
    LPVOID TokenInformation, DWORD TokenInformationLength,
    PDWORD ReturnLength) const {
    return ::GetTokenInformation(TokenHandle, TokenInformationClass,
                                 TokenInformation, TokenInformationLength,
                                 ReturnLength);
}

WINBOOL WinApi::InitializeSecurityDescriptor(
    PSECURITY_DESCRIPTOR pSecurityDescriptor, DWORD dwRevision) const {
    return ::InitializeSecurityDescriptor(pSecurityDescriptor, dwRevision);
}

WINBOOL WinApi::LookupAccountSidW(LPCWSTR lpSystemName, PSID Sid, LPWSTR Name,
                                  LPDWORD cchName, LPWSTR ReferencedDomainName,
                                  LPDWORD cchReferencedDomainName,
                                  PSID_NAME_USE peUse) const {
    return ::LookupAccountSidW(lpSystemName, Sid, Name, cchName,
                               ReferencedDomainName, cchReferencedDomainName,
                               peUse);
}

HANDLE WinApi::OpenEventLogW(LPCWSTR lpUNCServerName,
                             LPCWSTR lpSourceName) const {
    return ::OpenEventLogW(lpUNCServerName, lpSourceName);
}

WINBOOL WinApi::OpenProcessToken(HANDLE ProcessHandle, DWORD DesiredAccess,
                                 PHANDLE TokenHandle) const {
    return ::OpenProcessToken(ProcessHandle, DesiredAccess, TokenHandle);
}

SC_HANDLE WinApi::OpenSCManager(LPCSTR lpMachineName, LPCSTR lpDatabaseName,
                                DWORD dwDesiredAccess) const {
    return ::OpenSCManagerA(lpMachineName, lpDatabaseName, dwDesiredAccess);
}

SC_HANDLE WinApi::OpenService(SC_HANDLE hSCManager, LPCSTR lpServiceName,
                              DWORD dwDesiredAccess) const {
    return ::OpenServiceA(hSCManager, lpServiceName, dwDesiredAccess);
}

SC_HANDLE WinApi::OpenServiceW(SC_HANDLE hSCManager, LPCWSTR lpServiceName,
                               DWORD dwDesiredAccess) const {
    return ::OpenServiceW(hSCManager, lpServiceName, dwDesiredAccess);
}

WINBOOL WinApi::QueryServiceConfig(SC_HANDLE hService,
                                   LPQUERY_SERVICE_CONFIGW lpServiceConfig,
                                   DWORD cbBufSize,
                                   LPDWORD pcbBytesNeeded) const {
    return ::QueryServiceConfigW(hService, lpServiceConfig, cbBufSize,
                                 pcbBytesNeeded);
}

WINBOOL WinApi::QueryServiceStatus(SC_HANDLE hService,
                                   LPSERVICE_STATUS lpServiceStatus) const {
    return ::QueryServiceStatus(hService, lpServiceStatus);
}

WINBOOL WinApi::ReadEventLogW(HANDLE hEventLog, DWORD dwReadFlags,
                              DWORD dwRecordOffset, LPVOID lpBuffer,
                              DWORD nNumberOfBytesToRead, DWORD *pnBytesRead,
                              DWORD *pnMinNumberOfBytesNeeded) const {
    return ::ReadEventLogW(hEventLog, dwReadFlags, dwRecordOffset, lpBuffer,
                           nNumberOfBytesToRead, pnBytesRead,
                           pnMinNumberOfBytesNeeded);
}

LONG WinApi::RegCloseKey(HKEY hKey) const { return ::RegCloseKey(hKey); }

LONG WinApi::RegEnumKeyEx(HKEY hKey, DWORD dwIndex, LPSTR lpName,
                          LPDWORD lpcchName, LPDWORD lpReserved, LPSTR lpClass,
                          LPDWORD lpcchClass,
                          PFILETIME lpftLastWriteTime) const {
    return ::RegEnumKeyExA(hKey, dwIndex, lpName, lpcchName, lpReserved,
                           lpClass, lpcchClass, lpftLastWriteTime);
}

SERVICE_STATUS_HANDLE WinApi::RegisterServiceCtrlHandler(
    LPCSTR lpServiceName, LPHANDLER_FUNCTION lpHandlerProc) const {
    return ::RegisterServiceCtrlHandlerA(lpServiceName, lpHandlerProc);
}

LONG WinApi::RegOpenKeyEx(HKEY hKey, LPCSTR lpSubKey, DWORD ulOptions,
                          REGSAM samDesired, PHKEY phkResult) const {
    return ::RegOpenKeyExA(hKey, lpSubKey, ulOptions, samDesired, phkResult);
}

LONG WinApi::RegOpenKeyExW(HKEY hKey, LPCWSTR lpSubKey, DWORD ulOptions,
                           REGSAM samDesired, PHKEY phkResult) const {
    return ::RegOpenKeyExW(hKey, lpSubKey, ulOptions, samDesired, phkResult);
}

LONG WinApi::RegQueryValueEx(HKEY hKey, LPCSTR lpValueName, LPDWORD lpReserved,
                             LPDWORD lpType, LPBYTE lpData,
                             LPDWORD lpcbData) const {
    return ::RegQueryValueEx(hKey, lpValueName, lpReserved, lpType, lpData,
                             lpcbData);
}

LONG WinApi::RegQueryValueExW(HKEY hKey, LPCWSTR lpValueName,
                              LPDWORD lpReserved, LPDWORD lpType, LPBYTE lpData,
                              LPDWORD lpcbData) const {
    return ::RegQueryValueExW(hKey, lpValueName, lpReserved, lpType, lpData,
                              lpcbData);
}

WINBOOL WinApi::SetSecurityDescriptorDacl(
    PSECURITY_DESCRIPTOR pSecurityDescriptor, WINBOOL bDaclPresent, PACL pDacl,
    WINBOOL bDaclDefaulted) const {
    return ::SetSecurityDescriptorDacl(pSecurityDescriptor, bDaclPresent, pDacl,
                                       bDaclDefaulted);
}

WINBOOL WinApi::SetServiceStatus(SERVICE_STATUS_HANDLE hServiceStatus,
                                 LPSERVICE_STATUS lpServiceStatus) const {
    return ::SetServiceStatus(hServiceStatus, lpServiceStatus);
}

WINBOOL WinApi::StartServiceCtrlDispatcher(
    const SERVICE_TABLE_ENTRY *lpServiceStartTable) const {
    return ::StartServiceCtrlDispatcherA(lpServiceStartTable);
}

// WINBASEAPI:
WINBOOL WinApi::AssignProcessToJobObject(HANDLE hJob, HANDLE hProcess) const {
    return ::AssignProcessToJobObject(hJob, hProcess);
}

WINBOOL WinApi::CloseHandle(HANDLE hObject) const {
    return ::CloseHandle(hObject);
}

LONG WinApi::CompareFileTime(const FILETIME *lpFileTime1,
                             const FILETIME *lpFileTime2) const {
    return ::CompareFileTime(lpFileTime1, lpFileTime2);
}

WINBOOL WinApi::CreateDirectory(
    LPCSTR lpPathName, LPSECURITY_ATTRIBUTES lpSecurityAttributes) const {
    return ::CreateDirectoryA(lpPathName, lpSecurityAttributes);
}

WINBOOL WinApi::CreateDirectoryA(
    LPCSTR lpPathName, LPSECURITY_ATTRIBUTES lpSecurityAttributes) const {
    return ::CreateDirectoryA(lpPathName, lpSecurityAttributes);
}

HANDLE WinApi::CreateEvent(LPSECURITY_ATTRIBUTES lpEventAttributes,
                           WINBOOL bManualReset, WINBOOL bInitialState,
                           LPCSTR lpName) const {
    return ::CreateEventA(lpEventAttributes, bManualReset, bInitialState,
                          lpName);
}

HANDLE WinApi::CreateFile(LPCSTR lpFileName, DWORD dwDesiredAccess,
                          DWORD dwShareMode,
                          LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                          DWORD dwCreationDisposition,
                          DWORD dwFlagsAndAttributes,
                          HANDLE hTemplateFile) const {
    return ::CreateFileA(lpFileName, dwDesiredAccess, dwShareMode,
                         lpSecurityAttributes, dwCreationDisposition,
                         dwFlagsAndAttributes, hTemplateFile);
}

HANDLE WinApi::CreateJobObject(LPSECURITY_ATTRIBUTES lpJobAttributes,
                               LPCSTR lpName) const {
    return ::CreateJobObjectA(lpJobAttributes, lpName);
}

HANDLE WinApi::CreateMutex(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                           WINBOOL bInitialOwner, LPCSTR lpName) const {
    return ::CreateMutexA(lpMutexAttributes, bInitialOwner, lpName);
}

HANDLE WinApi::CreateMutexA(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                            WINBOOL bInitialOwner, LPCSTR lpName) const {
    return ::CreateMutexA(lpMutexAttributes, bInitialOwner, lpName);
}

WINBOOL WinApi::CreatePipe(PHANDLE hReadPipe, PHANDLE hWritePipe,
                           LPSECURITY_ATTRIBUTES lpPipeAttributes,
                           DWORD nSize) const {
    return ::CreatePipe(hReadPipe, hWritePipe, lpPipeAttributes, nSize);
}

WINBOOL WinApi::CreateProcess(
    LPCSTR lpApplicationName, LPSTR lpCommandLine,
    LPSECURITY_ATTRIBUTES lpProcessAttributes,
    LPSECURITY_ATTRIBUTES lpThreadAttributes, WINBOOL bInheritHandles,
    DWORD dwCreationFlags, LPVOID lpEnvironment, LPCSTR lpCurrentDirectory,
    LPSTARTUPINFO lpStartupInfo,
    LPPROCESS_INFORMATION lpProcessInformation) const {
    return ::CreateProcess(
        lpApplicationName, lpCommandLine, lpProcessAttributes,
        lpThreadAttributes, bInheritHandles, dwCreationFlags, lpEnvironment,
        lpCurrentDirectory, lpStartupInfo, lpProcessInformation);
}

HANDLE WinApi::CreateThread(LPSECURITY_ATTRIBUTES lpThreadAttributes,
                            SIZE_T dwStackSize,
                            LPTHREAD_START_ROUTINE lpStartAddress,
                            LPVOID lpParameter, DWORD dwCreationFlags,
                            LPDWORD lpThreadId) const {
    return ::CreateThread(lpThreadAttributes, dwStackSize, lpStartAddress,
                          lpParameter, dwCreationFlags, lpThreadId);
}

WINBOOL WinApi::DeleteFile(LPCSTR lpFileName) const {
    return ::DeleteFileA(lpFileName);
}

WINBOOL WinApi::DuplicateHandle(HANDLE hSourceProcessHandle,
                                HANDLE hSourceHandle,
                                HANDLE hTargetProcessHandle,
                                LPHANDLE lpTargetHandle, DWORD dwDesiredAccess,
                                WINBOOL bInheritHandle, DWORD dwOptions) const {
    return ::DuplicateHandle(hSourceProcessHandle, hSourceHandle,
                             hTargetProcessHandle, lpTargetHandle,
                             dwDesiredAccess, bInheritHandle, dwOptions);
}

DWORD WinApi::ExpandEnvironmentStringsW(LPCWSTR lpSrc, LPWSTR lpDst,
                                        DWORD nSize) const {
    return ::ExpandEnvironmentStringsW(lpSrc, lpDst, nSize);
}

WINBOOL WinApi::FindClose(HANDLE hFindFile) const {
    return ::FindClose(hFindFile);
}

HANDLE WinApi::FindFirstFile(LPCSTR lpFileName,
                             LPWIN32_FIND_DATA lpFindFileData) const {
    return ::FindFirstFileA(lpFileName, lpFindFileData);
}

HANDLE WinApi::FindFirstFileEx(LPCSTR lpFileName, int fInfoLevelId,
                               LPVOID lpFindFileData, int fSearchOp,
                               LPVOID lpSearchFilter,
                               DWORD dwAdditionalFlags) const {
    return ::FindFirstFileExA(
        lpFileName, static_cast<FINDEX_INFO_LEVELS>(fInfoLevelId),
        lpFindFileData, static_cast<FINDEX_SEARCH_OPS>(fSearchOp),
        lpSearchFilter, dwAdditionalFlags);
}

HANDLE WinApi::FindFirstVolumeMountPoint(LPCSTR lpszRootPathName,
                                         LPSTR lpszVolumeMountPoint,
                                         DWORD cchBufferLength) const {
    return ::FindFirstVolumeMountPointA(lpszRootPathName, lpszVolumeMountPoint,
                                        cchBufferLength);
}

WINBOOL WinApi::FindNextFile(HANDLE hFindFile,
                             LPWIN32_FIND_DATAA lpFindFileData) const {
    return ::FindNextFileA(hFindFile, lpFindFileData);
}

WINBOOL WinApi::FindNextVolumeMountPoint(HANDLE hFindVolumeMountPoint,
                                         LPSTR lpszVolumeMountPoint,
                                         DWORD cchBufferLength) const {
    return ::FindNextVolumeMountPointA(hFindVolumeMountPoint,
                                       lpszVolumeMountPoint, cchBufferLength);
}

WINBOOL WinApi::FindVolumeMountPointClose(HANDLE hFindVolumeMountPoint) const {
    return ::FindVolumeMountPointClose(hFindVolumeMountPoint);
}

WINBOOL WinApi::FlushFileBuffers(HANDLE hFile) const {
    return ::FlushFileBuffers(hFile);
}

DWORD WinApi::FormatMessageA(DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId,
                             DWORD dwLanguageId, LPSTR lpBuffer, DWORD nSize,
                             va_list *Arguments) const {
    return ::FormatMessageA(dwFlags, lpSource, dwMessageId, dwLanguageId,
                            lpBuffer, nSize, Arguments);
}

DWORD WinApi::FormatMessageW(DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId,
                             DWORD dwLanguageId, LPWSTR lpBuffer, DWORD nSize,
                             va_list *Arguments) const {
    return ::FormatMessageW(dwFlags, lpSource, dwMessageId, dwLanguageId,
                            lpBuffer, nSize, Arguments);
}

WINBOOL WinApi::FreeLibrary(HMODULE hLibModule) const {
    return ::FreeLibrary(hLibModule);
}

HANDLE WinApi::GetCurrentProcess(void) const { return ::GetCurrentProcess(); }

DWORD WinApi::GetCurrentDirectoryA(DWORD nBufferLength, LPSTR lpBuffer) const {
    return ::GetCurrentDirectoryA(nBufferLength, lpBuffer);
}

WINBOOL WinApi::GetExitCodeProcess(HANDLE hProcess, LPDWORD lpExitCode) const {
    return ::GetExitCodeProcess(hProcess, lpExitCode);
}

WINBOOL WinApi::GetExitCodeThread(HANDLE hThread, LPDWORD lpExitCode) const {
    return ::GetExitCodeThread(hThread, lpExitCode);
}

WINBOOL WinApi::GetFileInformationByHandle(
    HANDLE hFile, LPBY_HANDLE_FILE_INFORMATION lpFileInformation) const {
    return ::GetFileInformationByHandle(hFile, lpFileInformation);
}

DWORD WinApi::GetFileAttributes(LPCSTR lpFileName) const {
    return ::GetFileAttributes(lpFileName);
}

WINBOOL WinApi::GetDiskFreeSpaceEx(
    LPCSTR lpDirectoryName, PULARGE_INTEGER lpFreeBytesAvailableToCaller,
    PULARGE_INTEGER lpTotalNumberOfBytes,
    PULARGE_INTEGER lpTotalNumberOfFreeBytes) const {
    return ::GetDiskFreeSpaceExA(lpDirectoryName, lpFreeBytesAvailableToCaller,
                                 lpTotalNumberOfBytes,
                                 lpTotalNumberOfFreeBytes);
}

UINT WinApi::GetDriveType(LPCSTR lpRootPathName) const {
    return ::GetDriveTypeA(lpRootPathName);
}

DWORD WinApi::GetLastError(void) const { return ::GetLastError(); }

DWORD WinApi::GetLogicalDriveStrings(DWORD nBufferLength,
                                     LPSTR lpBuffer) const {
    return ::GetLogicalDriveStringsA(nBufferLength, lpBuffer);
}

DWORD WinApi::GetModuleFileName(HMODULE hModule, LPSTR lpFilename,
                                DWORD nSize) const {
    return ::GetModuleFileNameA(hModule, lpFilename, nSize);
}

FARPROC WinApi::GetProcAddress(HMODULE hModule, LPCSTR lpProcName) const {
    return ::GetProcAddress(hModule, lpProcName);
}

HANDLE WinApi::GetProcessHeap(void) const { return ::GetProcessHeap(); }

WINBOOL WinApi::GetProcessTimes(HANDLE hProcess, LPFILETIME lpCreationTime,
                                LPFILETIME lpExitTime, LPFILETIME lpKernelTime,
                                LPFILETIME lpUserTime) const {
    return ::GetProcessTimes(hProcess, lpCreationTime, lpExitTime, lpKernelTime,
                             lpUserTime);
}

VOID WinApi::GetStartupInfo(LPSTARTUPINFO lpStartupInfo) const {
    return ::GetStartupInfoA(lpStartupInfo);
}

VOID WinApi::GetSystemInfo(LPSYSTEM_INFO lpSystemInfo) const {
    return ::GetSystemInfo(lpSystemInfo);
}

VOID WinApi::GetSystemTime(LPSYSTEMTIME lpSystemTime) const {
    return ::GetSystemTime(lpSystemTime);
}

WINBOOL WinApi::GetVersionEx(LPOSVERSIONINFO lpVersionInformation) const {
    return ::GetVersionExA(lpVersionInformation);
}

WINBOOL WinApi::GetVolumeInformation(
    LPCSTR lpRootPathName, LPSTR lpVolumeNameBuffer, DWORD nVolumeNameSize,
    LPDWORD lpVolumeSerialNumber, LPDWORD lpMaximumComponentLength,
    LPDWORD lpFileSystemFlags, LPSTR lpFileSystemNameBuffer,
    DWORD nFileSystemNameSize) const {
    return ::GetVolumeInformationA(lpRootPathName, lpVolumeNameBuffer,
                                   nVolumeNameSize, lpVolumeSerialNumber,
                                   lpMaximumComponentLength, lpFileSystemFlags,
                                   lpFileSystemNameBuffer, nFileSystemNameSize);
}

WINBOOL WinApi::GlobalMemoryStatusEx(LPMEMORYSTATUSEX lpBuffer) const {
    return ::GlobalMemoryStatusEx(lpBuffer);
}

LPVOID WinApi::HeapAlloc(HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes) const {
    return ::HeapAlloc(hHeap, dwFlags, dwBytes);
}

WINBOOL WinApi::HeapFree(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem) const {
    return ::HeapFree(hHeap, dwFlags, lpMem);
}

LPVOID WinApi::HeapReAlloc(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem,
                           SIZE_T dwBytes) const {
    return ::HeapReAlloc(hHeap, dwFlags, lpMem, dwBytes);
}

SIZE_T WinApi::HeapSize(HANDLE hHeap, DWORD dwFlags, LPCVOID lpMem) const {
    return ::HeapSize(hHeap, dwFlags, lpMem);
}

HMODULE WinApi::LoadLibraryExW(LPCWSTR lpLibFileName, HANDLE hFile,
                               DWORD dwFlags) const {
    return ::LoadLibraryExW(lpLibFileName, hFile, dwFlags);
}

HMODULE WinApi::LoadLibraryW(LPCWSTR lpLibFileName) const {
    return ::LoadLibraryW(lpLibFileName);
}

HLOCAL WinApi::LocalAlloc(UINT uFlags, SIZE_T uBytes) const {
    return ::LocalAlloc(uFlags, uBytes);
}

HLOCAL WinApi::LocalFree(HLOCAL hMem) const { return ::LocalFree(hMem); }

int WinApi::MultiByteToWideChar(UINT CodePage, DWORD dwFlags,
                                LPCCH lpMultiByteStr, int cbMultiByte,
                                LPWSTR lpWideCharStr, int cchWideChar) const {
    return ::MultiByteToWideChar(CodePage, dwFlags, lpMultiByteStr, cbMultiByte,
                                 lpWideCharStr, cchWideChar);
}

HANDLE WinApi::OpenProcess(DWORD dwDesiredAccess, WINBOOL bInheritHandle,
                           DWORD dwProcessId) const {
    return ::OpenProcess(dwDesiredAccess, bInheritHandle, dwProcessId);
}

WINBOOL WinApi::MoveFile(LPCSTR lpExistingFileName,
                         LPCSTR lpNewFileName) const {
    return ::MoveFileA(lpExistingFileName, lpNewFileName);
}

WINBOOL WinApi::PeekNamedPipe(HANDLE hNamedPipe, LPVOID lpBuffer,
                              DWORD nBufferSize, LPDWORD lpBytesRead,
                              LPDWORD lpTotalBytesAvail,
                              LPDWORD lpBytesLeftThisMessage) const {
    return ::PeekNamedPipe(hNamedPipe, lpBuffer, nBufferSize, lpBytesRead,
                           lpTotalBytesAvail, lpBytesLeftThisMessage);
}

WINBOOL WinApi::QueryPerformanceCounter(
    LARGE_INTEGER *lpPerformanceCount) const {
    return ::QueryPerformanceCounter(lpPerformanceCount);
}

WINBOOL WinApi::QueryPerformanceFrequency(LARGE_INTEGER *lpFrequency) const {
    return ::QueryPerformanceFrequency(lpFrequency);
}

WINBOOL WinApi::ReadFile(HANDLE hFile, LPVOID lpBuffer,
                         DWORD nNumberOfBytesToRead,
                         LPDWORD lpNumberOfBytesRead,
                         LPOVERLAPPED lpOverlapped) const {
    return ::ReadFile(hFile, lpBuffer, nNumberOfBytesToRead,
                      lpNumberOfBytesRead, lpOverlapped);
}

WINBOOL WinApi::ReleaseMutex(HANDLE hMutex) const {
    return ::ReleaseMutex(hMutex);
}

WINBOOL WinApi::ResetEvent(HANDLE hEvent) const { return ::ResetEvent(hEvent); }

DWORD WinApi::SearchPathA(LPCSTR lpPath, LPCSTR lpFileName, LPCSTR lpExtension,
                          DWORD nBufferLength, LPSTR lpBuffer,
                          LPSTR *lpFilePart) const {
    return ::SearchPathA(lpPath, lpFileName, lpExtension, nBufferLength,
                         lpBuffer, lpFilePart);
}

WINBOOL WinApi::SetConsoleCtrlHandler(PHANDLER_ROUTINE HandlerRoutine,
                                      WINBOOL Add) const {
    return ::SetConsoleCtrlHandler(HandlerRoutine, Add);
}

WINBOOL WinApi::SetEnvironmentVariable(LPCSTR lpName, LPCSTR lpValue) const {
    return ::SetEnvironmentVariableA(lpName, lpValue);
}

LPTOP_LEVEL_EXCEPTION_FILTER WinApi::SetUnhandledExceptionFilter(
    LPTOP_LEVEL_EXCEPTION_FILTER lpTopLevelExceptionFilter) const {
    return ::SetUnhandledExceptionFilter(lpTopLevelExceptionFilter);
}

VOID WinApi::Sleep(DWORD dwMilliseconds) const { ::Sleep(dwMilliseconds); }

WINBOOL WinApi::SystemTimeToFileTime(const SYSTEMTIME *lpSystemTime,
                                     LPFILETIME lpFileTime) const {
    return ::SystemTimeToFileTime(lpSystemTime, lpFileTime);
}

WINBOOL WinApi::TerminateJobObject(HANDLE hJob, UINT uExitCode) const {
    return ::TerminateJobObject(hJob, uExitCode);
}

WINBOOL WinApi::TerminateProcess(HANDLE hProcess, UINT uExitCode) const {
    return ::TerminateProcess(hProcess, uExitCode);
}

WINBOOL WinApi::TerminateThread(HANDLE hThread, DWORD dwExitCode) const {
    return ::TerminateThread(hThread, dwExitCode);
}

DWORD WinApi::WaitForMultipleObjects(DWORD nCount, const HANDLE *lpHandles,
                                     WINBOOL bWaitAll,
                                     DWORD dwMilliseconds) const {
    return ::WaitForMultipleObjects(nCount, lpHandles, bWaitAll,
                                    dwMilliseconds);
}

DWORD WinApi::WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds) const {
    return ::WaitForSingleObject(hHandle, dwMilliseconds);
}

WINBOOL WinApi::WriteFile(HANDLE hFile, LPCVOID lpBuffer,
                          DWORD nNumberOfBytesToWrite,
                          LPDWORD lpNumberOfBytesWritten,
                          LPOVERLAPPED lpOverlapped) const {
    return ::WriteFile(hFile, lpBuffer, nNumberOfBytesToWrite,
                       lpNumberOfBytesWritten, lpOverlapped);
}

// WINIMPM:
WINBOOL WinApi::CryptAcquireContext(HCRYPTPROV *phProv, LPCSTR szContainer,
                                    LPCSTR szProvider, DWORD dwProvType,
                                    DWORD dwFlags) const {
    return ::CryptAcquireContextA(phProv, szContainer, szProvider, dwProvType,
                                  dwFlags);
}

WINBOOL WinApi::CryptCreateHash(HCRYPTPROV hProv, ALG_ID Algid, HCRYPTKEY hKey,
                                DWORD dwFlags, HCRYPTHASH *phHash) const {
    return ::CryptCreateHash(hProv, Algid, hKey, dwFlags, phHash);
}

WINBOOL WinApi::CryptDecrypt(HCRYPTKEY hKey, HCRYPTHASH hHash, WINBOOL Final,
                             DWORD dwFlags, BYTE *pbData,
                             DWORD *pdwDataLen) const {
    return ::CryptDecrypt(hKey, hHash, Final, dwFlags, pbData, pdwDataLen);
}

WINBOOL WinApi::CryptDestroyHash(HCRYPTHASH hHash) const {
    return ::CryptDestroyHash(hHash);
}

WINBOOL WinApi::CryptDestroyKey(HCRYPTKEY hKey) const {
    return ::CryptDestroyKey(hKey);
}

WINBOOL WinApi::CryptDuplicateHash(HCRYPTHASH hHash, DWORD *pdwReserved,
                                   DWORD dwFlags, HCRYPTHASH *phHash) const {
    return ::CryptDuplicateHash(hHash, pdwReserved, dwFlags, phHash);
}

WINBOOL WinApi::CryptEncrypt(HCRYPTKEY hKey, HCRYPTHASH hHash, WINBOOL Final,
                             DWORD dwFlags, BYTE *pbData, DWORD *pdwDataLen,
                             DWORD dwBufLen) const {
    return ::CryptEncrypt(hKey, hHash, Final, dwFlags, pbData, pdwDataLen,
                          dwBufLen);
}

WINBOOL WinApi::CryptExportKey(HCRYPTKEY hKey, HCRYPTKEY hExpKey,
                               DWORD dwBlobType, DWORD dwFlags, BYTE *pbData,
                               DWORD *pdwDataLen) const {
    return ::CryptExportKey(hKey, hExpKey, dwBlobType, dwFlags, pbData,
                            pdwDataLen);
}

WINBOOL WinApi::CryptGenKey(HCRYPTPROV hProv, ALG_ID Algid, DWORD dwFlags,
                            HCRYPTKEY *phKey) const {
    return ::CryptGenKey(hProv, Algid, dwFlags, phKey);
}

WINBOOL WinApi::CryptGenRandom(HCRYPTPROV hProv, DWORD dwLen,
                               BYTE *pbBuffer) const {
    return ::CryptGenRandom(hProv, dwLen, pbBuffer);
}

WINBOOL WinApi::CryptGetHashParam(HCRYPTHASH hHash, DWORD dwParam, BYTE *pbData,
                                  DWORD *pdwDataLen, DWORD dwFlags) const {
    return ::CryptGetHashParam(hHash, dwParam, pbData, pdwDataLen, dwFlags);
}

WINBOOL WinApi::CryptGetKeyParam(HCRYPTKEY hKey, DWORD dwParam, BYTE *pbData,
                                 DWORD *pdwDataLen, DWORD dwFlags) const {
    return ::CryptGetKeyParam(hKey, dwParam, pbData, pdwDataLen, dwFlags);
}

WINBOOL WinApi::CryptHashData(HCRYPTHASH hHash, const BYTE *pbData,
                              DWORD dwDataLen, DWORD dwFlags) const {
    return ::CryptHashData(hHash, pbData, dwDataLen, dwFlags);
}

WINBOOL WinApi::CryptImportKey(HCRYPTPROV hProv, const BYTE *pbData,
                               DWORD dwDataLen, HCRYPTKEY hPubKey,
                               DWORD dwFlags, HCRYPTKEY *phKey) const {
    return ::CryptImportKey(hProv, pbData, dwDataLen, hPubKey, dwFlags, phKey);
}

WINBOOL WinApi::CryptReleaseContext(HCRYPTPROV hProv, DWORD dwFlags) const {
    return ::CryptReleaseContext(hProv, dwFlags);
}

WINBOOL WinApi::CryptSetKeyParam(HCRYPTKEY hKey, DWORD dwParam,
                                 const BYTE *pbData, DWORD dwFlags) const {
    return ::CryptSetKeyParam(hKey, dwParam, pbData, dwFlags);
}

// WINOLEAPI:
HRESULT WinApi::CoCreateInstance(REFCLSID rclsid, LPUNKNOWN pUnkOuter,
                                 DWORD dwClsContext, const IID &riid,
                                 LPVOID *ppv) const {
    return ::CoCreateInstance(rclsid, pUnkOuter, dwClsContext, riid, ppv);
}

HRESULT WinApi::CoInitializeEx(LPVOID pvReserved, DWORD dwCoInit) const {
    return ::CoInitializeEx(pvReserved, dwCoInit);
}

HRESULT WinApi::CoInitializeSecurity(PSECURITY_DESCRIPTOR pSecDesc,
                                     LONG cAuthSvc,
                                     SOLE_AUTHENTICATION_SERVICE *asAuthSvc,
                                     void *pReserved1, DWORD dwAuthnLevel,
                                     DWORD dwImpLevel, void *pAuthList,
                                     DWORD dwCapabilities,
                                     void *pReserved3) const {
    return ::CoInitializeSecurity(pSecDesc, cAuthSvc, asAuthSvc, pReserved1,
                                  dwAuthnLevel, dwImpLevel, pAuthList,
                                  dwCapabilities, pReserved3);
}

HRESULT WinApi::CoSetProxyBlanket(IUnknown *pProxy, DWORD dwAuthnSvc,
                                  DWORD dwAuthzSvc, OLECHAR *pServerPrincName,
                                  DWORD dwAuthnLevel, DWORD dwImpLevel,
                                  RPC_AUTH_IDENTITY_HANDLE pAuthInfo,
                                  DWORD dwCapabilities) const {
    return ::CoSetProxyBlanket(pProxy, dwAuthnSvc, dwAuthzSvc, pServerPrincName,
                               dwAuthnLevel, dwImpLevel, pAuthInfo,
                               dwCapabilities);
}
void WinApi::CoUninitialize(void) const { ::CoUninitialize(); }

// WINOLEAUTAPI:
HRESULT WinApi::GetErrorInfo(ULONG dwReserved, IErrorInfo **pperrinfo) const {
    return ::GetErrorInfo(dwReserved, pperrinfo);
}

HRESULT WinApi::SafeArrayDestroy(SAFEARRAY *psa) const {
    return ::SafeArrayDestroy(psa);
}

HRESULT WinApi::SafeArrayGetElement(SAFEARRAY *psa, LONG *rgIndices,
                                    void *pv) const {
    return ::SafeArrayGetElement(psa, rgIndices, pv);
}

HRESULT WinApi::SafeArrayGetLBound(SAFEARRAY *psa, UINT nDim,
                                   LONG *plLbound) const {
    return ::SafeArrayGetLBound(psa, nDim, plLbound);
}

HRESULT WinApi::SafeArrayGetUBound(SAFEARRAY *psa, UINT nDim,
                                   LONG *plUbound) const {
    return ::SafeArrayGetUBound(psa, nDim, plUbound);
}

BSTR WinApi::SysAllocString(const OLECHAR *ptr) const {
    return ::SysAllocString(ptr);
}

void WinApi::SysFreeString(BSTR str) const { return ::SysFreeString(str); }

HRESULT WinApi::VariantClear(VARIANTARG *pvarg) const {
    return ::VariantClear(pvarg);
}

// WSAAPI:
SOCKET WinApi::accept(SOCKET s, struct sockaddr *addr, int *addrlen) const {
    return ::accept(s, addr, addrlen);
}

int WinApi::bind(SOCKET s, const struct sockaddr *name, int namelen) const {
    return ::bind(s, name, namelen);
}

int WinApi::closesocket(SOCKET s) const { return ::closesocket(s); }

int WinApi::connect(SOCKET s, const struct sockaddr *name, int namelen) const {
    return ::connect(s, name, namelen);
}

int WinApi::gethostname(char *name, int namelen) const {
    return ::gethostname(name, namelen);
}

int WinApi::getpeername(SOCKET s, struct sockaddr *name, int *namelen) const {
    return ::getpeername(s, name, namelen);
}

u_short WinApi::htons(u_short hostshort) const { return ::htons(hostshort); }

int WinApi::listen(SOCKET s, int backlog) const { return ::listen(s, backlog); }

int WinApi::select(int nfds, fd_set *readfds, fd_set *writefds,
                   fd_set *exceptfds, const PTIMEVAL timeout) const {
    return ::select(nfds, readfds, writefds, exceptfds, timeout);
}

int WinApi::send(SOCKET s, const char *buf, int len, int flags) const {
    return ::send(s, buf, len, flags);
}

int WinApi::setsockopt(SOCKET s, int level, int optname, const char *optval,
                       int optlen) const {
    return ::setsockopt(s, level, optname, optval, optlen);
}

SOCKET WinApi::socket(int af, int type, int protocol) const {
    return ::socket(af, type, protocol);
}

int WinApi::WSACleanup(void) const { return ::WSACleanup(); }

int WinApi::WSAGetLastError(void) const { return ::WSAGetLastError(); }

int WinApi::WSAStartup(WORD wVersionRequested, LPWSADATA lpWSAData) const {
    return ::WSAStartup(wVersionRequested, lpWSAData);
}

// IMAGEAPI:
WINBOOL WinApi::SymCleanup(HANDLE hProcess) const {
    return ::SymCleanup(hProcess);
}
#ifdef __x86_64
WINBOOL WinApi::SymFromAddr(HANDLE hProcess, DWORD64 Address,
                            PDWORD64 Displacement, PSYMBOL_INFO Symbol) const {
    return ::SymFromAddr(hProcess, Address, Displacement, Symbol);
}
#endif  // __x86_64
WINBOOL WinApi::SymGetLineFromAddr64(HANDLE hProcess, DWORD64 qwAddr,
                                     PDWORD pdwDisplacement,
                                     PIMAGEHLP_LINE64 Line64) const {
    return ::SymGetLineFromAddr64(hProcess, qwAddr, pdwDisplacement, Line64);
}

DWORD WinApi::SymGetOptions(void) const { return ::SymGetOptions(); }

WINBOOL WinApi::SymInitialize(HANDLE hProcess, PCSTR UserSearchPath,
                              WINBOOL fInvadeProcess) const {
    return ::SymInitialize(hProcess, UserSearchPath, fInvadeProcess);
}

DWORD WinApi::SymSetOptions(DWORD SymOptions) const {
    return ::SymSetOptions(SymOptions);
}

// NTAPI:
#ifdef __x86_64

VOID WinApi::RtlCaptureContext(PCONTEXT ContextRecord) const {
    return ::RtlCaptureContext(ContextRecord);
}

PRUNTIME_FUNCTION WinApi::RtlLookupFunctionEntry(
    DWORD64 ControlPc, PDWORD64 ImageBase,
    PUNWIND_HISTORY_TABLE HistoryTable) const {
    return ::RtlLookupFunctionEntry(ControlPc, ImageBase, HistoryTable);
}

PEXCEPTION_ROUTINE WinApi::RtlVirtualUnwind(
    DWORD HandlerType, DWORD64 ImageBase, DWORD64 ControlPc,
    PRUNTIME_FUNCTION FunctionEntry, PCONTEXT ContextRecord, PVOID *HandlerData,
    PDWORD64 EstablisherFrame,
    PKNONVOLATILE_CONTEXT_POINTERS ContextPointers) const {
    return ::RtlVirtualUnwind(HandlerType, ImageBase, ControlPc, FunctionEntry,
                              ContextRecord, HandlerData, EstablisherFrame,
                              ContextPointers);
}

#endif  // __x86_64

// MISC:
LPWSTR *WinApi::CommandLineToArgvW(LPCWSTR lpCmdLine, int *pNumArgs) const {
    return ::CommandLineToArgvW(lpCmdLine, pNumArgs);
}

HANDLE WinApi::CreateToolhelp32Snapshot(DWORD dwFlags,
                                        DWORD th32ProcessID) const {
    return ::CreateToolhelp32Snapshot(dwFlags, th32ProcessID);
}

WINBOOL WinApi::PathIsRelative(LPCSTR pszPath) const {
    return ::PathIsRelative(pszPath);
}

WINBOOL WinApi::Process32First(HANDLE hSnapshot, LPPROCESSENTRY32 lppe) const {
    return ::Process32First(hSnapshot, lppe);
}

WINBOOL WinApi::Process32Next(HANDLE hSnapshot, LPPROCESSENTRY32 lppe) const {
    return ::Process32Next(hSnapshot, lppe);
}
