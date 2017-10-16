#include "WinApiAdaptor.h"
#include "gmock/gmock.h"

class MockWinApi : public WinApiAdaptor {
public:
    MockWinApi();
    virtual ~MockWinApi();
    MockWinApi(const MockWinApi &) = delete;
    MockWinApi &operator=(const MockWinApi &) = delete;

    // WINADVAPI:
    MOCK_CONST_METHOD1(CloseEventLog, WINBOOL(HANDLE hEventLog));
    MOCK_CONST_METHOD1(CloseServiceHandle, WINBOOL(SC_HANDLE hSCObject));
    MOCK_CONST_METHOD3(ControlService,
                       WINBOOL(SC_HANDLE hService, DWORD dwControl,
                               LPSERVICE_STATUS lpServiceStatus));
    MOCK_CONST_METHOD8(
        CreateService,
        SC_HANDLE(
            SC_HANDLE hSCManager, LPCSTR lpServiceName, LPCSTR lpDisplayName,
            DWORD dwDesiredAccess, DWORD dwServiceType, DWORD dwStartType,
            DWORD dwErrorControl,
            LPCSTR
                lpBinaryPathName /* ,LPCSTR lpLoadOrderGroup,LPDWORD lpdwTagId,LPCSTR lpDependencies,LPCSTR lpServiceStartName,LPCSTR lpPassword */));  // last 5 params are always 0!
    MOCK_CONST_METHOD1(DeleteService, WINBOOL(SC_HANDLE hService));
    MOCK_CONST_METHOD10(EnumServicesStatusExW,
                        WINBOOL(SC_HANDLE hSCManager, SC_ENUM_TYPE InfoLevel,
                                DWORD dwServiceType, DWORD dwServiceState,
                                LPBYTE lpServices, DWORD cbBufSize,
                                LPDWORD pcbBytesNeeded,
                                LPDWORD lpServicesReturned,
                                LPDWORD lpResumeHandle, LPCWSTR pszGroupName));
    MOCK_CONST_METHOD2(GetNumberOfEventLogRecords,
                       WINBOOL(HANDLE hEventLog, PDWORD NumberOfRecords));
    MOCK_CONST_METHOD2(GetOldestEventLogRecord,
                       WINBOOL(HANDLE hEventLog, PDWORD OldestRecord));
    MOCK_CONST_METHOD5(GetTokenInformation,
                       WINBOOL(HANDLE TokenHandle,
                               TOKEN_INFORMATION_CLASS TokenInformationClass,
                               LPVOID TokenInformation,
                               DWORD TokenInformationLength,
                               PDWORD ReturnLength));
    MOCK_CONST_METHOD2(InitializeSecurityDescriptor,
                       WINBOOL(PSECURITY_DESCRIPTOR pSecurityDescriptor,
                               DWORD dwRevision));
    MOCK_CONST_METHOD7(LookupAccountSidW,
                       WINBOOL(LPCWSTR lpSystemName, PSID Sid, LPWSTR Name,
                               LPDWORD cchName, LPWSTR ReferencedDomainName,
                               LPDWORD cchReferencedDomainName,
                               PSID_NAME_USE peUse));
    MOCK_CONST_METHOD2(OpenEventLogW,
                       HANDLE(LPCWSTR lpUNCServerName, LPCWSTR lpSourceName));
    MOCK_CONST_METHOD3(OpenProcessToken,
                       WINBOOL(HANDLE ProcessHandle, DWORD DesiredAccess,
                               PHANDLE TokenHandle));
    MOCK_CONST_METHOD3(OpenSCManager,
                       SC_HANDLE(LPCSTR lpMachineName, LPCSTR lpDatabaseName,
                                 DWORD dwDesiredAccess));
    MOCK_CONST_METHOD3(OpenService,
                       SC_HANDLE(SC_HANDLE hSCManager, LPCSTR lpServiceName,
                                 DWORD dwDesiredAccess));
    MOCK_CONST_METHOD3(OpenServiceW,
                       SC_HANDLE(SC_HANDLE hSCManager, LPCWSTR lpServiceName,
                                 DWORD dwDesiredAccess));
    MOCK_CONST_METHOD4(QueryServiceConfig,
                       WINBOOL(SC_HANDLE hService,
                               LPQUERY_SERVICE_CONFIGW lpServiceConfig,
                               DWORD cbBufSize, LPDWORD pcbBytesNeeded));
    MOCK_CONST_METHOD2(QueryServiceStatus,
                       WINBOOL(SC_HANDLE hService,
                               LPSERVICE_STATUS lpServiceStatus));
    MOCK_CONST_METHOD7(ReadEventLogW,
                       WINBOOL(HANDLE hEventLog, DWORD dwReadFlags,
                               DWORD dwRecordOffset, LPVOID lpBuffer,
                               DWORD nNumberOfBytesToRead, DWORD *pnBytesRead,
                               DWORD *pnMinNumberOfBytesNeeded));
    MOCK_CONST_METHOD1(RegCloseKey, LONG(HKEY hKey));
    MOCK_CONST_METHOD8(RegEnumKeyEx,
                       LONG(HKEY hKey, DWORD dwIndex, LPSTR lpName,
                            LPDWORD lpcchName, LPDWORD lpReserved,
                            LPSTR lpClass, LPDWORD lpcchClass,
                            PFILETIME lpftLastWriteTime));
    MOCK_CONST_METHOD2(RegisterServiceCtrlHandler,
                       SERVICE_STATUS_HANDLE(LPCSTR lpServiceName,
                                             LPHANDLER_FUNCTION lpHandlerProc));
    MOCK_CONST_METHOD5(RegOpenKeyEx,
                       LONG(HKEY hKey, LPCSTR lpSubKey, DWORD ulOptions,
                            REGSAM samDesired, PHKEY phkResult));
    MOCK_CONST_METHOD5(RegOpenKeyExW,
                       LONG(HKEY hKey, LPCWSTR lpSubKey, DWORD ulOptions,
                            REGSAM samDesired, PHKEY phkResult));
    MOCK_CONST_METHOD6(RegQueryValueEx,
                       LONG(HKEY hKey, LPCSTR lpValueName, LPDWORD lpReserved,
                            LPDWORD lpType, LPBYTE lpData, LPDWORD lpcbData));
    MOCK_CONST_METHOD6(RegQueryValueExW,
                       LONG(HKEY hKey, LPCWSTR lpValueName, LPDWORD lpReserved,
                            LPDWORD lpType, LPBYTE lpData, LPDWORD lpcbData));
    MOCK_CONST_METHOD4(SetSecurityDescriptorDacl,
                       WINBOOL(PSECURITY_DESCRIPTOR pSecurityDescriptor,
                               WINBOOL bDaclPresent, PACL pDacl,
                               WINBOOL bDaclDefaulted));
    MOCK_CONST_METHOD2(SetServiceStatus,
                       WINBOOL(SERVICE_STATUS_HANDLE hServiceStatus,
                               LPSERVICE_STATUS lpServiceStatus));
    MOCK_CONST_METHOD1(StartServiceCtrlDispatcher,
                       WINBOOL(const SERVICE_TABLE_ENTRY *lpServiceStartTable));

    // WINBASEAPI:
    MOCK_CONST_METHOD2(AssignProcessToJobObject,
                       WINBOOL(HANDLE hJob, HANDLE hProcess));
    MOCK_CONST_METHOD1(CloseHandle, WINBOOL(HANDLE hObject));
    MOCK_CONST_METHOD2(CompareFileTime, LONG(const FILETIME *lpFileTime1,
                                             const FILETIME *lpFileTime2));
    MOCK_CONST_METHOD2(CreateDirectory,
                       WINBOOL(LPCSTR lpPathName,
                               LPSECURITY_ATTRIBUTES lpSecurityAttributes));
    MOCK_CONST_METHOD2(CreateDirectoryA,
                       WINBOOL(LPCSTR lpPathName,
                               LPSECURITY_ATTRIBUTES lpSecurityAttributes));
    MOCK_CONST_METHOD4(CreateEvent,
                       HANDLE(LPSECURITY_ATTRIBUTES lpEventAttributes,
                              WINBOOL bManualReset, WINBOOL bInitialState,
                              LPCSTR lpName));
    MOCK_CONST_METHOD7(CreateFile,
                       HANDLE(LPCSTR lpFileName, DWORD dwDesiredAccess,
                              DWORD dwShareMode,
                              LPSECURITY_ATTRIBUTES lpSecurityAttributes,
                              DWORD dwCreationDisposition,
                              DWORD dwFlagsAndAttributes,
                              HANDLE hTemplateFile));
    MOCK_CONST_METHOD2(CreateJobObject,
                       HANDLE(LPSECURITY_ATTRIBUTES lpJobAttributes,
                              LPCSTR lpName));
    MOCK_CONST_METHOD3(CreateMutex,
                       HANDLE(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                              WINBOOL bInitialOwner, LPCSTR lpName));
    MOCK_CONST_METHOD3(CreateMutexA,
                       HANDLE(LPSECURITY_ATTRIBUTES lpMutexAttributes,
                              WINBOOL bInitialOwner, LPCSTR lpName));
    MOCK_CONST_METHOD4(CreatePipe,
                       WINBOOL(PHANDLE hReadPipe, PHANDLE hWritePipe,
                               LPSECURITY_ATTRIBUTES lpPipeAttributes,
                               DWORD nSize));
    MOCK_CONST_METHOD10(CreateProcess,
                        WINBOOL(LPCSTR lpApplicationName, LPSTR lpCommandLine,
                                LPSECURITY_ATTRIBUTES lpProcessAttributes,
                                LPSECURITY_ATTRIBUTES lpThreadAttributes,
                                WINBOOL bInheritHandles, DWORD dwCreationFlags,
                                LPVOID lpEnvironment, LPCSTR lpCurrentDirectory,
                                LPSTARTUPINFO lpStartupInfo,
                                LPPROCESS_INFORMATION lpProcessInformation));
    MOCK_CONST_METHOD6(CreateThread,
                       HANDLE(LPSECURITY_ATTRIBUTES lpThreadAttributes,
                              SIZE_T dwStackSize,
                              LPTHREAD_START_ROUTINE lpStartAddress,
                              LPVOID lpParameter, DWORD dwCreationFlags,
                              LPDWORD lpThreadId));
    MOCK_CONST_METHOD1(DeleteFile, WINBOOL(LPCSTR lpFileName));
    MOCK_CONST_METHOD7(DuplicateHandle,
                       WINBOOL(HANDLE hSourceProcessHandle,
                               HANDLE hSourceHandle,
                               HANDLE hTargetProcessHandle,
                               LPHANDLE lpTargetHandle, DWORD dwDesiredAccess,
                               WINBOOL bInheritHandle, DWORD dwOptions));
    MOCK_CONST_METHOD3(ExpandEnvironmentStringsW,
                       DWORD(LPCWSTR lpSrc, LPWSTR lpDst, DWORD nSize));
    MOCK_CONST_METHOD1(FindClose, WINBOOL(HANDLE hFindFile));
    MOCK_CONST_METHOD2(FindFirstFile, HANDLE(LPCSTR lpFileName,
                                             LPWIN32_FIND_DATA lpFindFileData));
    MOCK_CONST_METHOD6(FindFirstFileEx,
                       HANDLE(LPCSTR lpFileName, int fInfoLevelId,
                              LPVOID lpFindFileData, int fSearchOp,
                              LPVOID lpSearchFilter, DWORD dwAdditionalFlags));
    MOCK_CONST_METHOD3(FindFirstVolumeMountPoint,
                       HANDLE(LPCSTR lpszRootPathName,
                              LPSTR lpszVolumeMountPoint,
                              DWORD cchBufferLength));
    MOCK_CONST_METHOD2(FindNextFile,
                       WINBOOL(HANDLE hFindFile,
                               LPWIN32_FIND_DATAA lpFindFileData));
    MOCK_CONST_METHOD3(FindNextVolumeMountPoint,
                       WINBOOL(HANDLE hFindVolumeMountPoint,
                               LPSTR lpszVolumeMountPoint,
                               DWORD cchBufferLength));
    MOCK_CONST_METHOD1(FindVolumeMountPointClose,
                       WINBOOL(HANDLE hFindVolumeMountPoint));
    MOCK_CONST_METHOD1(FlushFileBuffers, WINBOOL(HANDLE hFile));
    MOCK_CONST_METHOD7(FormatMessageA,
                       DWORD(DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId,
                             DWORD dwLanguageId, LPSTR lpBuffer, DWORD nSize,
                             va_list *Arguments));
    MOCK_CONST_METHOD7(FormatMessageW,
                       DWORD(DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId,
                             DWORD dwLanguageId, LPWSTR lpBuffer, DWORD nSize,
                             va_list *Arguments));
    MOCK_CONST_METHOD1(FreeLibrary, WINBOOL(HMODULE hLibModule));
    MOCK_CONST_METHOD0(GetCurrentProcess, HANDLE(void));
    MOCK_CONST_METHOD2(GetCurrentDirectoryA,
                       DWORD(DWORD nBufferLength, LPSTR lpBuffer));
    MOCK_CONST_METHOD2(GetExitCodeProcess,
                       WINBOOL(HANDLE hProcess, LPDWORD lpExitCode));
    MOCK_CONST_METHOD2(GetExitCodeThread,
                       WINBOOL(HANDLE hThread, LPDWORD lpExitCode));
    MOCK_CONST_METHOD1(GetFileAttributes, DWORD(LPCSTR lpFileName));
    MOCK_CONST_METHOD2(GetFileInformationByHandle,
                       WINBOOL(HANDLE hFile,
                               LPBY_HANDLE_FILE_INFORMATION lpFileInformation));
    MOCK_CONST_METHOD4(GetDiskFreeSpaceEx,
                       WINBOOL(LPCSTR lpDirectoryName,
                               PULARGE_INTEGER lpFreeBytesAvailableToCaller,
                               PULARGE_INTEGER lpTotalNumberOfBytes,
                               PULARGE_INTEGER lpTotalNumberOfFreeBytes));
    MOCK_CONST_METHOD1(GetDriveType, UINT(LPCSTR lpRootPathName));
    MOCK_CONST_METHOD0(GetLastError, DWORD(void));
    MOCK_CONST_METHOD2(GetLogicalDriveStrings,
                       DWORD(DWORD nBufferLength, LPSTR lpBuffer));
    MOCK_CONST_METHOD3(GetModuleFileName,
                       DWORD(HMODULE hModule, LPSTR lpFilename, DWORD nSize));
    MOCK_CONST_METHOD2(GetProcAddress,
                       FARPROC(HMODULE hModule, LPCSTR lpProcName));
    MOCK_CONST_METHOD0(GetProcessHeap, HANDLE(void));
    MOCK_CONST_METHOD5(GetProcessTimes,
                       WINBOOL(HANDLE hProcess, LPFILETIME lpCreationTime,
                               LPFILETIME lpExitTime, LPFILETIME lpKernelTime,
                               LPFILETIME lpUserTime));
    MOCK_CONST_METHOD1(GetStartupInfo, VOID(LPSTARTUPINFO lpStartupInfo));
    MOCK_CONST_METHOD1(GetSystemInfo, VOID(LPSYSTEM_INFO lpSystemInfo));
    MOCK_CONST_METHOD1(GetSystemTime, VOID(LPSYSTEMTIME lpSystemTime));
    MOCK_CONST_METHOD1(GetVersionEx,
                       WINBOOL(LPOSVERSIONINFO lpVersionInformation));
    MOCK_CONST_METHOD8(
        GetVolumeInformation,
        WINBOOL(LPCSTR lpRootPathName, LPSTR lpVolumeNameBuffer,
                DWORD nVolumeNameSize, LPDWORD lpVolumeSerialNumber,
                LPDWORD lpMaximumComponentLength, LPDWORD lpFileSystemFlags,
                LPSTR lpFileSystemNameBuffer, DWORD nFileSystemNameSize));
    MOCK_CONST_METHOD1(GlobalMemoryStatusEx,
                       WINBOOL(LPMEMORYSTATUSEX lpBuffer));
    MOCK_CONST_METHOD3(HeapAlloc,
                       LPVOID(HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes));
    MOCK_CONST_METHOD3(HeapFree,
                       WINBOOL(HANDLE hHeap, DWORD dwFlags, LPVOID lpMem));
    MOCK_CONST_METHOD4(HeapReAlloc, LPVOID(HANDLE hHeap, DWORD dwFlags,
                                           LPVOID lpMem, SIZE_T dwBytes));
    MOCK_CONST_METHOD3(HeapSize,
                       SIZE_T(HANDLE hHeap, DWORD dwFlags, LPCVOID lpMem));
    MOCK_CONST_METHOD3(LoadLibraryExW, HMODULE(LPCWSTR lpLibFileName,
                                               HANDLE hFile, DWORD dwFlags));
    MOCK_CONST_METHOD1(LoadLibraryW, HMODULE(LPCWSTR lpLibFileName));
    MOCK_CONST_METHOD2(LocalAlloc, HLOCAL(UINT uFlags, SIZE_T uBytes));
    MOCK_CONST_METHOD1(LocalFree, HLOCAL(HLOCAL hMem));
    MOCK_CONST_METHOD6(MultiByteToWideChar,
                       int(UINT CodePage, DWORD dwFlags, LPCCH lpMultiByteStr,
                           int cbMultiByte, LPWSTR lpWideCharStr,
                           int cchWideChar));
    MOCK_CONST_METHOD3(OpenProcess,
                       HANDLE(DWORD dwDesiredAccess, WINBOOL bInheritHandle,
                              DWORD dwProcessId));
    MOCK_CONST_METHOD2(MoveFile, WINBOOL(LPCSTR lpExistingFileName,
                                         LPCSTR lpNewFileName));
    MOCK_CONST_METHOD6(PeekNamedPipe,
                       WINBOOL(HANDLE hNamedPipe, LPVOID lpBuffer,
                               DWORD nBufferSize, LPDWORD lpBytesRead,
                               LPDWORD lpTotalBytesAvail,
                               LPDWORD lpBytesLeftThisMessage));
    MOCK_CONST_METHOD1(QueryPerformanceCounter,
                       WINBOOL(LARGE_INTEGER *lpPerformanceCount));
    MOCK_CONST_METHOD1(QueryPerformanceFrequency,
                       WINBOOL(LARGE_INTEGER *lpFrequency));
    MOCK_CONST_METHOD5(ReadFile, WINBOOL(HANDLE hFile, LPVOID lpBuffer,
                                         DWORD nNumberOfBytesToRead,
                                         LPDWORD lpNumberOfBytesRead,
                                         LPOVERLAPPED lpOverlapped));
    MOCK_CONST_METHOD1(ReleaseMutex, WINBOOL(HANDLE hMutex));
    MOCK_CONST_METHOD1(ResetEvent, WINBOOL(HANDLE hEvent));
    MOCK_CONST_METHOD6(SearchPathA,
                       DWORD(LPCSTR lpPath, LPCSTR lpFileName,
                             LPCSTR lpExtension, DWORD nBufferLength,
                             LPSTR lpBuffer, LPSTR *lpFilePart));
    MOCK_CONST_METHOD2(SetConsoleCtrlHandler,
                       WINBOOL(PHANDLER_ROUTINE HandlerRoutine, WINBOOL Add));
    MOCK_CONST_METHOD2(SetEnvironmentVariable,
                       WINBOOL(LPCSTR lpName, LPCSTR lpValue));
    MOCK_CONST_METHOD1(
        SetUnhandledExceptionFilter,
        LPTOP_LEVEL_EXCEPTION_FILTER(
            LPTOP_LEVEL_EXCEPTION_FILTER lpTopLevelExceptionFilter));
    MOCK_CONST_METHOD1(Sleep, VOID(DWORD dwMilliseconds));
    MOCK_CONST_METHOD2(SystemTimeToFileTime,
                       WINBOOL(const SYSTEMTIME *lpSystemTime,
                               LPFILETIME lpFileTime));
    MOCK_CONST_METHOD2(TerminateJobObject,
                       WINBOOL(HANDLE hJob, UINT uExitCode));
    MOCK_CONST_METHOD2(TerminateProcess,
                       WINBOOL(HANDLE hProcess, UINT uExitCode));
    MOCK_CONST_METHOD2(TerminateThread,
                       WINBOOL(HANDLE hThread, DWORD dwExitCode));
    MOCK_CONST_METHOD4(WaitForMultipleObjects,
                       DWORD(DWORD nCount, const HANDLE *lpHandles,
                             WINBOOL bWaitAll, DWORD dwMilliseconds));
    MOCK_CONST_METHOD2(WaitForSingleObject,
                       DWORD(HANDLE hHandle, DWORD dwMilliseconds));
    MOCK_CONST_METHOD5(WriteFile, WINBOOL(HANDLE hFile, LPCVOID lpBuffer,
                                          DWORD nNumberOfBytesToWrite,
                                          LPDWORD lpNumberOfBytesWritten,
                                          LPOVERLAPPED lpOverlapped));

    // WINIMPM:
    MOCK_CONST_METHOD5(CryptAcquireContext,
                       WINBOOL(HCRYPTPROV *phProv, LPCSTR szContainer,
                               LPCSTR szProvider, DWORD dwProvType,
                               DWORD dwFlags));
    MOCK_CONST_METHOD5(CryptCreateHash,
                       WINBOOL(HCRYPTPROV hProv, ALG_ID Algid, HCRYPTKEY hKey,
                               DWORD dwFlags, HCRYPTHASH *phHash));
    MOCK_CONST_METHOD6(CryptDecrypt,
                       WINBOOL(HCRYPTKEY hKey, HCRYPTHASH hHash, WINBOOL Final,
                               DWORD dwFlags, BYTE *pbData, DWORD *pdwDataLen));
    MOCK_CONST_METHOD1(CryptDestroyHash, WINBOOL(HCRYPTHASH hHash));
    MOCK_CONST_METHOD1(CryptDestroyKey, WINBOOL(HCRYPTKEY hKey));
    MOCK_CONST_METHOD4(CryptDuplicateHash,
                       WINBOOL(HCRYPTHASH hHash, DWORD *pdwReserved,
                               DWORD dwFlags, HCRYPTHASH *phHash));
    MOCK_CONST_METHOD7(CryptEncrypt,
                       WINBOOL(HCRYPTKEY hKey, HCRYPTHASH hHash, WINBOOL Final,
                               DWORD dwFlags, BYTE *pbData, DWORD *pdwDataLen,
                               DWORD dwBufLen));
    MOCK_CONST_METHOD6(CryptExportKey,
                       WINBOOL(HCRYPTKEY hKey, HCRYPTKEY hExpKey,
                               DWORD dwBlobType, DWORD dwFlags, BYTE *pbData,
                               DWORD *pdwDataLen));
    MOCK_CONST_METHOD4(CryptGenKey, WINBOOL(HCRYPTPROV hProv, ALG_ID Algid,
                                            DWORD dwFlags, HCRYPTKEY *phKey));
    MOCK_CONST_METHOD3(CryptGenRandom,
                       WINBOOL(HCRYPTPROV hProv, DWORD dwLen, BYTE *pbBuffer));
    MOCK_CONST_METHOD5(CryptGetHashParam,
                       WINBOOL(HCRYPTHASH hHash, DWORD dwParam, BYTE *pbData,
                               DWORD *pdwDataLen, DWORD dwFlags));
    MOCK_CONST_METHOD5(CryptGetKeyParam,
                       WINBOOL(HCRYPTKEY hKey, DWORD dwParam, BYTE *pbData,
                               DWORD *pdwDataLen, DWORD dwFlags));
    MOCK_CONST_METHOD4(CryptHashData,
                       WINBOOL(HCRYPTHASH hHash, const BYTE *pbData,
                               DWORD dwDataLen, DWORD dwFlags));
    MOCK_CONST_METHOD6(CryptImportKey,
                       WINBOOL(HCRYPTPROV hProv, const BYTE *pbData,
                               DWORD dwDataLen, HCRYPTKEY hPubKey,
                               DWORD dwFlags, HCRYPTKEY *phKey));
    MOCK_CONST_METHOD2(CryptReleaseContext,
                       WINBOOL(HCRYPTPROV hProv, DWORD dwFlags));
    MOCK_CONST_METHOD4(CryptSetKeyParam,
                       WINBOOL(HCRYPTKEY hKey, DWORD dwParam,
                               const BYTE *pbData, DWORD dwFlags));

    // WINOLEAPI:
    MOCK_CONST_METHOD5(CoCreateInstance,
                       HRESULT(REFCLSID rclsid, LPUNKNOWN pUnkOuter,
                               DWORD dwClsContext, const IID &riid,
                               LPVOID *ppv));
    MOCK_CONST_METHOD2(CoInitializeEx,
                       HRESULT(LPVOID pvReserved, DWORD dwCoInit));
    MOCK_CONST_METHOD9(CoInitializeSecurity,
                       HRESULT(PSECURITY_DESCRIPTOR pSecDesc, LONG cAuthSvc,
                               SOLE_AUTHENTICATION_SERVICE *asAuthSvc,
                               void *pReserved1, DWORD dwAuthnLevel,
                               DWORD dwImpLevel, void *pAuthList,
                               DWORD dwCapabilities, void *pReserved3));
    MOCK_CONST_METHOD8(CoSetProxyBlanket,
                       HRESULT(IUnknown *pProxy, DWORD dwAuthnSvc,
                               DWORD dwAuthzSvc, OLECHAR *pServerPrincName,
                               DWORD dwAuthnLevel, DWORD dwImpLevel,
                               RPC_AUTH_IDENTITY_HANDLE pAuthInfo,
                               DWORD dwCapabilities));
    MOCK_CONST_METHOD0(CoUninitialize, void(void));

    // WINOLEAUTAPI:
    MOCK_CONST_METHOD2(GetErrorInfo,
                       HRESULT(ULONG dwReserved, IErrorInfo **pperrinfo));
    MOCK_CONST_METHOD1(SafeArrayDestroy, HRESULT(SAFEARRAY *psa));
    MOCK_CONST_METHOD3(SafeArrayGetElement,
                       HRESULT(SAFEARRAY *psa, LONG *rgIndices, void *pv));
    MOCK_CONST_METHOD3(SafeArrayGetLBound,
                       HRESULT(SAFEARRAY *psa, UINT nDim, LONG *plLbound));
    MOCK_CONST_METHOD3(SafeArrayGetUBound,
                       HRESULT(SAFEARRAY *psa, UINT nDim, LONG *plUbound));
    MOCK_CONST_METHOD1(SysAllocString, BSTR(const OLECHAR *));
    MOCK_CONST_METHOD1(SysFreeString, void(BSTR));
    MOCK_CONST_METHOD1(VariantClear, HRESULT(VARIANTARG *pvarg));

    // WSAAPI:
    MOCK_CONST_METHOD3(accept,
                       SOCKET(SOCKET s, struct sockaddr *addr, int *addrlen));
    MOCK_CONST_METHOD3(bind,
                       int(SOCKET s, const struct sockaddr *name, int namelen));
    MOCK_CONST_METHOD1(closesocket, int(SOCKET s));
    MOCK_CONST_METHOD3(connect,
                       int(SOCKET s, const struct sockaddr *name, int namelen));
    MOCK_CONST_METHOD2(gethostname, int(char *name, int namelen));
    MOCK_CONST_METHOD3(getpeername,
                       int(SOCKET s, struct sockaddr *name, int *namelen));
    MOCK_CONST_METHOD1(htons, u_short(u_short hostshort));
    MOCK_CONST_METHOD2(listen, int(SOCKET s, int backlog));
    MOCK_CONST_METHOD5(select, int(int nfds, fd_set *readfds, fd_set *writefds,
                                   fd_set *exceptfds, const PTIMEVAL timeout));
    MOCK_CONST_METHOD4(send,
                       int(SOCKET s, const char *buf, int len, int flags));
    MOCK_CONST_METHOD5(setsockopt, int(SOCKET s, int level, int optname,
                                       const char *optval, int optlen));
    MOCK_CONST_METHOD3(socket, SOCKET(int af, int type, int protocol));
    MOCK_CONST_METHOD0(WSACleanup, int(void));
    MOCK_CONST_METHOD0(WSAGetLastError, int(void));
    MOCK_CONST_METHOD2(WSAStartup,
                       int(WORD wVersionRequested, LPWSADATA lpWSAData));

    // IMAGEAPI:
    MOCK_CONST_METHOD1(SymCleanup, WINBOOL(HANDLE hProcess));
    MOCK_CONST_METHOD4(SymFromAddr,
                       WINBOOL(HANDLE hProcess, DWORD64 Address,
                               PDWORD64 Displacement, PSYMBOL_INFO Symbol));
    MOCK_CONST_METHOD4(SymGetLineFromAddr64,
                       WINBOOL(HANDLE hProcess, DWORD64 qwAddr,
                               PDWORD pdwDisplacement,
                               PIMAGEHLP_LINE64 Line64));
    MOCK_CONST_METHOD0(SymGetOptions, DWORD(void));
    MOCK_CONST_METHOD3(SymInitialize,
                       WINBOOL(HANDLE hProcess, PCSTR UserSearchPath,
                               WINBOOL fInvadeProcess));
    MOCK_CONST_METHOD1(SymSetOptions, DWORD(DWORD SymOptions));

    // NTAPI:
#ifdef __x86_64
    MOCK_CONST_METHOD1(RtlCaptureContext, VOID(PCONTEXT ContextRecord));
    MOCK_CONST_METHOD3(RtlLookupFunctionEntry,
                       PRUNTIME_FUNCTION(DWORD64 ControlPc, PDWORD64 ImageBase,
                                         PUNWIND_HISTORY_TABLE HistoryTable));
    MOCK_CONST_METHOD8(
        RtlVirtualUnwind,
        PEXCEPTION_ROUTINE(DWORD HandlerType, DWORD64 ImageBase,
                           DWORD64 ControlPc, PRUNTIME_FUNCTION FunctionEntry,
                           PCONTEXT ContextRecord, PVOID *HandlerData,
                           PDWORD64 EstablisherFrame,
                           PKNONVOLATILE_CONTEXT_POINTERS ContextPointers));
#endif  // __x86_64

    // MISC:
    MOCK_CONST_METHOD2(CommandLineToArgvW,
                       LPWSTR *(LPCWSTR lpCmdLine, int *pNumArgs));
    MOCK_CONST_METHOD2(CreateToolhelp32Snapshot,
                       HANDLE(DWORD dwFlags, DWORD th32ProcessID));
    MOCK_CONST_METHOD1(PathIsRelative, WINBOOL(LPCSTR pszPath));
    MOCK_CONST_METHOD2(Process32First,
                       WINBOOL(HANDLE hSnapshot, LPPROCESSENTRY32 lppe));
    MOCK_CONST_METHOD2(Process32Next,
                       WINBOOL(HANDLE hSnapshot, LPPROCESSENTRY32 lppe));
};
