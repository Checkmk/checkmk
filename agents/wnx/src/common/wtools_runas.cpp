// Windows extremely speccual Tools-RunAs
#include "stdafx.h"

#include "wtools_runas.h"

// windows
#include <ProfInfo.h>
#include <Sddl.h>
#include <UserEnv.h>
#include <WtsApi32.h>
#include <psapi.h>
#include <winsafer.h>
// end

#include <fmt/format.h>
#include <string.h>

#include "logger.h"
#include "tools/_misc.h"
#include "wtools.h"

#pragma comment(lib, "Wtsapi32.lib")
#pragma comment(lib, "Userenv.lib")
namespace wtools::runas {

static bool gbInService = false;

namespace krnl {
typedef BOOL(WINAPI* Wow64DisableWow64FsRedirectionProc)(PVOID* OldValue);
typedef BOOL(WINAPI* Wow64RevertWow64FsRedirectionProc)(PVOID OldValue);

static HMODULE G_Kernel32DllHandle = nullptr;
static Wow64DisableWow64FsRedirectionProc S_DisableFsRedirection = nullptr;
static Wow64RevertWow64FsRedirectionProc S_RevertFsRedirection = nullptr;
void* G_OldWow64RedirVal = nullptr;

void DisableFileRedirection() {
    if (nullptr == G_Kernel32DllHandle)
        G_Kernel32DllHandle = LoadLibraryW(L"Kernel32.dll");

    if ((nullptr != G_Kernel32DllHandle) &&
        ((nullptr == S_DisableFsRedirection) ||
         (nullptr == S_RevertFsRedirection))) {
        S_DisableFsRedirection =
            (Wow64DisableWow64FsRedirectionProc)GetProcAddress(
                G_Kernel32DllHandle, "Wow64DisableWow64FsRedirection");
        S_RevertFsRedirection =
            (Wow64RevertWow64FsRedirectionProc)GetProcAddress(
                G_Kernel32DllHandle, "Wow64RevertWow64FsRedirection");
    }

    if (nullptr != S_DisableFsRedirection) {
        auto b = S_DisableFsRedirection(&G_OldWow64RedirVal);
        if (b)
            XLOG::l.i("Disabled WOW64 file system redirection");
        else
            XLOG::l("Failed to disable WOW64 file system redirection {}",
                    ::GetLastError());
    } else
        XLOG::l.i("Failed to find Wow64DisableWow64FsRedirection API");
}

void RevertFileRedirection() {
    if (nullptr == G_Kernel32DllHandle)
        G_Kernel32DllHandle = LoadLibraryW(L"Kernel32.dll");

    if ((nullptr != G_Kernel32DllHandle) &&
        ((nullptr == S_DisableFsRedirection) ||
         (nullptr == S_RevertFsRedirection))) {
        S_DisableFsRedirection =
            (Wow64DisableWow64FsRedirectionProc)GetProcAddress(
                G_Kernel32DllHandle, "Wow64DisableWow64FsRedirection");
        S_RevertFsRedirection =
            (Wow64RevertWow64FsRedirectionProc)GetProcAddress(
                G_Kernel32DllHandle, "Wow64RevertWow64FsRedirection");
    }

    if (nullptr != S_RevertFsRedirection)
        S_RevertFsRedirection(G_OldWow64RedirVal);
}
}  // namespace krnl

inline bool IsBadHandle(HANDLE x) noexcept {
    return INVALID_HANDLE_VALUE == x || nullptr == x;
}

struct AppSettings {
public:
    bool use_system_account = false;
    bool dont_load_profile = true;  //  we do not load it speed up process
    HANDLE hUser = nullptr;
    HANDLE hStdErr = nullptr;
    HANDLE hStdIn = nullptr;
    HANDLE hStdOut = nullptr;
    std::wstring user;
    std::wstring password;
    std::wstring app;
    std::wstring app_args;
    std::wstring working_dir;
    bool show_window = false;

    // output
    HANDLE hProcess = nullptr;
    uint32_t pid = 0;

    // interactive
    bool interactive = false;
    bool show_ui_on_logon = false;
    uint32_t session_to_interact_with = 0xFFFFFFFF;

    // special
    bool run_elevated = false;
    bool run_limited = false;
    bool disable_file_redirection = false;
    std::vector<uint16_t> allowed_processors;
    int priority = NORMAL_PRIORITY_CLASS;
};

std::wstring MakePath(const AppSettings& settings) {
    auto path = fmt::format(L"{}", settings.app);
    if (!settings.app_args.empty()) {
        path += L" ";
        path += settings.app_args;
    }

    return path;
}

STARTUPINFO MakeStartupInfo(const AppSettings& settings) {
    STARTUPINFO si = {0};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = settings.show_window ? SW_SHOW : SW_HIDE;

    if (!IsBadHandle(settings.hStdErr)) {
        si.hStdError = settings.hStdErr;
        si.hStdInput = settings.hStdIn;
        si.hStdOutput = settings.hStdOut;
        si.dwFlags |= STARTF_USESTDHANDLES;
        XLOG::t("Using redirected handles");
    } else
        XLOG::t("Not using redirected IO");

    return si;
}

[[nodiscard]] bool DupeHandle(HANDLE& h) noexcept {
    HANDLE dupe = nullptr;
    if (::DuplicateTokenEx(h, MAXIMUM_ALLOWED, nullptr, SecurityImpersonation,
                           TokenPrimary, &dupe)) {
        ::CloseHandle(h);
        h = dupe;
        return true;
    }

    return false;
}

static void LogDupeError(std::string_view text) {
    auto gle = ::GetLastError();
    XLOG::l.bp("Error duplicating a user token '{}' - [{}]", gle);
}

HANDLE OpenCurrentProcessToken(DWORD DesiredAccess) {
    HANDLE hToken = nullptr;
    if (!::OpenProcessToken(::GetCurrentProcess(), DesiredAccess, &hToken)) {
        XLOG::l("Failed to open process to enable privilege  error is[{}]",
                ::GetLastError());
        return nullptr;
    }

    return hToken;
}

std::optional<LUID> GetLookupPrivilegeValue(const wchar_t* privilegs) {
    LUID luid;
    if (!::LookupPrivilegeValue(nullptr, privilegs, &luid)) {
        XLOG::l.bp("Could not find privilege  '{}' [{}]",
                   wtools::ConvertToUTF8(privilegs), ::GetLastError());
        return {};
    }

    return luid;
}

bool SetLookupPrivilege(HANDLE hToken, const LUID& luid) {
    TOKEN_PRIVILEGES tp;  // token privileges
    ZeroMemory(&tp, sizeof(tp));
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    // Adjust Token privileges
    if (AdjustTokenPrivileges(hToken, FALSE, &tp, sizeof(TOKEN_PRIVILEGES),
                              nullptr, nullptr))
        return true;

    XLOG::l.bp("Failed to adjust token for privilege [{}]", ::GetLastError());

    return false;
}

bool EnablePrivilege(LPCWSTR privileges, HANDLE hToken = nullptr) {
    bool close_token = false;

    if (!hToken) {
        hToken = OpenCurrentProcessToken(TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY);

        if (!hToken) return false;

        close_token = true;
    }
    ON_OUT_OF_SCOPE(if (close_token) CloseHandle(hToken));

    auto luid = GetLookupPrivilegeValue(privileges);
    if (!luid) return false;

    return SetLookupPrivilege(hToken, *luid);
}

using WTSGetActiveConsoleSessionIdProc = DWORD(WINAPI*)(void);

DWORD GetInteractiveSessionID() {
    // Get the active session ID.
    PWTS_SESSION_INFO session_info;
    DWORD count = 0;
    if (::WTSEnumerateSessions(WTS_CURRENT_SERVER_HANDLE, 0, 1, &session_info,
                               &count)) {
        ON_OUT_OF_SCOPE(::WTSFreeMemory(session_info))
        for (DWORD i = 0; i < count; i++) {
            if (session_info[i].State == WTSActive)  // Here is
                return session_info[i].SessionId;
        };
    }

    static WTSGetActiveConsoleSessionIdProc s_WTSGetActiveConsoleSessionId =
        nullptr;
    if (nullptr == s_WTSGetActiveConsoleSessionId) {
        auto hMod = ::LoadLibrary(L"Kernel32.dll");  // GLOK
        if (hMod) {
            s_WTSGetActiveConsoleSessionId =
                (WTSGetActiveConsoleSessionIdProc)GetProcAddress(
                    hMod, "WTSGetActiveConsoleSessionId");
        }
    }

    if (s_WTSGetActiveConsoleSessionId)           // not supported on Win2K
        return s_WTSGetActiveConsoleSessionId();  // we fall back on this if
                                                  // needed since it apparently
                                                  // doesn't always work

    XLOG::l("WTSGetActiveConsoleSessionId not supported on this OS");
    return 0;
}

struct CleanupInteractive {
    DWORD origSessionID = 0;
    HANDLE hUser = nullptr;
    bool bPreped = false;
};

BOOL PrepForInteractiveProcess(AppSettings& settings, CleanupInteractive* pCI,
                               DWORD session_id) {
    pCI->bPreped = true;
    // settings.hUser is set as the -u user, Local System (from -s) or as the
    // account the user originally launched Exec with

    // figure out which session we need to go into
    if (!DupeHandle(settings.hUser)) LogDupeError(XLOG_FLINE + " !!!");
    pCI->hUser = settings.hUser;

    auto targetSessionID = session_id;

    if ((DWORD)-1 == settings.session_to_interact_with) {
        targetSessionID = GetInteractiveSessionID();
        XLOG::l.i("Using SessionID {} (interactive session)", targetSessionID);
    } else
        XLOG::l.i("Using SessionID {} from params", targetSessionID);

    // if(FALSE == WTSQueryUserToken(targetSessionID, &settings.hUser))
    //	Log(L"Failed to get user from session ", ::GetLastError());

    // Duplicate(settings.hUser, __FILE__, __LINE__);

    DWORD len = 0;
    ::GetTokenInformation(settings.hUser, TokenSessionId, &pCI->origSessionID,
                          sizeof(pCI->origSessionID), &len);

    EnablePrivilege(SE_TCB_NAME, settings.hUser);

    if (FALSE == ::SetTokenInformation(settings.hUser, TokenSessionId,
                                       &targetSessionID,
                                       sizeof(targetSessionID)))
        XLOG::l("Failed to set interactive token [{}]", ::GetLastError());

    return TRUE;
}

CleanupInteractive MakeCleanupInteractive(AppSettings& settings,
                                          STARTUPINFO& si) {
    CleanupInteractive ci;
    if (settings.interactive || settings.show_ui_on_logon) {
        auto b = PrepForInteractiveProcess(settings, &ci,
                                           settings.session_to_interact_with);
        if (!b)
            XLOG::l("Failed to PrepForInteractiveProcess [{}]",
                    ::GetLastError());

        if (nullptr == si.lpDesktop)
            si.lpDesktop = (wchar_t*)L"WinSta0\\Default";

        if (settings.show_ui_on_logon)
            si.lpDesktop = (wchar_t*)L"winsta0\\Winlogon";

        // http://blogs.msdn.com/b/winsdk/archive/2009/07/14/launching-an-interactive-process-from-windows-service-in-windows-vista-and-later.aspx
        // indicates desktop names are case sensitive
    }

    return ci;
}

PROFILEINFOW MakeProfile(std::wstring_view user_name) {
    PROFILEINFO profile = {0};
    profile.dwSize = sizeof(profile);
    profile.lpUserName = (LPWSTR)(LPCWSTR)user_name.data();
    profile.dwFlags = PI_NOUI;
    return profile;
}

void* MakeEnvironment(HANDLE h) noexcept {
    void* environment = nullptr;
    auto ret = CreateEnvironmentBlock(&environment, h, TRUE);
    if (!ret)
        XLOG::l.bp(XLOG_FLINE + "create env block [{}]", ::GetLastError());

    return environment;
}

std::wstring GetTokenUserSID(HANDLE hToken) {
    DWORD tmp = 0;
    std::wstring userName;
    DWORD sidNameSize = 64;
    std::vector<WCHAR> sidName;
    sidName.resize(sidNameSize);

    DWORD sidDomainSize = 64;
    std::vector<WCHAR> sidDomain;
    sidDomain.resize(sidNameSize);

    DWORD userTokenSize = 1024;
    std::vector<WCHAR> tokenUserBuf;
    tokenUserBuf.resize(userTokenSize);

    TOKEN_USER* userToken = (TOKEN_USER*)&tokenUserBuf.front();

    if (GetTokenInformation(hToken, TokenUser, userToken, userTokenSize,
                            &tmp)) {
        WCHAR* pSidString = nullptr;
        if (ConvertSidToStringSidW(userToken->User.Sid, &pSidString))
            userName = pSidString;
        if (nullptr != pSidString) LocalFree(pSidString);
    } else
        _ASSERT(0);

    return userName;
}

HANDLE GetLocalSystemProcessToken() {
    DWORD pids[1024 * 10] = {0};
    DWORD cbNeeded = 0;
    DWORD cProcesses = 0;

    if (!::EnumProcesses(pids, sizeof(pids), &cbNeeded)) {
        XLOG::l("Can't enumProcesses - Failed to get token for Local System.");
        return nullptr;
    }

    // Calculate how many process identifiers were returned.
    cProcesses = cbNeeded / sizeof(DWORD);
    for (DWORD i = 0; i < cProcesses; ++i) {
        DWORD gle = 0;
        DWORD dwPid = pids[i];
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, dwPid);
        if (hProcess) {
            HANDLE hToken = 0;
            if (OpenProcessToken(hProcess,
                                 TOKEN_QUERY | TOKEN_READ | TOKEN_IMPERSONATE |
                                     TOKEN_QUERY_SOURCE | TOKEN_DUPLICATE |
                                     TOKEN_ASSIGN_PRIMARY | TOKEN_EXECUTE,
                                 &hToken)) {
                try {
                    auto name = GetTokenUserSID(hToken);

                    // const wchar_t arg[] = L"NT AUTHORITY\\";
                    // if(0 == _wcsnicmp(name, arg,
                    // sizeof(arg)/sizeof(arg[0])-1))

                    if (name == L"S-1-5-18")  // Well known SID for Local System
                    {
                        CloseHandle(hProcess);
                        return hToken;
                    }
                } catch (...) {
                    _ASSERT(0);
                }
            } else
                gle = ::GetLastError();
            CloseHandle(hToken);
        } else
            gle = ::GetLastError();
        CloseHandle(hProcess);
    }
    XLOG::l("Failed to get token for Local System.");
    return nullptr;
}

std::pair<std::wstring, std::wstring> GetDomainUser(
    const std::wstring& userIn) {
    // run as specified user
    if (nullptr != wcschr(userIn.c_str(), L'@'))
        return {L"", userIn};  // leave domain as nullptr

    auto tbl = cma::tools::SplitString(userIn, L"\\", 2);
    if (tbl.size() < 2) return {L".", userIn};
    return {tbl[0], tbl[1]};
}

void CleanUpInteractiveProcess(CleanupInteractive* pCI) noexcept {
    SetTokenInformation(pCI->hUser, TokenSessionId, &pCI->origSessionID,
                        sizeof(pCI->origSessionID));
}

// GTEST [-]
bool GetUserHandleSystemAccount(HANDLE& user_handle) {
    if (!IsBadHandle(user_handle))
        return true;  // we can have already ready handle

    EnablePrivilege(SE_DEBUG_NAME);  // OpenProcess
                                     // GetLocalSystemProcessToken
    user_handle = GetLocalSystemProcessToken();
    if (IsBadHandle(user_handle)) {
        XLOG::l("Not able to get Local System token");
        return false;
    } else
        XLOG::l.t("Got Local System handle");

    if (!DupeHandle(user_handle)) LogDupeError(XLOG_FLINE + " !!!");

    return true;  // ?????
}

bool GetUserHandleCurrentUser(HANDLE& user_handle, HANDLE hCmdPipe) {
    if (nullptr != hCmdPipe) {
        if (ImpersonateNamedPipeClient(hCmdPipe))
            XLOG::l("Impersonated caller");
        else
            XLOG::l("Failed to impersonate client user [{}]", ::GetLastError());
    }

    auto cur_thread_handle = ::GetCurrentThread();
    auto duplicated = ::DuplicateHandle(
        ::GetCurrentProcess(), cur_thread_handle, ::GetCurrentProcess(),
        &cur_thread_handle, 0, TRUE, DUPLICATE_SAME_ACCESS);
    auto opened = ::OpenThreadToken(
        cur_thread_handle, TOKEN_DUPLICATE | TOKEN_QUERY, TRUE, &user_handle);
    auto gle = ::GetLastError();
    if (1008 == gle)  // no thread token
    {
        opened = ::OpenProcessToken(
            GetCurrentProcess(), TOKEN_DUPLICATE | TOKEN_QUERY, &user_handle);
        gle = ::GetLastError();
    }

    if (!opened) XLOG::l("Failed to open current user token [{}]", gle);

    if (!DupeHandle(user_handle))
        LogDupeError(XLOG_FLINE + " !!!");  // gives max rights
    ::RevertToSelf();

    return !IsBadHandle(user_handle);
}

bool GetUserHandlePredefinedUser(HANDLE& user_handle,
                                 std::wstring_view user_name,
                                 std::wstring_view password) {
    auto [domain, user] = GetDomainUser(std::wstring(user_name));

    auto logged_in = LogonUser(
        user.data(), domain.empty() ? nullptr : domain.c_str(), password.data(),
        LOGON32_LOGON_INTERACTIVE, LOGON32_PROVIDER_WINNT50, &user_handle);
    XLOG::l.t("LogonUser {}", ::GetLastError());
    if ((FALSE == logged_in) || IsBadHandle(user_handle)) {
        XLOG::l("Error logging in as '{}' [{}]",
                wtools::ConvertToUTF8(user_name), ::GetLastError());
        return false;
    }

    if (!DupeHandle(user_handle)) LogDupeError(XLOG_FLINE + " !!!");

    return true;
}

bool LoadProfile(HANDLE user_handle, PROFILEINFO& profile) {
    EnablePrivilege(SE_RESTORE_NAME);
    EnablePrivilege(SE_BACKUP_NAME);
    auto profile_loaded = ::LoadUserProfile(user_handle, &profile);
    XLOG::t("LoadUserProfile [{}]", profile_loaded ? 0 : ::GetLastError());
    return profile_loaded;
}

bool GetUserHandle(AppSettings& settings, BOOL& profile_loaded,
                   PROFILEINFO& profile, HANDLE hCmdPipe) {
    if (settings.use_system_account) {
        return GetUserHandleSystemAccount(settings.hUser);
    }

    // not Local System, so either as specified user, or as current user
    if (!settings.user.empty()) {
        auto ret = GetUserHandlePredefinedUser(settings.hUser, settings.user,
                                               settings.password);
        if (!IsBadHandle(settings.hUser) && !settings.dont_load_profile)
            profile_loaded = LoadProfile(settings.hUser, profile);
        return true;
    }

    // run as current user
    return GetUserHandleCurrentUser(settings.hUser, hCmdPipe);
}

using SaferCreateLevelProc = BOOL(WINAPI*)(DWORD dwScopeId, DWORD dwLevelId,
                                           DWORD OpenFlags,
                                           SAFER_LEVEL_HANDLE* pLevelHandle,
                                           void* lpReserved);
using SaferComputeTokenFromLevelProc =
    BOOL(WINAPI*)(SAFER_LEVEL_HANDLE LevelHandle, HANDLE InAccessToken,
                  PHANDLE OutAccessToken, DWORD dwFlags, void* lpReserved);

using SaferCloseLevelProc = BOOL(WINAPI*)(SAFER_LEVEL_HANDLE hLevelHandle);

bool LimitRights(HANDLE& hUser) {
    DWORD gle = 0;

    static SaferCreateLevelProc s_SaferCreateLevel = nullptr;
    static SaferComputeTokenFromLevelProc s_SaferComputeTokenFromLevel =
        nullptr;
    static SaferCloseLevelProc s_SaferCloseLevel = nullptr;

    if ((nullptr == s_SaferCloseLevel) ||
        (nullptr == s_SaferComputeTokenFromLevel) ||
        (nullptr == s_SaferCreateLevel)) {
        HMODULE hMod = LoadLibrary(L"advapi32.dll");  // GLOK
        if (nullptr != hMod) {
            s_SaferCreateLevel =
                (SaferCreateLevelProc)GetProcAddress(hMod, "SaferCreateLevel");
            s_SaferComputeTokenFromLevel =
                (SaferComputeTokenFromLevelProc)GetProcAddress(
                    hMod, "SaferComputeTokenFromLevel");
            s_SaferCloseLevel =
                (SaferCloseLevelProc)GetProcAddress(hMod, "SaferCloseLevel");
        }
    }

    if ((nullptr == s_SaferCloseLevel) ||
        (nullptr == s_SaferComputeTokenFromLevel) ||
        (nullptr == s_SaferCreateLevel)) {
        XLOG::l(
            "Safer... calls not supported on this OS -- can't limit rights");
        return false;
    }

    if (!IsBadHandle(hUser)) {
        HANDLE hNew = nullptr;
        SAFER_LEVEL_HANDLE safer = nullptr;
        if (FALSE == s_SaferCreateLevel(SAFER_SCOPEID_USER,
                                        SAFER_LEVELID_NORMALUSER,
                                        SAFER_LEVEL_OPEN, &safer, nullptr)) {
            gle = ::GetLastError();
            XLOG::l("Failed to limit rights (SaferCreateLevel) [{}]", gle);
            return false;
        }

        if (nullptr != safer) {
            if (FALSE ==
                s_SaferComputeTokenFromLevel(safer, hUser, &hNew, 0, nullptr)) {
                gle = ::GetLastError();
                XLOG::l(
                    "Failed to limit rights (SaferComputeTokenFromLevel) {}.",
                    gle);
                auto ret = s_SaferCloseLevel(safer);
                if (!ret) XLOG::l.bp(XLOG_FLINE + " trash!");
                return false;
            }
            auto ret = s_SaferCloseLevel(safer);
            if (!ret) XLOG::l.bp(XLOG_FLINE + " trash!");
        }

        if (!IsBadHandle(hNew)) {
            auto ret = CloseHandle(hUser);
            if (!ret) XLOG::l.bp(XLOG_FLINE + " trash!");

            hUser = hNew;
            if (!DupeHandle(hUser)) LogDupeError(XLOG_FLINE + " !!!");

            return true;
        }
    }

    XLOG::l("Don't have a good user -- can't limit rights");
    return false;
}

bool ElevateUserToken(HANDLE& hEnvUser) {
    TOKEN_ELEVATION_TYPE tet;
    DWORD needed = 0;

    if (GetTokenInformation(hEnvUser, TokenElevationType, (void*)&tet,
                            sizeof(tet), &needed)) {
        if (tet != TokenElevationTypeLimited) return true;

        // get the associated token, which is the full-admin token
        TOKEN_LINKED_TOKEN tlt = {0};
        if (GetTokenInformation(hEnvUser, TokenLinkedToken, (void*)&tlt,
                                sizeof(tlt), &needed)) {
            if (!DupeHandle(tlt.LinkedToken)) LogDupeError(XLOG_FLINE + " !!!");
            hEnvUser = tlt.LinkedToken;
            return true;
        }

        auto gle = ::GetLastError();
        XLOG::l("Failed to get elevated token {}", gle);
        return false;
    }

    // can't tell if it's elevated or not -- continue anyway

    auto gle = ::GetLastError();
    switch (gle) {
        case ERROR_INVALID_PARAMETER:  // expected on 32-bit XP
        case ERROR_INVALID_FUNCTION:   // expected on 64-bit XP
            break;
        default:
            XLOG::l.w(
                "Can't query token to run elevated - continuing anyway [{}]",
                gle);
            break;
    }

    return true;
}

static void SetAffinityMask(HANDLE process,
                            const std::vector<uint16_t>& affinity) {
    if (affinity.empty()) return;

    DWORD_PTR system_mask = 0;
    DWORD_PTR process_mask = 0;
    auto ret = ::GetProcessAffinityMask(process, &process_mask, &system_mask);
    if (!ret) XLOG::l.bp(XLOG_FLINE + " hit1!");

    process_mask = 0;
    for (auto a : affinity) {
        DWORD bit = 1;
        bit = bit << (a - 1);
        process_mask |= bit & system_mask;
    }
    ret = ::SetProcessAffinityMask(process, process_mask);
    if (!ret) XLOG::l.bp(XLOG_FLINE + " hit2!");
}

bool StartProcess(AppSettings& settings, HANDLE command_pipe) {
    // Launching as one of:
    // 1. System Account
    // 2. Specified account (or limited account)
    // 3. As current process

    BOOL profile_loaded = FALSE;
    PROFILEINFO profile = MakeProfile(settings.user);

    if (false == GetUserHandle(settings, profile_loaded, profile, command_pipe))
        return false;

    PROCESS_INFORMATION pi = {0};
    auto si = MakeStartupInfo(settings);
    auto path = MakePath(settings);
    auto startingDir = settings.working_dir;

    CleanupInteractive ci = MakeCleanupInteractive(settings, si);

    XLOG::t("Exec using desktop {}", si.lpDesktop == nullptr
                                         ? "{default}"
                                         : wtools::ConvertToUTF8(si.lpDesktop));

    DWORD start_flags = CREATE_SUSPENDED;  //| CREATE_NEW_CONSOLE;

    auto environment = MakeEnvironment(settings.hUser);
    ON_OUT_OF_SCOPE(if (environment)::DestroyEnvironmentBlock(environment));

    if (nullptr != environment) start_flags |= CREATE_UNICODE_ENVIRONMENT;
    XLOG::l("CreateEnvironmentBlock [{}]", ::GetLastError());

    if (settings.disable_file_redirection) krnl::DisableFileRedirection();

    if (settings.run_limited && !LimitRights(settings.hUser)) return false;

    if (settings.run_elevated && !ElevateUserToken(settings.hUser))
        return false;

    auto [domain, user] = GetDomainUser(settings.user);

    XLOG::t("U:{} D:{} P:{} bP:{} Env:{} WD:{}", wtools::ConvertToUTF8(user),
            wtools::ConvertToUTF8(domain),
            wtools::ConvertToUTF8(settings.password),
            settings.dont_load_profile, environment ? "true" : "null",
            startingDir.empty() ? "null" : wtools::ConvertToUTF8(startingDir));

    BOOL bLaunched = FALSE;
    DWORD launch_gle = 0;

    if (settings.use_system_account) {
        XLOG::l.i("Exec starting process [{}] as Local System",
                  wtools::ConvertToUTF8(path));

        if (IsBadHandle(settings.hUser)) XLOG::l("Have bad user handle");

        EnablePrivilege(SE_IMPERSONATE_NAME);
        auto impersonated = ::ImpersonateLoggedOnUser(settings.hUser);
        if (!impersonated) {
            XLOG::l.bp("Failed to impersonate {}", ::GetLastError());
        }

        EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
        EnablePrivilege(SE_INCREASE_QUOTA_NAME);
        bLaunched = CreateProcessAsUser(
            settings.hUser, nullptr, path.data(), nullptr, nullptr, TRUE,
            start_flags, environment, startingDir.c_str(), &si, &pi);
        launch_gle = ::GetLastError();

        if (0 != launch_gle)
            XLOG::t(
                "Launch (launchGLE={}) params: user=[x{:X}] path=[{}] flags=[x{:X}], pEnv=[{}], dir=[{}], stdin=[x{:X}], stdout=[x{:X}], stderr=[x{:X}]",
                launch_gle, settings.hUser, wtools::ConvertToUTF8(path),
                start_flags, environment ? "{env}" : "{null}",
                startingDir.empty() ? "{null}" : ConvertToUTF8(startingDir),
                si.hStdInput, si.hStdOutput, si.hStdError);

        ::RevertToSelf();
    } else {
        if (FALSE == settings.user.empty())  // launching as a specific user
        {
            XLOG::l.t("Exec starting process [{}] as {}",
                      wtools::ConvertToUTF8(path),
                      wtools::ConvertToUTF8(settings.user));

            if (false == settings.run_limited) {
                bLaunched = CreateProcessWithLogonW(
                    user.c_str(), domain.empty() ? nullptr : domain.c_str(),
                    settings.password.c_str(),
                    settings.dont_load_profile ? 0 : LOGON_WITH_PROFILE,
                    nullptr, path.data(), start_flags, environment,
                    startingDir.empty() ? nullptr : startingDir.c_str(), &si,
                    &pi);
                launch_gle = ::GetLastError();

                if (0 != launch_gle) {
                    XLOG::t(
                        "Launch (launchGLE={:X}) params: user=[{}] "
                        "domain=[{}] "
                        "prof=[x{:X}] ",
                        launch_gle, wtools::ConvertToUTF8(user),
                        wtools::ConvertToUTF8(domain),
                        settings.dont_load_profile ? 0 : LOGON_WITH_PROFILE);
                    XLOG::t(
                        "path=[{}] flags=[x{:X}],"
                        " pEnv=[{}],"
                        " dir=[{}],"
                        " stdin=[x{:X}], stdout=[x{:X}], stderr=[x{:X}]",
                        wtools::ConvertToUTF8(path), start_flags,
                        environment ? "{env}" : "{null}",
                        startingDir.empty()
                            ? "{null}"
                            : wtools::ConvertToUTF8(startingDir),
                        si.hStdInput, si.hStdOutput, si.hStdError);
                }
            } else
                bLaunched = FALSE;  // force to run with CreateProcessAsUser so
                                    // rights can be limited

            // CreateProcessWithLogonW can't be called from LocalSystem on
            // Win2003 and earlier, so LogonUser/CreateProcessAsUser must be
            // used. Might as well try for everyone
            if (!bLaunched && !IsBadHandle(settings.hUser)) {
                XLOG::t(
                    "Failed CreateProcessWithLogonW - trying CreateProcessAsUser [{}]",
                    ::GetLastError());

                EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
                EnablePrivilege(SE_INCREASE_QUOTA_NAME);
                EnablePrivilege(SE_IMPERSONATE_NAME);
                auto impersonated = ImpersonateLoggedOnUser(settings.hUser);
                if (!impersonated)
                    XLOG::l.bp("Failed to impersonate [{}]", ::GetLastError());

                bLaunched = ::CreateProcessAsUserW(
                    settings.hUser, nullptr, path.data(), nullptr, nullptr,
                    TRUE,
                    CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
                        CREATE_NEW_CONSOLE,
                    environment, startingDir.c_str(), &si, &pi);
                if (0 == ::GetLastError())
                    launch_gle = 0;  // mark as successful, otherwise return our
                                     // original error
                if (0 != launch_gle)
                    XLOG::t(
                        "Launch (launchGLE={}) params: user=[x{:X}] path=[{}] pEnv=[{}], dir=[{}], stdin=[x{:X}], stdout=[x{:X}], stderr=[x{:X}]",
                        launch_gle, settings.hUser, wtools::ConvertToUTF8(path),
                        environment ? "{env}" : "{null}",
                        startingDir.empty()
                            ? "{null}"
                            : wtools::ConvertToUTF8(startingDir),
                        si.hStdInput, si.hStdOutput, si.hStdError);
                ::RevertToSelf();
            }
        } else {
            XLOG::l.t("Exec starting process [{}] as current user",
                      wtools::ConvertToUTF8(path));

            EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
            EnablePrivilege(SE_INCREASE_QUOTA_NAME);
            EnablePrivilege(SE_IMPERSONATE_NAME);

            if (nullptr != settings.hUser)
                bLaunched = ::CreateProcessAsUser(
                    settings.hUser, nullptr, path.data(), nullptr, nullptr,
                    TRUE, start_flags, environment, startingDir.c_str(), &si,
                    &pi);
            if (FALSE == bLaunched)
                bLaunched = CreateProcess(
                    nullptr, path.data(), nullptr, nullptr, TRUE, start_flags,
                    environment, startingDir.c_str(), &si, &pi);
            launch_gle = ::GetLastError();

            //#ifdef _DEBUG
            if (0 != launch_gle)
                XLOG::l.i(
                    "Launch (launchGLE={}) params: path=[{}] user=[{}], pEnv=[{}], dir=[{}], stdin=[{:X}], stdout=[{:X}], stderr=[{:X}]",
                    launch_gle, wtools::ConvertToUTF8(path),
                    settings.hUser ? "{non-null}" : "{null}",
                    environment ? "{env}" : "{null}",
                    startingDir.empty() ? "{null}"
                                        : wtools::ConvertToUTF8(startingDir),
                    si.hStdInput, si.hStdOutput, si.hStdError);
            //#endif
        }
    }

    if (bLaunched) {
        if (gbInService) XLOG::l.t("Successfully launched");

        settings.hProcess = pi.hProcess;
        settings.pid = pi.dwProcessId;

        SetAffinityMask(pi.hProcess, settings.allowed_processors);

        auto ret = SetPriorityClass(pi.hProcess, settings.priority);
        if (!ret) XLOG::l.bp(XLOG_FLINE + " error [{}]", ::GetLastError());
        ResumeThread(pi.hThread);
        ret = CloseHandle(pi.hThread);
        if (!ret) XLOG::l.bp(XLOG_FLINE + " error [{}]", ::GetLastError());

    } else {
        XLOG::l("Failed to start {} [{}]", wtools::ConvertToUTF8(path),
                launch_gle);
        if ((ERROR_ELEVATION_REQUIRED == launch_gle) && (false == gbInService))
            XLOG::l("HINT: Exec probably needs to be 'Run As Administrator'");
    }

    if (ci.bPreped) CleanUpInteractiveProcess(&ci);

    if (settings.disable_file_redirection) krnl::RevertFileRedirection();

    if (profile_loaded) UnloadUserProfile(settings.hUser, profile.hProfile);

    if (!IsBadHandle(settings.hUser)) {
        CloseHandle(settings.hUser);
        settings.hUser = nullptr;
    }

    return bLaunched ? true : false;
}

// Tree controlling command
// returns [ProcId, JobHandle, ProcessHandle]
std::tuple<DWORD, HANDLE, HANDLE> RunAsJob(
    std::wstring_view user_name,  // serg
    std::wstring_view password,   // my_pass
    std::wstring_view command,    // "c.bat"
    BOOL inherit_handles,         // not optimal, but default
    HANDLE stdio_handle,          // when we want to catch output
    HANDLE stderr_handle,         // same
    DWORD creation_flags,         // never checked this
    DWORD start_flags) noexcept {
    auto job_handle = CreateJobObjectA(nullptr, nullptr);

    if (!job_handle) return {0, nullptr, nullptr};

    AppSettings settings;
    settings.user = user_name;
    settings.password = password;
    settings.app = command;
    settings.dont_load_profile = true;
    settings.show_window = false;
    settings.hStdOut = stdio_handle;
    settings.hStdErr = stderr_handle;

    if (!StartProcess(settings, nullptr)) {
        CloseHandle(job_handle);

        return {0, nullptr, nullptr};
    }
    auto process_id = settings.pid;
    AssignProcessToJobObject(job_handle, settings.hProcess);
    return {process_id, job_handle, settings.hProcess};
}

}  // namespace wtools::runas
