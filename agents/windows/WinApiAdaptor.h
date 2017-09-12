#ifndef WinApiAdaptor_h
#define WinApiAdaptor_h

#include <winsock2.h>
#include <dbghelp.h>
#include <minwindef.h>
#include <pdh.h>
#include <shlwapi.h>
#include <tlhelp32.h>
#include <windows.h>
#include <winnt.h>
#include <winsvc.h>
#include <cstdarg>
#include <cstddef>
#include <cstring>

#undef CreateDirectory
#undef CreateFile
#undef CreateEvent
#undef CreateJobObject
#undef CreateMutex
#undef CreateService
#undef CryptAcquireContext
#undef DeleteFile
#undef FindFirstFile
#undef FindFirstFileEx
#undef FindFirstVolumeMountPoint
#undef FindNextFile
#undef FindNextVolumeMountPoint
#undef GetDiskFreeSpaceEx
#undef GetDriveType
#undef GetLogicalDriveStrings
#undef GetModuleFileName
#undef GetStartupInfo
#undef GetVersionEx
#undef GetVolumeInformation
#undef MoveFile
#undef OpenSCManager
#undef OpenService
#undef PdhOpenQuery
#undef QueryServiceConfig
#undef RegEnumKeyEx
#undef RegisterServiceCtrlHandler
#undef RegOpenKeyEx
#undef RtlZeroMemory
#undef SetEnvironmentVariable
#undef StartServiceCtrlDispatcher
#undef SymFromAddr
#undef ZeroMemory

class WinApiAdaptor {
public:
    WinApiAdaptor() = default;
    virtual ~WinApiAdaptor() = default;
    WinApiAdaptor(const WinApiAdaptor &) = delete;
    WinApiAdaptor &operator=(const WinApiAdaptor &) = delete;

    // WINADVAPI:
    virtual WINBOOL CloseEventLog(HANDLE hEventLog) const = 0;
    virtual WINBOOL CloseServiceHandle(SC_HANDLE hSCObject) const = 0;
    virtual WINBOOL ControlService(SC_HANDLE hService, DWORD dwControl,
                                   LPSERVICE_STATUS lpServiceStatus) const = 0;
    virtual SC_HANDLE CreateService(
        SC_HANDLE hSCManager, LPCSTR lpServiceName, LPCSTR lpDisplayName,
        DWORD dwDesiredAccess, DWORD dwServiceType, DWORD dwStartType,
        DWORD dwErrorControl,
        LPCSTR
            lpBinaryPathName /* ,LPCSTR lpLoadOrderGroup,LPDWORD lpdwTagId,LPCSTR lpDependencies,LPCSTR lpServiceStartName,LPCSTR lpPassword */)
        const = 0;  // last 5 params are always 0!
    virtual WINBOOL DeleteService(SC_HANDLE hService) const = 0;
    virtual WINBOOL EnumServicesStatusExW(
        SC_HANDLE hSCManager, SC_ENUM_TYPE InfoLevel, DWORD dwServiceType,
        DWORD dwServiceState, LPBYTE lpServices, DWORD cbBufSize,
        LPDWORD pcbBytesNeeded, LPDWORD lpServicesReturned,
        LPDWORD lpResumeHandle, LPCWSTR pszGroupName) const = 0;
    virtual WINBOOL GetNumberOfEventLogRecords(
        HANDLE hEventLog, PDWORD NumberOfRecords) const = 0;
    virtual WINBOOL GetOldestEventLogRecord(HANDLE hEventLog,
                                            PDWORD OldestRecord) const = 0;
    virtual WINBOOL GetTokenInformation(
        HANDLE TokenHandle, TOKEN_INFORMATION_CLASS TokenInformationClass,
        LPVOID TokenInformation, DWORD TokenInformationLength,
        PDWORD ReturnLength) const = 0;
    virtual WINBOOL InitializeSecurityDescriptor(
        PSECURITY_DESCRIPTOR pSecurityDescriptor, DWORD dwRevision) const = 0;
    virtual WINBOOL LookupAccountSidW(LPCWSTR lpSystemName, PSID Sid,
                                      LPWSTR Name, LPDWORD cchName,
                                      LPWSTR ReferencedDomainName,
                                      LPDWORD cchReferencedDomainName,
                                      PSID_NAME_USE peUse) const = 0;
    virtual HANDLE OpenEventLogW(LPCWSTR lpUNCServerName,
                                 LPCWSTR lpSourceName) const = 0;
    virtual WINBOOL OpenProcessToken(HANDLE ProcessHandle, DWORD DesiredAccess,
                                     PHANDLE TokenHandle) const = 0;
    virtual SC_HANDLE OpenSCManager(LPCSTR lpMachineName, LPCSTR lpDatabaseName,
                                    DWORD dwDesiredAccess) const = 0;
    virtual SC_HANDLE OpenService(SC_HANDLE hSCManager, LPCSTR lpServiceName,
                                  DWORD dwDesiredAccess) const = 0;
    virtual SC_HANDLE OpenServiceW(SC_HANDLE hSCManager, LPCWSTR lpServiceName,
                                   DWORD dwDesiredAccess) const = 0;
    virtual WINBOOL QueryServiceConfig(SC_HANDLE hService,
                                       LPQUERY_SERVICE_CONFIGW lpServiceConfig,
                                       DWORD cbBufSize,
                                       LPDWORD pcbBytesNeeded) const = 0;
    virtual WINBOOL QueryServiceStatus(
        SC_HANDLE hService, LPSERVICE_STATUS lpServiceStatus) const = 0;
    virtual WINBOOL ReadEventLogW(HANDLE hEventLog, DWORD dwReadFlags,
                                  DWORD dwRecordOffset, LPVOID lpBuffer,
                                  DWORD nNumberOfBytesToRead,
                                  DWORD *pnBytesRead,
                                  DWORD *pnMinNumberOfBytesNeeded) const = 0;
    virtual LONG RegCloseKey(HKEY hKey) const = 0;
    virtual LONG RegEnumKeyEx(HKEY hKey, DWORD dwIndex, LPSTR lpName,
                              LPDWORD lpcchName, LPDWORD lpReserved,
                              LPSTR lpClass, LPDWORD lpcchClass,
                              PFILETIME lpftLastWriteTime) const = 0;
    virtual SERVICE_STATUS_HANDLE RegisterServiceCtrlHandler(
        LPCSTR lpServiceName, LPHANDLER_FUNCTION lpHandlerProc) const = 0;
    virtual LONG RegOpenKeyEx(HKEY hKey, LPCSTR lpSubKey, DWORD ulOptions,
                              REGSAM samDesired, PHKEY phkResult) const = 0;
    virtual LONG RegOpenKeyExW(HKEY hKey, LPCWSTR lpSubKey, DWORD ulOptions,
                               REGSAM samDesired, PHKEY phkResult) const = 0;
    virtual LONG RegQueryValueEx(HKEY hKey, LPCSTR lpValueName,
                                 LPDWORD lpReserved, LPDWORD lpType,
                                 LPBYTE lpData, LPDWORD lpcbData) const = 0;
    virtual LONG RegQueryValueExW(HKEY hKey, LPCWSTR lpValueName,
                                  LPDWORD lpReserved, LPDWORD lpType,
                                  LPBYTE lpData, LPDWORD lpcbData) const = 0;
    virtual WINBOOL SetSecurityDescriptorDacl(
        PSECURITY_DESCRIPTOR pSecurityDescriptor, WINBOOL bDaclPresent,
        PACL pDacl, WINBOOL bDaclDefaulted) const = 0;
    virtual WINBOOL SetServiceStatus(
        SERVICE_STATUS_HANDLE hServiceStatus,
        LPSERVICE_STATUS lpServiceStatus) const = 0;
    virtual WINBOOL StartServiceCtrlDispatcher(
        const SERVICE_TABLE_ENTRY *lpServiceStartTable) const = 0;

    // WINBASEAPI:
    virtual WINBOOL AssignProcessToJobObject(HANDLE hJob,
                                             HANDLE hProcess) const = 0;
    virtual WINBOOL CloseHandle(HANDLE hObject) const = 0;
    virtual LONG CompareFileTime(const FILETIME *lpFileTime1,
                                 const FILETIME *lpFileTime2) const = 0;
    virtual WINBOOL CreateDirectory(
        LPCSTR lpPathName,
        LPSECURITY_ATTRIBUTES lpSecurityAttributes) const = 0;
    virtual WINBOOL CreateDirectoryA(
        LPCSTR lpPathName,
        LPSECURITY_ATTRIBUTES lpSecurityAttributes) const = 0;
    virtual HANDLE CreateEvent(LPSECURITY_ATTRIBUTES lpEventAttributes,
                               WINBOOL bManualReset, WINBOOL bInitialState,
                               LPCSTR lpName) const = 0;
    virtual HANDLE CreateFile(LPCSTR lpFileName, DWORD dwDesiredAccess,
                              DWORD dwShareMode,
                              LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                              DWORD dwCreationDisposition,
                              DWORD dwFlagsAndAttributes,
                              HANDLE hTemplateFile) const = 0;
    virtual HANDLE CreateJobObject(LPSECURITY_ATTRIBUTES lpJobAttributes,
                                   LPCSTR lpName) const = 0;
    virtual HANDLE CreateMutex(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                               WINBOOL bInitialOwner, LPCSTR lpName) const = 0;
    virtual HANDLE CreateMutexA(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                                WINBOOL bInitialOwner, LPCSTR lpName) const = 0;
    virtual WINBOOL CreatePipe(PHANDLE hReadPipe, PHANDLE hWritePipe,
                               LPSECURITY_ATTRIBUTES lpPipeAttributes,
                               DWORD nSize) const = 0;
    virtual WINBOOL CreateProcess(
        LPCSTR lpApplicationName, LPSTR lpCommandLine,
        LPSECURITY_ATTRIBUTES lpProcessAttributes,
        LPSECURITY_ATTRIBUTES lpThreadAttributes, WINBOOL bInheritHandles,
        DWORD dwCreationFlags, LPVOID lpEnvironment, LPCSTR lpCurrentDirectory,
        LPSTARTUPINFO lpStartupInfo,
        LPPROCESS_INFORMATION lpProcessInformation) const = 0;
    virtual HANDLE CreateThread(LPSECURITY_ATTRIBUTES lpThreadAttributes,
                                SIZE_T dwStackSize,
                                LPTHREAD_START_ROUTINE lpStartAddress,
                                LPVOID lpParameter, DWORD dwCreationFlags,
                                LPDWORD lpThreadId) const = 0;
    virtual WINBOOL DeleteFile(LPCSTR lpFileName) const = 0;
    virtual WINBOOL DuplicateHandle(HANDLE hSourceProcessHandle,
                                    HANDLE hSourceHandle,
                                    HANDLE hTargetProcessHandle,
                                    LPHANDLE lpTargetHandle,
                                    DWORD dwDesiredAccess,
                                    WINBOOL bInheritHandle,
                                    DWORD dwOptions) const = 0;
    virtual DWORD ExpandEnvironmentStringsW(LPCWSTR lpSrc, LPWSTR lpDst,
                                            DWORD nSize) const = 0;
    virtual WINBOOL FindClose(HANDLE hFindFile) const = 0;
    virtual HANDLE FindFirstFile(LPCSTR lpFileName,
                                 LPWIN32_FIND_DATA lpFindFileData) const = 0;
    virtual HANDLE FindFirstFileEx(LPCSTR lpFileName, int fInfoLevelId,
                                   LPVOID lpFindFileData, int fSearchOp,
                                   LPVOID lpSearchFilter,
                                   DWORD dwAdditionalFlags) const = 0;
    virtual HANDLE FindFirstVolumeMountPoint(LPCSTR lpszRootPathName,
                                             LPSTR lpszVolumeMountPoint,
                                             DWORD cchBufferLength) const = 0;
    virtual WINBOOL FindNextFile(HANDLE hFindFile,
                                 LPWIN32_FIND_DATAA lpFindFileData) const = 0;
    virtual WINBOOL FindNextVolumeMountPoint(HANDLE hFindVolumeMountPoint,
                                             LPSTR lpszVolumeMountPoint,
                                             DWORD cchBufferLength) const = 0;
    virtual WINBOOL FindVolumeMountPointClose(
        HANDLE hFindVolumeMountPoint) const = 0;
    virtual WINBOOL FlushFileBuffers(HANDLE hFile) const = 0;
    virtual DWORD FormatMessageA(DWORD dwFlags, LPCVOID lpSource,
                                 DWORD dwMessageId, DWORD dwLanguageId,
                                 LPSTR lpBuffer, DWORD nSize,
                                 va_list *Arguments) const = 0;
    virtual DWORD FormatMessageW(DWORD dwFlags, LPCVOID lpSource,
                                 DWORD dwMessageId, DWORD dwLanguageId,
                                 LPWSTR lpBuffer, DWORD nSize,
                                 va_list *Arguments) const = 0;
    virtual WINBOOL FreeLibrary(HMODULE hLibModule) const = 0;
    virtual HANDLE GetCurrentProcess(void) const = 0;
    virtual DWORD GetCurrentDirectoryA(DWORD nBufferLength,
                                       LPSTR lpBuffer) const = 0;
    virtual WINBOOL GetExitCodeProcess(HANDLE hProcess,
                                       LPDWORD lpExitCode) const = 0;
    virtual WINBOOL GetExitCodeThread(HANDLE hThread,
                                      LPDWORD lpExitCode) const = 0;
    virtual DWORD GetFileAttributes(LPCSTR lpFileName) const = 0;
    virtual WINBOOL GetFileInformationByHandle(
        HANDLE hFile, LPBY_HANDLE_FILE_INFORMATION lpFileInformation) const = 0;
    virtual WINBOOL GetDiskFreeSpaceEx(
        LPCSTR lpDirectoryName, PULARGE_INTEGER lpFreeBytesAvailableToCaller,
        PULARGE_INTEGER lpTotalNumberOfBytes,
        PULARGE_INTEGER lpTotalNumberOfFreeBytes) const = 0;
    virtual UINT GetDriveType(LPCSTR lpRootPathName) const = 0;
    virtual DWORD GetLastError(void) const = 0;
    virtual DWORD GetLogicalDriveStrings(DWORD nBufferLength,
                                         LPSTR lpBuffer) const = 0;
    virtual DWORD GetModuleFileName(HMODULE hModule, LPSTR lpFilename,
                                    DWORD nSize) const = 0;
    virtual FARPROC GetProcAddress(HMODULE hModule,
                                   LPCSTR lpProcName) const = 0;
    virtual HANDLE GetProcessHeap(void) const = 0;
    virtual WINBOOL GetProcessTimes(HANDLE hProcess, LPFILETIME lpCreationTime,
                                    LPFILETIME lpExitTime,
                                    LPFILETIME lpKernelTime,
                                    LPFILETIME lpUserTime) const = 0;
    virtual VOID GetStartupInfo(LPSTARTUPINFO lpStartupInfo) const = 0;
    virtual VOID GetSystemInfo(LPSYSTEM_INFO lpSystemInfo) const = 0;
    virtual VOID GetSystemTime(LPSYSTEMTIME lpSystemTime) const = 0;
    virtual WINBOOL GetVersionEx(
        LPOSVERSIONINFO lpVersionInformation) const = 0;
    virtual WINBOOL GetVolumeInformation(
        LPCSTR lpRootPathName, LPSTR lpVolumeNameBuffer, DWORD nVolumeNameSize,
        LPDWORD lpVolumeSerialNumber, LPDWORD lpMaximumComponentLength,
        LPDWORD lpFileSystemFlags, LPSTR lpFileSystemNameBuffer,
        DWORD nFileSystemNameSize) const = 0;
    virtual WINBOOL GlobalMemoryStatusEx(LPMEMORYSTATUSEX lpBuffer) const = 0;
    virtual LPVOID HeapAlloc(HANDLE hHeap, DWORD dwFlags,
                             SIZE_T dwBytes) const = 0;
    virtual WINBOOL HeapFree(HANDLE hHeap, DWORD dwFlags,
                             LPVOID lpMem) const = 0;
    virtual LPVOID HeapReAlloc(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem,
                               SIZE_T dwBytes) const = 0;
    virtual SIZE_T HeapSize(HANDLE hHeap, DWORD dwFlags,
                            LPCVOID lpMem) const = 0;
    virtual HMODULE LoadLibraryExW(LPCWSTR lpLibFileName, HANDLE hFile,
                                   DWORD dwFlags) const = 0;
    virtual HMODULE LoadLibraryW(LPCWSTR lpLibFileName) const = 0;
    virtual HLOCAL LocalAlloc(UINT uFlags, SIZE_T uBytes) const = 0;
    virtual HLOCAL LocalFree(HLOCAL hMem) const = 0;
    virtual int MultiByteToWideChar(UINT CodePage, DWORD dwFlags,
                                    LPCCH lpMultiByteStr, int cbMultiByte,
                                    LPWSTR lpWideCharStr,
                                    int cchWideChar) const = 0;
    virtual HANDLE OpenProcess(DWORD dwDesiredAccess, WINBOOL bInheritHandle,
                               DWORD dwProcessId) const = 0;
    virtual WINBOOL MoveFile(LPCSTR lpExistingFileName,
                             LPCSTR lpNewFileName) const = 0;
    virtual WINBOOL PeekNamedPipe(HANDLE hNamedPipe, LPVOID lpBuffer,
                                  DWORD nBufferSize, LPDWORD lpBytesRead,
                                  LPDWORD lpTotalBytesAvail,
                                  LPDWORD lpBytesLeftThisMessage) const = 0;
    virtual WINBOOL QueryPerformanceCounter(
        LARGE_INTEGER *lpPerformanceCount) const = 0;
    virtual WINBOOL QueryPerformanceFrequency(
        LARGE_INTEGER *lpFrequency) const = 0;
    virtual WINBOOL ReadFile(HANDLE hFile, LPVOID lpBuffer,
                             DWORD nNumberOfBytesToRead,
                             LPDWORD lpNumberOfBytesRead,
                             LPOVERLAPPED lpOverlapped) const = 0;
    virtual WINBOOL ReleaseMutex(HANDLE hMutex) const = 0;
    virtual WINBOOL ResetEvent(HANDLE hEvent) const = 0;
    virtual DWORD SearchPathA(LPCSTR lpPath, LPCSTR lpFileName,
                              LPCSTR lpExtension, DWORD nBufferLength,
                              LPSTR lpBuffer, LPSTR *lpFilePart) const = 0;
    virtual WINBOOL SetConsoleCtrlHandler(PHANDLER_ROUTINE HandlerRoutine,
                                          WINBOOL Add) const = 0;
    virtual WINBOOL SetEnvironmentVariable(LPCSTR lpName,
                                           LPCSTR lpValue) const = 0;
    virtual LPTOP_LEVEL_EXCEPTION_FILTER SetUnhandledExceptionFilter(
        LPTOP_LEVEL_EXCEPTION_FILTER lpTopLevelExceptionFilter) const = 0;
    virtual VOID Sleep(DWORD dwMilliseconds) const = 0;
    virtual WINBOOL SystemTimeToFileTime(const SYSTEMTIME *lpSystemTime,
                                         LPFILETIME lpFileTime) const = 0;
    virtual WINBOOL TerminateJobObject(HANDLE hJob, UINT uExitCode) const = 0;
    virtual WINBOOL TerminateProcess(HANDLE hProcess, UINT uExitCode) const = 0;
    virtual WINBOOL TerminateThread(HANDLE hThread, DWORD dwExitCode) const = 0;
    virtual DWORD WaitForMultipleObjects(DWORD nCount, const HANDLE *lpHandles,
                                         WINBOOL bWaitAll,
                                         DWORD dwMilliseconds) const = 0;
    virtual DWORD WaitForSingleObject(HANDLE hHandle,
                                      DWORD dwMilliseconds) const = 0;
    virtual WINBOOL WriteFile(HANDLE hFile, LPCVOID lpBuffer,
                              DWORD nNumberOfBytesToWrite,
                              LPDWORD lpNumberOfBytesWritten,
                              LPOVERLAPPED lpOverlapped) const = 0;

    // WINIMPM:
    virtual WINBOOL CryptAcquireContext(HCRYPTPROV *phProv, LPCSTR szContainer,
                                        LPCSTR szProvider, DWORD dwProvType,
                                        DWORD dwFlags) const = 0;
    virtual WINBOOL CryptCreateHash(HCRYPTPROV hProv, ALG_ID Algid,
                                    HCRYPTKEY hKey, DWORD dwFlags,
                                    HCRYPTHASH *phHash) const = 0;
    virtual WINBOOL CryptDecrypt(HCRYPTKEY hKey, HCRYPTHASH hHash,
                                 WINBOOL Final, DWORD dwFlags, BYTE *pbData,
                                 DWORD *pdwDataLen) const = 0;
    virtual WINBOOL CryptDestroyHash(HCRYPTHASH hHash) const = 0;
    virtual WINBOOL CryptDestroyKey(HCRYPTKEY hKey) const = 0;
    virtual WINBOOL CryptDuplicateHash(HCRYPTHASH hHash, DWORD *pdwReserved,
                                       DWORD dwFlags,
                                       HCRYPTHASH *phHash) const = 0;
    virtual WINBOOL CryptEncrypt(HCRYPTKEY hKey, HCRYPTHASH hHash,
                                 WINBOOL Final, DWORD dwFlags, BYTE *pbData,
                                 DWORD *pdwDataLen, DWORD dwBufLen) const = 0;
    virtual WINBOOL CryptExportKey(HCRYPTKEY hKey, HCRYPTKEY hExpKey,
                                   DWORD dwBlobType, DWORD dwFlags,
                                   BYTE *pbData, DWORD *pdwDataLen) const = 0;
    virtual WINBOOL CryptGenKey(HCRYPTPROV hProv, ALG_ID Algid, DWORD dwFlags,
                                HCRYPTKEY *phKey) const = 0;
    virtual WINBOOL CryptGenRandom(HCRYPTPROV hProv, DWORD dwLen,
                                   BYTE *pbBuffer) const = 0;
    virtual WINBOOL CryptGetHashParam(HCRYPTHASH hHash, DWORD dwParam,
                                      BYTE *pbData, DWORD *pdwDataLen,
                                      DWORD dwFlags) const = 0;
    virtual WINBOOL CryptGetKeyParam(HCRYPTKEY hKey, DWORD dwParam,
                                     BYTE *pbData, DWORD *pdwDataLen,
                                     DWORD dwFlags) const = 0;
    virtual WINBOOL CryptHashData(HCRYPTHASH hHash, const BYTE *pbData,
                                  DWORD dwDataLen, DWORD dwFlags) const = 0;
    virtual WINBOOL CryptImportKey(HCRYPTPROV hProv, const BYTE *pbData,
                                   DWORD dwDataLen, HCRYPTKEY hPubKey,
                                   DWORD dwFlags, HCRYPTKEY *phKey) const = 0;
    virtual WINBOOL CryptReleaseContext(HCRYPTPROV hProv,
                                        DWORD dwFlags) const = 0;
    virtual WINBOOL CryptSetKeyParam(HCRYPTKEY hKey, DWORD dwParam,
                                     const BYTE *pbData,
                                     DWORD dwFlags) const = 0;

    // WINOLEAPI:
    virtual HRESULT CoCreateInstance(REFCLSID rclsid, LPUNKNOWN pUnkOuter,
                                     DWORD dwClsContext, const IID &riid,
                                     LPVOID *ppv) const = 0;
    virtual HRESULT CoInitializeEx(LPVOID pvReserved, DWORD dwCoInit) const = 0;
    virtual HRESULT CoInitializeSecurity(PSECURITY_DESCRIPTOR pSecDesc,
                                         LONG cAuthSvc,
                                         SOLE_AUTHENTICATION_SERVICE *asAuthSvc,
                                         void *pReserved1, DWORD dwAuthnLevel,
                                         DWORD dwImpLevel, void *pAuthList,
                                         DWORD dwCapabilities,
                                         void *pReserved3) const = 0;
    virtual HRESULT CoSetProxyBlanket(IUnknown *pProxy, DWORD dwAuthnSvc,
                                      DWORD dwAuthzSvc,
                                      OLECHAR *pServerPrincName,
                                      DWORD dwAuthnLevel, DWORD dwImpLevel,
                                      RPC_AUTH_IDENTITY_HANDLE pAuthInfo,
                                      DWORD dwCapabilities) const = 0;
    virtual void CoUninitialize(void) const = 0;

    // WINOLEAUTAPI:
    virtual HRESULT GetErrorInfo(ULONG dwReserved,
                                 IErrorInfo **pperrinfo) const = 0;
    virtual HRESULT SafeArrayDestroy(SAFEARRAY *psa) const = 0;
    virtual HRESULT SafeArrayGetElement(SAFEARRAY *psa, LONG *rgIndices,
                                        void *pv) const = 0;
    virtual HRESULT SafeArrayGetLBound(SAFEARRAY *psa, UINT nDim,
                                       LONG *plLbound) const = 0;
    virtual HRESULT SafeArrayGetUBound(SAFEARRAY *psa, UINT nDim,
                                       LONG *plUbound) const = 0;
    virtual BSTR SysAllocString(const OLECHAR *) const = 0;
    virtual void SysFreeString(BSTR) const = 0;
    virtual HRESULT VariantClear(VARIANTARG *pvarg) const = 0;

    // WSAAPI:
    virtual SOCKET accept(SOCKET s, struct sockaddr *addr,
                          int *addrlen) const = 0;
    virtual int bind(SOCKET s, const struct sockaddr *name,
                     int namelen) const = 0;
    virtual int closesocket(SOCKET s) const = 0;
    virtual int connect(SOCKET s, const struct sockaddr *name,
                        int namelen) const = 0;
    virtual int gethostname(char *name, int namelen) const = 0;
    virtual int getpeername(SOCKET s, struct sockaddr *name,
                            int *namelen) const = 0;
    virtual u_short htons(u_short hostshort) const = 0;
    virtual int listen(SOCKET s, int backlog) const = 0;
    virtual int select(int nfds, fd_set *readfds, fd_set *writefds,
                       fd_set *exceptfds, const PTIMEVAL timeout) const = 0;
    virtual int send(SOCKET s, const char *buf, int len, int flags) const = 0;
    virtual int setsockopt(SOCKET s, int level, int optname, const char *optval,
                           int optlen) const = 0;
    virtual SOCKET socket(int af, int type, int protocol) const = 0;
    virtual int WSACleanup(void) const = 0;
    virtual int WSAGetLastError(void) const = 0;
    virtual int WSAStartup(WORD wVersionRequested,
                           LPWSADATA lpWSAData) const = 0;

    // IMAGEAPI:
    virtual WINBOOL SymCleanup(HANDLE hProcess) const = 0;
#ifdef __x86_64
    virtual WINBOOL SymFromAddr(HANDLE hProcess, DWORD64 Address,
                                PDWORD64 Displacement,
                                PSYMBOL_INFO Symbol) const = 0;
#endif  // __x86_64
    virtual WINBOOL SymGetLineFromAddr64(HANDLE hProcess, DWORD64 qwAddr,
                                         PDWORD pdwDisplacement,
                                         PIMAGEHLP_LINE64 Line64) const = 0;
    virtual DWORD SymGetOptions(void) const = 0;
    virtual WINBOOL SymInitialize(HANDLE hProcess, PCSTR UserSearchPath,
                                  WINBOOL fInvadeProcess) const = 0;
    virtual DWORD SymSetOptions(DWORD SymOptions) const = 0;

// NTAPI:
#ifdef __x86_64
    virtual VOID RtlCaptureContext(PCONTEXT ContextRecord) const = 0;
    virtual PRUNTIME_FUNCTION RtlLookupFunctionEntry(
        DWORD64 ControlPc, PDWORD64 ImageBase,
        PUNWIND_HISTORY_TABLE HistoryTable) const = 0;
    virtual PEXCEPTION_ROUTINE RtlVirtualUnwind(
        DWORD HandlerType, DWORD64 ImageBase, DWORD64 ControlPc,
        PRUNTIME_FUNCTION FunctionEntry, PCONTEXT ContextRecord,
        PVOID *HandlerData, PDWORD64 EstablisherFrame,
        PKNONVOLATILE_CONTEXT_POINTERS ContextPointers) const = 0;
#endif  // __x86_64

    // MISC:
    virtual LPWSTR *CommandLineToArgvW(LPCWSTR lpCmdLine,
                                       int *pNumArgs) const = 0;
    virtual HANDLE CreateToolhelp32Snapshot(DWORD dwFlags,
                                            DWORD th32ProcessID) const = 0;
    virtual WINBOOL PathIsRelative(LPCSTR pszPath) const = 0;
    virtual WINBOOL Process32First(HANDLE hSnapshot,
                                   LPPROCESSENTRY32 lppe) const = 0;
    virtual WINBOOL Process32Next(HANDLE hSnapshot,
                                  LPPROCESSENTRY32 lppe) const = 0;
};

#endif  // WinApiAdaptor_h
