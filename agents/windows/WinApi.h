#ifndef WinApi_h
#define WinApi_h

#include "WinApiAdaptor.h"

class WinApi : public WinApiAdaptor {
public:
    // WINADVAPI:
    virtual WINBOOL CloseEventLog(HANDLE hEventLog) const override;
    virtual WINBOOL CloseServiceHandle(SC_HANDLE hSCObject) const override;
    virtual WINBOOL ControlService(
        SC_HANDLE hService, DWORD dwControl,
        LPSERVICE_STATUS lpServiceStatus) const override;
    virtual SC_HANDLE CreateService(
        SC_HANDLE hSCManager, LPCSTR lpServiceName, LPCSTR lpDisplayName,
        DWORD dwDesiredAccess, DWORD dwServiceType, DWORD dwStartType,
        DWORD dwErrorControl,
        LPCSTR
            lpBinaryPathName /* ,LPCSTR lpLoadOrderGroup,LPDWORD lpdwTagId,LPCSTR lpDependencies,LPCSTR lpServiceStartName,LPCSTR lpPassword */)
        const override;  // last 5 params are always 0!
    virtual WINBOOL DeleteService(SC_HANDLE hService) const override;
    virtual WINBOOL EnumServicesStatusExW(
        SC_HANDLE hSCManager, SC_ENUM_TYPE InfoLevel, DWORD dwServiceType,
        DWORD dwServiceState, LPBYTE lpServices, DWORD cbBufSize,
        LPDWORD pcbBytesNeeded, LPDWORD lpServicesReturned,
        LPDWORD lpResumeHandle, LPCWSTR pszGroupName) const override;
    virtual WINBOOL GetNumberOfEventLogRecords(
        HANDLE hEventLog, PDWORD NumberOfRecords) const override;
    virtual WINBOOL GetOldestEventLogRecord(HANDLE hEventLog,
                                            PDWORD OldestRecord) const override;
    virtual WINBOOL GetTokenInformation(
        HANDLE TokenHandle, TOKEN_INFORMATION_CLASS TokenInformationClass,
        LPVOID TokenInformation, DWORD TokenInformationLength,
        PDWORD ReturnLength) const override;
    virtual WINBOOL InitializeSecurityDescriptor(
        PSECURITY_DESCRIPTOR pSecurityDescriptor,
        DWORD dwRevision) const override;
    virtual WINBOOL LookupAccountSidW(LPCWSTR lpSystemName, PSID Sid,
                                      LPWSTR Name, LPDWORD cchName,
                                      LPWSTR ReferencedDomainName,
                                      LPDWORD cchReferencedDomainName,
                                      PSID_NAME_USE peUse) const override;
    virtual HANDLE OpenEventLogW(LPCWSTR lpUNCServerName,
                                 LPCWSTR lpSourceName) const override;
    virtual WINBOOL OpenProcessToken(HANDLE ProcessHandle, DWORD DesiredAccess,
                                     PHANDLE TokenHandle) const override;
    virtual SC_HANDLE OpenSCManager(LPCSTR lpMachineName, LPCSTR lpDatabaseName,
                                    DWORD dwDesiredAccess) const override;
    virtual SC_HANDLE OpenService(SC_HANDLE hSCManager, LPCSTR lpServiceName,
                                  DWORD dwDesiredAccess) const override;
    virtual SC_HANDLE OpenServiceW(SC_HANDLE hSCManager, LPCWSTR lpServiceName,
                                   DWORD dwDesiredAccess) const override;
    virtual WINBOOL QueryServiceConfig(SC_HANDLE hService,
                                       LPQUERY_SERVICE_CONFIGW lpServiceConfig,
                                       DWORD cbBufSize,
                                       LPDWORD pcbBytesNeeded) const override;
    virtual WINBOOL QueryServiceStatus(
        SC_HANDLE hService, LPSERVICE_STATUS lpServiceStatus) const override;
    virtual WINBOOL ReadEventLogW(
        HANDLE hEventLog, DWORD dwReadFlags, DWORD dwRecordOffset,
        LPVOID lpBuffer, DWORD nNumberOfBytesToRead, DWORD *pnBytesRead,
        DWORD *pnMinNumberOfBytesNeeded) const override;
    virtual LONG RegCloseKey(HKEY hKey) const override;
    virtual LONG RegEnumKeyEx(HKEY hKey, DWORD dwIndex, LPSTR lpName,
                              LPDWORD lpcchName, LPDWORD lpReserved,
                              LPSTR lpClass, LPDWORD lpcchClass,
                              PFILETIME lpftLastWriteTime) const override;
    virtual SERVICE_STATUS_HANDLE RegisterServiceCtrlHandler(
        LPCSTR lpServiceName, LPHANDLER_FUNCTION lpHandlerProc) const override;
    virtual LONG RegOpenKeyEx(HKEY hKey, LPCSTR lpSubKey, DWORD ulOptions,
                              REGSAM samDesired,
                              PHKEY phkResult) const override;
    virtual LONG RegOpenKeyExW(HKEY hKey, LPCWSTR lpSubKey, DWORD ulOptions,
                               REGSAM samDesired,
                               PHKEY phkResult) const override;
    virtual LONG RegQueryValueEx(HKEY hKey, LPCSTR lpValueName,
                                 LPDWORD lpReserved, LPDWORD lpType,
                                 LPBYTE lpData,
                                 LPDWORD lpcbData) const override;
    virtual LONG RegQueryValueExW(HKEY hKey, LPCWSTR lpValueName,
                                  LPDWORD lpReserved, LPDWORD lpType,
                                  LPBYTE lpData,
                                  LPDWORD lpcbData) const override;
    virtual WINBOOL SetSecurityDescriptorDacl(
        PSECURITY_DESCRIPTOR pSecurityDescriptor, WINBOOL bDaclPresent,
        PACL pDacl, WINBOOL bDaclDefaulted) const override;
    virtual WINBOOL SetServiceStatus(
        SERVICE_STATUS_HANDLE hServiceStatus,
        LPSERVICE_STATUS lpServiceStatus) const override;
    virtual WINBOOL StartServiceCtrlDispatcher(
        const SERVICE_TABLE_ENTRY *lpServiceStartTable) const override;

    // WINBASEAPI:
    virtual WINBOOL AssignProcessToJobObject(HANDLE hJob,
                                             HANDLE hProcess) const override;
    virtual WINBOOL CloseHandle(HANDLE hObject) const override;
    virtual LONG CompareFileTime(const FILETIME *lpFileTime1,
                                 const FILETIME *lpFileTime2) const override;
    virtual WINBOOL CreateDirectory(
        LPCSTR lpPathName,
        LPSECURITY_ATTRIBUTES lpSecurityAttributes) const override;
    virtual WINBOOL CreateDirectoryA(
        LPCSTR lpPathName,
        LPSECURITY_ATTRIBUTES lpSecurityAttributes) const override;
    virtual HANDLE CreateEvent(LPSECURITY_ATTRIBUTES lpEventAttributes,
                               WINBOOL bManualReset, WINBOOL bInitialState,
                               LPCSTR lpName) const override;
    virtual HANDLE CreateFile(LPCSTR lpFileName, DWORD dwDesiredAccess,
                              DWORD dwShareMode,
                              LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                              DWORD dwCreationDisposition,
                              DWORD dwFlagsAndAttributes,
                              HANDLE hTemplateFile) const override;
    virtual HANDLE CreateJobObject(LPSECURITY_ATTRIBUTES lpJobAttributes,
                                   LPCSTR lpName) const override;
    virtual HANDLE CreateMutex(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                               WINBOOL bInitialOwner,
                               LPCSTR lpName) const override;
    virtual HANDLE CreateMutexA(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                                WINBOOL bInitialOwner,
                                LPCSTR lpName) const override;
    virtual WINBOOL CreatePipe(PHANDLE hReadPipe, PHANDLE hWritePipe,
                               LPSECURITY_ATTRIBUTES lpPipeAttributes,
                               DWORD nSize) const override;
    virtual WINBOOL CreateProcess(
        LPCSTR lpApplicationName, LPSTR lpCommandLine,
        LPSECURITY_ATTRIBUTES lpProcessAttributes,
        LPSECURITY_ATTRIBUTES lpThreadAttributes, WINBOOL bInheritHandles,
        DWORD dwCreationFlags, LPVOID lpEnvironment, LPCSTR lpCurrentDirectory,
        LPSTARTUPINFO lpStartupInfo,
        LPPROCESS_INFORMATION lpProcessInformation) const override;
    virtual HANDLE CreateThread(LPSECURITY_ATTRIBUTES lpThreadAttributes,
                                SIZE_T dwStackSize,
                                LPTHREAD_START_ROUTINE lpStartAddress,
                                LPVOID lpParameter, DWORD dwCreationFlags,
                                LPDWORD lpThreadId) const override;
    virtual WINBOOL DeleteFile(LPCSTR lpFileName) const override;
    virtual WINBOOL DuplicateHandle(HANDLE hSourceProcessHandle,
                                    HANDLE hSourceHandle,
                                    HANDLE hTargetProcessHandle,
                                    LPHANDLE lpTargetHandle,
                                    DWORD dwDesiredAccess,
                                    WINBOOL bInheritHandle,
                                    DWORD dwOptions) const override;
    virtual DWORD ExpandEnvironmentStringsW(LPCWSTR lpSrc, LPWSTR lpDst,
                                            DWORD nSize) const override;
    virtual WINBOOL FindClose(HANDLE hFindFile) const override;
    virtual HANDLE FindFirstFile(
        LPCSTR lpFileName, LPWIN32_FIND_DATA lpFindFileData) const override;
    virtual HANDLE FindFirstFileEx(LPCSTR lpFileName, int fInfoLevelId,
                                   LPVOID lpFindFileData, int fSearchOp,
                                   LPVOID lpSearchFilter,
                                   DWORD dwAdditionalFlags) const override;
    virtual HANDLE FindFirstVolumeMountPoint(
        LPCSTR lpszRootPathName, LPSTR lpszVolumeMountPoint,
        DWORD cchBufferLength) const override;
    virtual WINBOOL FindNextFile(
        HANDLE hFindFile, LPWIN32_FIND_DATAA lpFindFileData) const override;
    virtual WINBOOL FindNextVolumeMountPoint(
        HANDLE hFindVolumeMountPoint, LPSTR lpszVolumeMountPoint,
        DWORD cchBufferLength) const override;
    virtual WINBOOL FindVolumeMountPointClose(
        HANDLE hFindVolumeMountPoint) const override;
    virtual WINBOOL FlushFileBuffers(HANDLE hFile) const override;
    virtual DWORD FormatMessageA(DWORD dwFlags, LPCVOID lpSource,
                                 DWORD dwMessageId, DWORD dwLanguageId,
                                 LPSTR lpBuffer, DWORD nSize,
                                 va_list *Arguments) const override;
    virtual DWORD FormatMessageW(DWORD dwFlags, LPCVOID lpSource,
                                 DWORD dwMessageId, DWORD dwLanguageId,
                                 LPWSTR lpBuffer, DWORD nSize,
                                 va_list *Arguments) const override;
    virtual WINBOOL FreeLibrary(HMODULE hLibModule) const override;
    virtual HANDLE GetCurrentProcess(void) const override;
    virtual DWORD GetCurrentDirectoryA(DWORD nBufferLength,
                                       LPSTR lpBuffer) const override;
    virtual WINBOOL GetExitCodeProcess(HANDLE hProcess,
                                       LPDWORD lpExitCode) const override;
    virtual WINBOOL GetExitCodeThread(HANDLE hThread,
                                      LPDWORD lpExitCode) const override;
    virtual DWORD GetFileAttributes(LPCSTR lpFileName) const override;
    virtual WINBOOL GetFileInformationByHandle(
        HANDLE hFile,
        LPBY_HANDLE_FILE_INFORMATION lpFileInformation) const override;
    virtual WINBOOL GetDiskFreeSpaceEx(
        LPCSTR lpDirectoryName, PULARGE_INTEGER lpFreeBytesAvailableToCaller,
        PULARGE_INTEGER lpTotalNumberOfBytes,
        PULARGE_INTEGER lpTotalNumberOfFreeBytes) const override;
    virtual UINT GetDriveType(LPCSTR lpRootPathName) const override;
    virtual DWORD GetLastError(void) const override;
    virtual DWORD GetLogicalDriveStrings(DWORD nBufferLength,
                                         LPSTR lpBuffer) const override;
    virtual DWORD GetModuleFileName(HMODULE hModule, LPSTR lpFilename,
                                    DWORD nSize) const override;
    virtual FARPROC GetProcAddress(HMODULE hModule,
                                   LPCSTR lpProcName) const override;
    virtual HANDLE GetProcessHeap(void) const override;
    virtual WINBOOL GetProcessTimes(HANDLE hProcess, LPFILETIME lpCreationTime,
                                    LPFILETIME lpExitTime,
                                    LPFILETIME lpKernelTime,
                                    LPFILETIME lpUserTime) const override;
    virtual VOID GetStartupInfo(LPSTARTUPINFO lpStartupInfo) const override;
    virtual VOID GetSystemInfo(LPSYSTEM_INFO lpSystemInfo) const override;
    virtual VOID GetSystemTime(LPSYSTEMTIME lpSystemTime) const override;
    virtual WINBOOL GetVersionEx(
        LPOSVERSIONINFO lpVersionInformation) const override;
    virtual WINBOOL GetVolumeInformation(
        LPCSTR lpRootPathName, LPSTR lpVolumeNameBuffer, DWORD nVolumeNameSize,
        LPDWORD lpVolumeSerialNumber, LPDWORD lpMaximumComponentLength,
        LPDWORD lpFileSystemFlags, LPSTR lpFileSystemNameBuffer,
        DWORD nFileSystemNameSize) const override;
    virtual WINBOOL GlobalMemoryStatusEx(
        LPMEMORYSTATUSEX lpBuffer) const override;
    virtual LPVOID HeapAlloc(HANDLE hHeap, DWORD dwFlags,
                             SIZE_T dwBytes) const override;
    virtual WINBOOL HeapFree(HANDLE hHeap, DWORD dwFlags,
                             LPVOID lpMem) const override;
    virtual LPVOID HeapReAlloc(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem,
                               SIZE_T dwBytes) const override;
    virtual SIZE_T HeapSize(HANDLE hHeap, DWORD dwFlags,
                            LPCVOID lpMem) const override;
    virtual HMODULE LoadLibraryExW(LPCWSTR lpLibFileName, HANDLE hFile,
                                   DWORD dwFlags) const override;
    virtual HMODULE LoadLibraryW(LPCWSTR lpLibFileName) const override;
    virtual HLOCAL LocalAlloc(UINT uFlags, SIZE_T uBytes) const override;
    virtual HLOCAL LocalFree(HLOCAL hMem) const override;
    virtual int MultiByteToWideChar(UINT CodePage, DWORD dwFlags,
                                    LPCCH lpMultiByteStr, int cbMultiByte,
                                    LPWSTR lpWideCharStr,
                                    int cchWideChar) const override;
    virtual HANDLE OpenProcess(DWORD dwDesiredAccess, WINBOOL bInheritHandle,
                               DWORD dwProcessId) const override;
    virtual WINBOOL MoveFile(LPCSTR lpExistingFileName,
                             LPCSTR lpNewFileName) const override;
    virtual WINBOOL PeekNamedPipe(
        HANDLE hNamedPipe, LPVOID lpBuffer, DWORD nBufferSize,
        LPDWORD lpBytesRead, LPDWORD lpTotalBytesAvail,
        LPDWORD lpBytesLeftThisMessage) const override;
    virtual WINBOOL QueryPerformanceCounter(
        LARGE_INTEGER *lpPerformanceCount) const override;
    virtual WINBOOL QueryPerformanceFrequency(
        LARGE_INTEGER *lpFrequency) const override;
    virtual WINBOOL ReadFile(HANDLE hFile, LPVOID lpBuffer,
                             DWORD nNumberOfBytesToRead,
                             LPDWORD lpNumberOfBytesRead,
                             LPOVERLAPPED lpOverlapped) const override;
    virtual WINBOOL ReleaseMutex(HANDLE hMutex) const override;
    virtual WINBOOL ResetEvent(HANDLE hEvent) const override;
    virtual DWORD SearchPathA(LPCSTR lpPath, LPCSTR lpFileName,
                              LPCSTR lpExtension, DWORD nBufferLength,
                              LPSTR lpBuffer, LPSTR *lpFilePart) const override;
    virtual WINBOOL SetConsoleCtrlHandler(PHANDLER_ROUTINE HandlerRoutine,
                                          WINBOOL Add) const override;
    virtual WINBOOL SetEnvironmentVariable(LPCSTR lpName,
                                           LPCSTR lpValue) const override;
    virtual LPTOP_LEVEL_EXCEPTION_FILTER SetUnhandledExceptionFilter(
        LPTOP_LEVEL_EXCEPTION_FILTER lpTopLevelExceptionFilter) const override;
    virtual VOID Sleep(DWORD dwMilliseconds) const override;
    virtual WINBOOL SystemTimeToFileTime(const SYSTEMTIME *lpSystemTime,
                                         LPFILETIME lpFileTime) const override;
    virtual WINBOOL TerminateJobObject(HANDLE hJob,
                                       UINT uExitCode) const override;
    virtual WINBOOL TerminateProcess(HANDLE hProcess,
                                     UINT uExitCode) const override;
    virtual WINBOOL TerminateThread(HANDLE hThread,
                                    DWORD dwExitCode) const override;
    virtual DWORD WaitForMultipleObjects(DWORD nCount, const HANDLE *lpHandles,
                                         WINBOOL bWaitAll,
                                         DWORD dwMilliseconds) const override;
    virtual DWORD WaitForSingleObject(HANDLE hHandle,
                                      DWORD dwMilliseconds) const override;
    virtual WINBOOL WriteFile(HANDLE hFile, LPCVOID lpBuffer,
                              DWORD nNumberOfBytesToWrite,
                              LPDWORD lpNumberOfBytesWritten,
                              LPOVERLAPPED lpOverlapped) const override;

    // WINIMPM:
    virtual WINBOOL CryptAcquireContext(HCRYPTPROV *phProv, LPCSTR szContainer,
                                        LPCSTR szProvider, DWORD dwProvType,
                                        DWORD dwFlags) const override;
    virtual WINBOOL CryptCreateHash(HCRYPTPROV hProv, ALG_ID Algid,
                                    HCRYPTKEY hKey, DWORD dwFlags,
                                    HCRYPTHASH *phHash) const override;
    virtual WINBOOL CryptDecrypt(HCRYPTKEY hKey, HCRYPTHASH hHash,
                                 WINBOOL Final, DWORD dwFlags, BYTE *pbData,
                                 DWORD *pdwDataLen) const override;
    virtual WINBOOL CryptDestroyHash(HCRYPTHASH hHash) const override;
    virtual WINBOOL CryptDestroyKey(HCRYPTKEY hKey) const override;
    virtual WINBOOL CryptDuplicateHash(HCRYPTHASH hHash, DWORD *pdwReserved,
                                       DWORD dwFlags,
                                       HCRYPTHASH *phHash) const override;
    virtual WINBOOL CryptEncrypt(HCRYPTKEY hKey, HCRYPTHASH hHash,
                                 WINBOOL Final, DWORD dwFlags, BYTE *pbData,
                                 DWORD *pdwDataLen,
                                 DWORD dwBufLen) const override;
    virtual WINBOOL CryptExportKey(HCRYPTKEY hKey, HCRYPTKEY hExpKey,
                                   DWORD dwBlobType, DWORD dwFlags,
                                   BYTE *pbData,
                                   DWORD *pdwDataLen) const override;
    virtual WINBOOL CryptGenKey(HCRYPTPROV hProv, ALG_ID Algid, DWORD dwFlags,
                                HCRYPTKEY *phKey) const override;
    virtual WINBOOL CryptGenRandom(HCRYPTPROV hProv, DWORD dwLen,
                                   BYTE *pbBuffer) const override;
    virtual WINBOOL CryptGetHashParam(HCRYPTHASH hHash, DWORD dwParam,
                                      BYTE *pbData, DWORD *pdwDataLen,
                                      DWORD dwFlags) const override;
    virtual WINBOOL CryptGetKeyParam(HCRYPTKEY hKey, DWORD dwParam,
                                     BYTE *pbData, DWORD *pdwDataLen,
                                     DWORD dwFlags) const override;
    virtual WINBOOL CryptHashData(HCRYPTHASH hHash, const BYTE *pbData,
                                  DWORD dwDataLen,
                                  DWORD dwFlags) const override;
    virtual WINBOOL CryptImportKey(HCRYPTPROV hProv, const BYTE *pbData,
                                   DWORD dwDataLen, HCRYPTKEY hPubKey,
                                   DWORD dwFlags,
                                   HCRYPTKEY *phKey) const override;
    virtual WINBOOL CryptReleaseContext(HCRYPTPROV hProv,
                                        DWORD dwFlags) const override;
    virtual WINBOOL CryptSetKeyParam(HCRYPTKEY hKey, DWORD dwParam,
                                     const BYTE *pbData,
                                     DWORD dwFlags) const override;

    // WINOLEAPI:
    virtual HRESULT CoCreateInstance(REFCLSID rclsid, LPUNKNOWN pUnkOuter,
                                     DWORD dwClsContext, const IID &riid,
                                     LPVOID *ppv) const override;
    virtual HRESULT CoInitializeEx(LPVOID pvReserved,
                                   DWORD dwCoInit) const override;
    virtual HRESULT CoInitializeSecurity(PSECURITY_DESCRIPTOR pSecDesc,
                                         LONG cAuthSvc,
                                         SOLE_AUTHENTICATION_SERVICE *asAuthSvc,
                                         void *pReserved1, DWORD dwAuthnLevel,
                                         DWORD dwImpLevel, void *pAuthList,
                                         DWORD dwCapabilities,
                                         void *pReserved3) const override;
    virtual HRESULT CoSetProxyBlanket(IUnknown *pProxy, DWORD dwAuthnSvc,
                                      DWORD dwAuthzSvc,
                                      OLECHAR *pServerPrincName,
                                      DWORD dwAuthnLevel, DWORD dwImpLevel,
                                      RPC_AUTH_IDENTITY_HANDLE pAuthInfo,
                                      DWORD dwCapabilities) const override;
    virtual void CoUninitialize(void) const override;

    // WINOLEAUTAPI:
    virtual HRESULT GetErrorInfo(ULONG dwReserved,
                                 IErrorInfo **pperrinfo) const override;
    virtual HRESULT SafeArrayDestroy(SAFEARRAY *psa) const override;
    virtual HRESULT SafeArrayGetElement(SAFEARRAY *psa, LONG *rgIndices,
                                        void *pv) const override;
    virtual HRESULT SafeArrayGetLBound(SAFEARRAY *psa, UINT nDim,
                                       LONG *plLbound) const override;
    virtual HRESULT SafeArrayGetUBound(SAFEARRAY *psa, UINT nDim,
                                       LONG *plUbound) const override;
    virtual BSTR SysAllocString(const OLECHAR *) const override;
    virtual void SysFreeString(BSTR) const override;
    virtual HRESULT VariantClear(VARIANTARG *pvarg) const override;

    // WSAAPI:
    virtual SOCKET accept(SOCKET s, struct sockaddr *addr,
                          int *addrlen) const override;
    virtual int bind(SOCKET s, const struct sockaddr *name,
                     int namelen) const override;
    virtual int closesocket(SOCKET s) const override;
    virtual int connect(SOCKET s, const struct sockaddr *name,
                        int namelen) const override;
    virtual int gethostname(char *name, int namelen) const override;
    virtual int getpeername(SOCKET s, struct sockaddr *name,
                            int *namelen) const override;
    virtual u_short htons(u_short hostshort) const override;
    virtual int listen(SOCKET s, int backlog) const override;
    virtual int select(int nfds, fd_set *readfds, fd_set *writefds,
                       fd_set *exceptfds,
                       const PTIMEVAL timeout) const override;
    virtual int send(SOCKET s, const char *buf, int len,
                     int flags) const override;
    virtual int setsockopt(SOCKET s, int level, int optname, const char *optval,
                           int optlen) const override;
    virtual SOCKET socket(int af, int type, int protocol) const override;
    virtual int WSACleanup(void) const override;
    virtual int WSAGetLastError(void) const override;
    virtual int WSAStartup(WORD wVersionRequested,
                           LPWSADATA lpWSAData) const override;

    // IMAGEAPI:
    virtual WINBOOL SymCleanup(HANDLE hProcess) const override;
#ifdef __x86_64
    virtual WINBOOL SymFromAddr(HANDLE hProcess, DWORD64 Address,
                                PDWORD64 Displacement,
                                PSYMBOL_INFO Symbol) const override;
#endif  // __x86_64
    virtual WINBOOL SymGetLineFromAddr64(
        HANDLE hProcess, DWORD64 qwAddr, PDWORD pdwDisplacement,
        PIMAGEHLP_LINE64 Line64) const override;
    virtual DWORD SymGetOptions(void) const override;
    virtual WINBOOL SymInitialize(HANDLE hProcess, PCSTR UserSearchPath,
                                  WINBOOL fInvadeProcess) const override;
    virtual DWORD SymSetOptions(DWORD SymOptions) const override;

// NTAPI:
#ifdef __x86_64
    virtual VOID RtlCaptureContext(PCONTEXT ContextRecord) const override;
    virtual PRUNTIME_FUNCTION RtlLookupFunctionEntry(
        DWORD64 ControlPc, PDWORD64 ImageBase,
        PUNWIND_HISTORY_TABLE HistoryTable) const override;
    virtual PEXCEPTION_ROUTINE RtlVirtualUnwind(
        DWORD HandlerType, DWORD64 ImageBase, DWORD64 ControlPc,
        PRUNTIME_FUNCTION FunctionEntry, PCONTEXT ContextRecord,
        PVOID *HandlerData, PDWORD64 EstablisherFrame,
        PKNONVOLATILE_CONTEXT_POINTERS ContextPointers) const override;
#endif  // __x86_64

    // MISC:
    virtual LPWSTR *CommandLineToArgvW(LPCWSTR lpCmdLine,
                                       int *pNumArgs) const override;
    virtual HANDLE CreateToolhelp32Snapshot(DWORD dwFlags,
                                            DWORD th32ProcessID) const override;
    virtual WINBOOL PathIsRelative(LPCSTR pszPath) const override;
    virtual WINBOOL Process32First(HANDLE hSnapshot,
                                   LPPROCESSENTRY32 lppe) const override;
    virtual WINBOOL Process32Next(HANDLE hSnapshot,
                                  LPPROCESSENTRY32 lppe) const override;
};

#endif  // WinApi_h
