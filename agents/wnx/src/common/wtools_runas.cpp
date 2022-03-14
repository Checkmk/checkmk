// Windows extremely speccual Tools-RunAs
#include "stdafx.h"

#include "wtools_runas.h"

// windows
#include <Sddl.h>
#include <UserEnv.h>
#include <WtsApi32.h>
#include <psapi.h>
#include <winsafer.h>

// end

#include "logger.h"
#include "tools/_misc.h"

#pragma comment(lib, "Wtsapi32.lib")
#pragma comment(lib, "Userenv.lib")
namespace wtools::runas {

static bool g_in_service = false;

namespace krnl {
using Wow64DisableWow64FsRedirectionProc = BOOL(WINAPI *)(PVOID *OldValue);
using Wow64RevertWow64FsRedirectionProc = BOOL(WINAPI *)(PVOID OldValue);

namespace {
HMODULE g_kernel32_dll_handle{nullptr};
Wow64DisableWow64FsRedirectionProc g_disable_fs_redirection{nullptr};
Wow64RevertWow64FsRedirectionProc g_revert_fs_redirection{nullptr};

void *g_old_wow64_redir_val{nullptr};

void FindWindowsProcs() {
    if (g_kernel32_dll_handle == nullptr)
        g_kernel32_dll_handle = LoadLibraryW(L"Kernel32.dll");

    if (g_kernel32_dll_handle == nullptr) {
        XLOG::l.crit("Can't load Kernel32.dll");
        return;
    }

    if (g_disable_fs_redirection == nullptr) {
        g_disable_fs_redirection =
            reinterpret_cast<Wow64DisableWow64FsRedirectionProc>(GetProcAddress(
                g_kernel32_dll_handle, "Wow64DisableWow64FsRedirection"));
    }

    if (g_revert_fs_redirection == nullptr) {
        g_revert_fs_redirection =
            reinterpret_cast<Wow64RevertWow64FsRedirectionProc>(GetProcAddress(
                g_kernel32_dll_handle, "Wow64RevertWow64FsRedirection"));
    }
}
}  // namespace

void DisableFileRedirection() {
    FindWindowsProcs();

    if (g_disable_fs_redirection == nullptr) {
        XLOG::l("Failed to find Wow64DisableWow64FsRedirection API");
        return;
    }

    auto b = g_disable_fs_redirection(&g_old_wow64_redir_val);
    if (b == TRUE)
        XLOG::d.i("Disabled WOW64 file system redirection");
    else
        XLOG::l("Failed to disable WOW64 file system redirection [{}]",
                ::GetLastError());
}

void RevertFileRedirection() {
    FindWindowsProcs();

    if (g_disable_fs_redirection == nullptr) {
        XLOG::l("Failed to find Wow64DisableWow64FsRedirection API");
        return;
    }

    g_revert_fs_redirection(g_old_wow64_redir_val);
}
}  // namespace krnl

struct AppSettings {
public:
    bool use_system_account{false};
    bool dont_load_profile{true};  //  we do not load it speed up process
    HANDLE hUser{nullptr};
    HANDLE hStdErr{nullptr};
    HANDLE hStdIn{nullptr};
    HANDLE hStdOut{nullptr};
    std::wstring user;
    std::wstring password;
    std::wstring app;
    std::wstring app_args;
    std::wstring working_dir;
    bool show_window{false};

    // output
    HANDLE hProcess{nullptr};
    uint32_t pid{0};

    // interactive
    bool interactive{false};
    bool show_ui_on_logon{false};
    uint32_t session_to_interact_with{0xFFFFFFFF};

    // special
    bool run_elevated{false};
    bool run_limited{false};
    bool disable_file_redirection{false};
    std::vector<uint16_t> allowed_processors;
    int priority{NORMAL_PRIORITY_CLASS};
};

std::wstring MakePath(const AppSettings &settings) {
    auto path = fmt::format(L"{}", settings.app);
    if (!settings.app_args.empty()) {
        path += L" ";
        path += settings.app_args;
    }

    return path;
}

STARTUPINFO MakeStartupInfo(const AppSettings &settings) {
    STARTUPINFO si = {0};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = settings.show_window ? SW_SHOW : SW_HIDE;

    if (!wtools::IsBadHandle(settings.hStdErr)) {
        si.hStdError = settings.hStdErr;
        si.hStdInput = settings.hStdIn;
        si.hStdOutput = settings.hStdOut;
        si.dwFlags |= STARTF_USESTDHANDLES;
        XLOG::t("Using redirected handles");
    } else
        XLOG::t("Not using redirected IO");

    return si;
}

[[nodiscard]] bool DupeHandle(HANDLE &h) noexcept {
    HANDLE dupe = nullptr;
    if (::DuplicateTokenEx(h, MAXIMUM_ALLOWED, nullptr, SecurityImpersonation,
                           TokenPrimary, &dupe) == TRUE) {
        ::CloseHandle(h);
        h = dupe;
        return true;
    }

    return false;
}

static void LogDupeError(std::string_view text) {
    XLOG::l("Error duplicating a user token '{}' - [{}]", text,
            ::GetLastError());
}

HANDLE OpenCurrentProcessToken(DWORD desired_access) {
    HANDLE token = nullptr;
    if (::OpenProcessToken(::GetCurrentProcess(), desired_access, &token) ==
        FALSE) {
        XLOG::l("Failed to open process to enable privilege  error is[{}]",
                ::GetLastError());
        return nullptr;
    }

    return token;
}

std::optional<LUID> GetLookupPrivilegeValue(const wchar_t *privilegs) {
    LUID luid;
    if (::LookupPrivilegeValue(nullptr, privilegs, &luid) == FALSE) {
        XLOG::l.bp("Could not find privilege  '{}' [{}]",
                   wtools::ToUtf8(privilegs), ::GetLastError());
        return {};
    }

    return luid;
}

bool SetLookupPrivilege(HANDLE token_handle, const LUID &luid) {
    TOKEN_PRIVILEGES tp;  // token privileges
    ZeroMemory(&tp, sizeof(tp));
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;

    // Adjust Token privileges
    if (::AdjustTokenPrivileges(token_handle, FALSE, &tp,
                                sizeof(TOKEN_PRIVILEGES), nullptr,
                                nullptr) == TRUE)
        return true;

    XLOG::l.bp("Failed to adjust token for privilege [{}]", ::GetLastError());

    return false;
}

bool EnablePrivilege(LPCWSTR privileges, HANDLE token) {
    bool close_token = false;

    if (token == nullptr) {
        token = OpenCurrentProcessToken(TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY);

        if (token == nullptr) return false;

        close_token = true;
    }
    ON_OUT_OF_SCOPE(if (close_token) CloseHandle(token));

    auto luid = GetLookupPrivilegeValue(privileges);
    if (!luid) return false;

    return SetLookupPrivilege(token, *luid);
}

bool EnablePrivilege(LPCWSTR privileges) {
    return EnablePrivilege(privileges, nullptr);
}

using WTSGetActiveConsoleSessionIdProc = DWORD(WINAPI *)(void);

DWORD GetInteractiveSessionID() {
    // Get the active session ID.
    PWTS_SESSION_INFO session_info;  // NOLINT
    DWORD count = 0;
    if (::WTSEnumerateSessions(WTS_CURRENT_SERVER_HANDLE, 0, 1, &session_info,
                               &count) == TRUE) {
        ON_OUT_OF_SCOPE(::WTSFreeMemory(session_info))

        for (DWORD i = 0; i < count; i++) {
            if (session_info[i].State == WTSActive)  // Here is
                return session_info[i].SessionId;
        };
    }

    static WTSGetActiveConsoleSessionIdProc
        s_wts_get_active_console_session_id = nullptr;
    if (nullptr == s_wts_get_active_console_session_id) {
        auto *module_handle = ::LoadLibrary(L"Kernel32.dll");  // GLOK
        if (module_handle != nullptr) {
            s_wts_get_active_console_session_id =
                reinterpret_cast<WTSGetActiveConsoleSessionIdProc>(
                    GetProcAddress(module_handle,
                                   "WTSGetActiveConsoleSessionId"));
        }
    }

    if (s_wts_get_active_console_session_id != nullptr)
        return s_wts_get_active_console_session_id();  // we fall back on this
                                                       // if needed since it
                                                       // apparently doesn't
                                                       // always work

    XLOG::l("WTSGetActiveConsoleSessionId not supported on this OS");
    return 0;
}

struct CleanupInteractive {
    DWORD origSessionID{0};
    HANDLE hUser{nullptr};
    bool bPreped{false};
};

BOOL PrepForInteractiveProcess(AppSettings &settings,
                               CleanupInteractive *cleanup_interactive,
                               DWORD session_id) {
    cleanup_interactive->bPreped = true;
    // settings.hUser is set as the -u user, Local System (from -s) or as the
    // account the user originally launched Exec with

    // figure out which session we need to go into
    if (!DupeHandle(settings.hUser)) LogDupeError(XLOG_FLINE + " !!!");
    cleanup_interactive->hUser = settings.hUser;

    auto target_session_id = session_id;

    if (0xFFFFFFFFU == settings.session_to_interact_with) {
        target_session_id = GetInteractiveSessionID();
        XLOG::d.i("Using SessionID {} (interactive session)",
                  target_session_id);
    } else
        XLOG::d.i("Using SessionID {} from params", target_session_id);

    // if(FALSE == WTSQueryUserToken(targetSessionID, &settings.hUser))
    //	Log(L"Failed to get user from session ", ::GetLastError());

    // Duplicate(settings.hUser, __FILE__, __LINE__);

    DWORD len = 0;
    ::GetTokenInformation(settings.hUser, TokenSessionId,
                          &cleanup_interactive->origSessionID,
                          sizeof(cleanup_interactive->origSessionID), &len);

    EnablePrivilege(SE_TCB_NAME, settings.hUser);

    if (FALSE == ::SetTokenInformation(settings.hUser, TokenSessionId,
                                       &target_session_id,
                                       sizeof(target_session_id)))
        XLOG::l("Failed to set interactive token [{}]", ::GetLastError());

    return TRUE;
}

CleanupInteractive MakeCleanupInteractive(AppSettings &settings,
                                          STARTUPINFO &si) {
    CleanupInteractive ci;
    if (settings.interactive || settings.show_ui_on_logon) {
        auto b = PrepForInteractiveProcess(settings, &ci,
                                           settings.session_to_interact_with);
        if (b == FALSE)
            XLOG::l("Failed to PrepForInteractiveProcess [{}]",
                    ::GetLastError());

        if (nullptr == si.lpDesktop)
            si.lpDesktop = const_cast<wchar_t *>(L"WinSta0\\Default");

        if (settings.show_ui_on_logon)
            si.lpDesktop = const_cast<wchar_t *>(L"winsta0\\Winlogon");

        // http://blogs.msdn.com/b/winsdk/archive/2009/07/14/launching-an-interactive-process-from-windows-service-in-windows-vista-and-later.aspx
        // indicates desktop names are case sensitive
    }

    return ci;
}

PROFILEINFOW MakeProfile(std::wstring_view user_name) {
    PROFILEINFO profile = {0};
    profile.dwSize = sizeof(profile);
    profile.lpUserName = const_cast<wchar_t *>(user_name.data());
    profile.dwFlags = PI_NOUI;
    return profile;
}

void *MakeEnvironment(HANDLE h) {
    void *environment = nullptr;
    auto ret = ::CreateEnvironmentBlock(&environment, h, TRUE);
    if (ret == FALSE)
        XLOG::l.bp(XLOG_FLINE + "create env block [{}]", ::GetLastError());

    return environment;
}

std::wstring GetTokenUserSID(HANDLE token_handle) {
    DWORD tmp = 0;
    std::wstring user_name;
    constexpr DWORD sid_name_size = 64;
    std::vector<WCHAR> sid_name;
    sid_name.resize(sid_name_size);

    constexpr DWORD sid_domain_size = 64;
    std::vector<WCHAR> sid_domain;
    sid_domain.resize(sid_domain_size);

    constexpr DWORD user_token_size = 1024;
    std::vector<WCHAR> token_user_buf;
    token_user_buf.resize(user_token_size);

    auto *user_token = reinterpret_cast<TOKEN_USER *>(&token_user_buf.front());

    if (::GetTokenInformation(token_handle, TokenUser, user_token,
                              user_token_size, &tmp) == TRUE) {
        WCHAR *sid_string = nullptr;
        if (::ConvertSidToStringSidW(user_token->User.Sid, &sid_string) == TRUE)
            user_name = sid_string;
        if (nullptr != sid_string) LocalFree(sid_string);
    } else
        _ASSERT(0);

    return user_name;
}

HANDLE GetLocalSystemProcessToken() {
    DWORD pids[1024 * 10] = {0};
    DWORD byte_count = 0;
    DWORD process_count = 0;

    if (::EnumProcesses(pids, sizeof(pids), &byte_count) == TRUE) {
        XLOG::l("Can't enumProcesses - Failed to get token for Local System.");
        return nullptr;
    }

    // Calculate how many process identifiers were returned.
    process_count = byte_count / sizeof(DWORD);
    for (DWORD i = 0; i < process_count; ++i) {
        DWORD pid = pids[i];
        HANDLE proc_handle = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid);
        if (proc_handle == nullptr) {
            continue;
        }

        HANDLE token_handle = nullptr;
        if (::OpenProcessToken(proc_handle,
                               TOKEN_QUERY | TOKEN_READ | TOKEN_IMPERSONATE |
                                   TOKEN_QUERY_SOURCE | TOKEN_DUPLICATE |
                                   TOKEN_ASSIGN_PRIMARY | TOKEN_EXECUTE,
                               &token_handle) == TRUE) {
            try {
                auto name = GetTokenUserSID(token_handle);

                // const wchar_t arg[] = L"NT AUTHORITY\\";
                // if(0 == _wcsnicmp(name, arg,
                // sizeof(arg)/sizeof(arg[0])-1))

                if (name == L"S-1-5-18")  // Well known SID for Local System
                {
                    CloseHandle(proc_handle);
                    return token_handle;
                }
            } catch (...) {
                _ASSERT(0);
            }
            CloseHandle(token_handle);
        }
        CloseHandle(proc_handle);
    }
    XLOG::l("Failed to get token for Local System.");
    return nullptr;
}

std::pair<std::wstring, std::wstring> GetDomainUser(
    const std::wstring &userIn) {
    // run as specified user
    if (nullptr != wcschr(userIn.c_str(), L'@'))
        return {L"", userIn};  // leave domain as nullptr

    auto tbl = cma::tools::SplitString(userIn, L"\\", 2);
    if (tbl.size() < 2) return {L".", userIn};
    return {tbl[0], tbl[1]};
}

void CleanUpInteractiveProcess(
    CleanupInteractive *cleanup_interactive) noexcept {
    SetTokenInformation(cleanup_interactive->hUser, TokenSessionId,
                        &cleanup_interactive->origSessionID,
                        sizeof(cleanup_interactive->origSessionID));
}

// GTEST [-]
bool GetUserHandleSystemAccount(HANDLE &user_handle) {
    if (!wtools::IsBadHandle(user_handle))
        return true;  // we can have already ready handle

    EnablePrivilege(SE_DEBUG_NAME);  // OpenProcess
                                     // GetLocalSystemProcessToken
    user_handle = GetLocalSystemProcessToken();
    if (wtools::IsBadHandle(user_handle)) {
        XLOG::l("Not able to get Local System token");
        return false;
    }
    XLOG::d.t("Got Local System handle");

    if (!DupeHandle(user_handle)) LogDupeError(XLOG_FLINE + " !!!");

    return true;  // ?????
}

bool GetUserHandleCurrentUser(HANDLE &user_handle, HANDLE pipe_handle) {
    if (pipe_handle != nullptr) {
        if (::ImpersonateNamedPipeClient(pipe_handle) == TRUE)
            XLOG::l("Impersonated caller");
        else
            XLOG::l("Failed to impersonate client user [{}]", ::GetLastError());
    }

    auto *cur_thread_handle = ::GetCurrentThread();
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

    if (opened == FALSE)
        XLOG::l("Failed to open current user token [{}] dup {}", gle,
                duplicated);

    if (!DupeHandle(user_handle))
        LogDupeError(XLOG_FLINE + " !!!");  // gives max rights
    ::RevertToSelf();

    return !wtools::IsBadHandle(user_handle);
}

bool GetUserHandlePredefinedUser(HANDLE &user_handle,
                                 std::wstring_view user_name,
                                 std::wstring_view password) {
    auto [domain, user] = GetDomainUser(std::wstring(user_name));

    auto logged_in = LogonUser(
        user.data(), domain.empty() ? nullptr : domain.c_str(), password.data(),
        LOGON32_LOGON_INTERACTIVE, LOGON32_PROVIDER_WINNT50, &user_handle);
    if ((FALSE == logged_in) || wtools::IsBadHandle(user_handle)) {
        XLOG::l("Error logging in as '{}' [{}]", wtools::ToUtf8(user_name),
                ::GetLastError());
        return false;
    }

    if (!DupeHandle(user_handle)) {
        LogDupeError(XLOG_FLINE + " !!!");
    }

    return true;
}

bool LoadProfile(HANDLE user_handle, PROFILEINFO &profile) {
    EnablePrivilege(SE_RESTORE_NAME);
    EnablePrivilege(SE_BACKUP_NAME);
    auto profile_loaded = ::LoadUserProfile(user_handle, &profile);
    if (profile_loaded != TRUE) {
        XLOG::t("LoadUserProfile failed with error [{}]", ::GetLastError());
        return false;
    }
    return true;
}

bool GetUserHandle(AppSettings &settings, BOOL &profile_loaded,
                   PROFILEINFO &profile, HANDLE hCmdPipe) {
    if (settings.use_system_account) {
        return GetUserHandleSystemAccount(settings.hUser);
    }

    // not Local System, so either as specified user, or as current user
    if (!settings.user.empty()) {
        GetUserHandlePredefinedUser(settings.hUser, settings.user,
                                    settings.password);
        if (!wtools::IsBadHandle(settings.hUser) && !settings.dont_load_profile)
            profile_loaded =
                LoadProfile(settings.hUser, profile) ? TRUE : FALSE;
        return true;
    }

    // run as current user
    return GetUserHandleCurrentUser(settings.hUser, hCmdPipe);
}

using SaferCreateLevelProc = BOOL(WINAPI *)(DWORD dwScopeId, DWORD dwLevelId,
                                            DWORD OpenFlags,
                                            SAFER_LEVEL_HANDLE *pLevelHandle,
                                            void *lpReserved);
using SaferComputeTokenFromLevelProc =
    BOOL(WINAPI *)(SAFER_LEVEL_HANDLE LevelHandle, HANDLE InAccessToken,
                   PHANDLE OutAccessToken, DWORD dwFlags, void *lpReserved);

using SaferCloseLevelProc = BOOL(WINAPI *)(SAFER_LEVEL_HANDLE hLevelHandle);

bool LimitRights(HANDLE &hUser) {
    static SaferCreateLevelProc s_safer_create_level = nullptr;
    static SaferComputeTokenFromLevelProc s_safer_compute_token_from_level =
        nullptr;
    static SaferCloseLevelProc s_safer_close_level = nullptr;

    if ((nullptr == s_safer_close_level) ||
        (nullptr == s_safer_compute_token_from_level) ||
        (nullptr == s_safer_create_level)) {
        HMODULE module_handle = LoadLibrary(L"advapi32.dll");  // GLOK
        if (nullptr != module_handle) {
            s_safer_create_level = reinterpret_cast<SaferCreateLevelProc>(
                GetProcAddress(module_handle, "SaferCreateLevel"));
            s_safer_compute_token_from_level =
                reinterpret_cast<SaferComputeTokenFromLevelProc>(GetProcAddress(
                    module_handle, "SaferComputeTokenFromLevel"));
            s_safer_close_level = reinterpret_cast<SaferCloseLevelProc>(
                GetProcAddress(module_handle, "SaferCloseLevel"));
        }
    }

    if ((nullptr == s_safer_close_level) ||
        (nullptr == s_safer_compute_token_from_level) ||
        (nullptr == s_safer_create_level)) {
        XLOG::l(
            "Safer... calls not supported on this OS -- can't limit rights");
        return false;
    }

    if (!wtools::IsBadHandle(hUser)) {
        HANDLE new_handle = nullptr;
        SAFER_LEVEL_HANDLE safer = nullptr;
        if (FALSE == s_safer_create_level(SAFER_SCOPEID_USER,
                                          SAFER_LEVELID_NORMALUSER,
                                          SAFER_LEVEL_OPEN, &safer, nullptr)) {
            XLOG::l("Failed to limit rights (SaferCreateLevel) [{}]",
                    ::GetLastError());
            return false;
        }

        if (safer != nullptr) {
            if (FALSE == s_safer_compute_token_from_level(
                             safer, hUser, &new_handle, 0, nullptr)) {
                XLOG::l(
                    "Failed to limit rights (SaferComputeTokenFromLevel) {}.",
                    ::GetLastError());
                auto ret = s_safer_close_level(safer);
                if (ret == FALSE) XLOG::l.bp(XLOG_FLINE + " trash!");
                return false;
            }
            auto ret = s_safer_close_level(safer);
            if (ret == FALSE) XLOG::l.bp(XLOG_FLINE + " trash!");
        }

        if (!wtools::IsBadHandle(new_handle)) {
            auto ret = ::CloseHandle(hUser);
            if (ret == FALSE) XLOG::l.bp(XLOG_FLINE + " trash!");

            hUser = new_handle;
            if (!DupeHandle(hUser)) LogDupeError(XLOG_FLINE + " !!!");

            return true;
        }
    }

    XLOG::l("Don't have a good user -- can't limit rights");
    return false;
}

bool ElevateUserToken(HANDLE &hEnvUser) {
    TOKEN_ELEVATION_TYPE tet;  // NOLINT
    DWORD needed = 0;

    if (::GetTokenInformation(hEnvUser, TokenElevationType,
                              static_cast<void *>(&tet), sizeof(tet),
                              &needed) == TRUE) {
        if (tet != TokenElevationTypeLimited) return true;

        // get the associated token, which is the full-admin token
        TOKEN_LINKED_TOKEN tlt = {nullptr};
        if (::GetTokenInformation(hEnvUser, TokenLinkedToken,
                                  static_cast<void *>(&tlt), sizeof(tlt),
                                  &needed) == TRUE) {
            if (!DupeHandle(tlt.LinkedToken)) LogDupeError(XLOG_FLINE + " !!!");
            hEnvUser = tlt.LinkedToken;
            return true;
        }

        XLOG::l("Failed to get elevated token {}", ::GetLastError());
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
                            const std::vector<uint16_t> &affinity) {
    if (affinity.empty()) return;

    DWORD_PTR system_mask = 0;
    DWORD_PTR process_mask = 0;
    auto ret = ::GetProcessAffinityMask(process, &process_mask, &system_mask);
    if (ret == FALSE) XLOG::l.bp(XLOG_FLINE + " hit1!");

    process_mask = 0;
    for (auto a : affinity) {
        DWORD bit = 1;
        bit = bit << (a - 1);
        process_mask |= bit & system_mask;
    }
    ret = ::SetProcessAffinityMask(process, process_mask);
    if (ret == FALSE) XLOG::l.bp(XLOG_FLINE + " hit2!");
}

namespace {
std::wstring GetUserHomeDir(HANDLE token) {
    constexpr size_t len{512};
    wchar_t buf[len];
    DWORD sz = len - 1;

    if (::GetUserProfileDirectoryW(token, buf, &sz) == TRUE) {
        return buf;
    }
    XLOG::d("Fail to get user profile [{}]", ::GetLastError());
    return cma::tools ::win::GetSomeSystemFolder(FOLDERID_Public);
}
}  // namespace

bool StartProcess(AppSettings &settings, HANDLE command_pipe) {
    // Launching as one of:
    // 1. System Account
    // 2. Specified account (or limited account)
    // 3. As current process

    BOOL profile_loaded{FALSE};
    auto profile = MakeProfile(settings.user);

    if (!GetUserHandle(settings, profile_loaded, profile, command_pipe))
        return false;

    PROCESS_INFORMATION pi = {nullptr};
    auto si = MakeStartupInfo(settings);
    auto path = MakePath(settings);
    auto starting_dir = settings.working_dir;

    auto ci = MakeCleanupInteractive(settings, si);

    XLOG::t("Exec using desktop {}", si.lpDesktop == nullptr
                                         ? "{default}"
                                         : wtools::ToUtf8(si.lpDesktop));

    DWORD start_flags = CREATE_SUSPENDED;  //| CREATE_NEW_CONSOLE <- forbidden

    auto *environment = MakeEnvironment(settings.hUser);
    ON_OUT_OF_SCOPE(if (environment)::DestroyEnvironmentBlock(environment));

    if (nullptr != environment) {
        start_flags |= CREATE_UNICODE_ENVIRONMENT;
    }

    if (settings.disable_file_redirection) {
        krnl::DisableFileRedirection();
    }

    if (settings.run_limited && !LimitRights(settings.hUser)) {
        return false;
    }

    if (settings.run_elevated && !ElevateUserToken(settings.hUser)) {
        return false;
    }

    auto [domain, user] = GetDomainUser(settings.user);

    XLOG::t("U:{} D:{} P:{} bP:{} Env:{} WD:{}", wtools::ToUtf8(user),
            wtools::ToUtf8(domain), wtools::ToUtf8(settings.password),
            settings.dont_load_profile,
            environment != nullptr ? "true" : "null",
            starting_dir.empty() ? "null" : wtools::ToUtf8(starting_dir));

    BOOL launched = FALSE;
    DWORD launch_gle = 0;

    if (settings.use_system_account) {
        XLOG::d.i("Exec starting process [{}] as Local System",
                  wtools::ToUtf8(path));

        if (wtools::IsBadHandle(settings.hUser))
            XLOG::l("Have bad user handle");

        EnablePrivilege(SE_IMPERSONATE_NAME);
        auto impersonated = ::ImpersonateLoggedOnUser(settings.hUser);
        if (impersonated == FALSE) {
            XLOG::l.bp("Failed to impersonate {}", ::GetLastError());
        }

        EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
        EnablePrivilege(SE_INCREASE_QUOTA_NAME);
        launched = CreateProcessAsUser(
            settings.hUser, nullptr, path.data(), nullptr, nullptr, TRUE,
            start_flags, environment, starting_dir.c_str(), &si, &pi);
        launch_gle = ::GetLastError();

        if (0 != launch_gle)
            XLOG::t(
                "Launch (launchGLE={}) params: user=[{}] path=[{}] flags=[x{:X}], pEnv=[{}], dir=[{}], stdin=[{}], stdout=[{}], stderr=[{}]",
                launch_gle, settings.hUser, wtools::ToUtf8(path), start_flags,
                environment != nullptr ? "{env}" : "{null}",
                starting_dir.empty() ? "{null}" : ToUtf8(starting_dir),
                si.hStdInput, si.hStdOutput, si.hStdError);

        ::RevertToSelf();
    } else {
        if (!settings.user.empty())  // launching as a specific user
        {
            XLOG::d.i("Exec starting process [{}] as {}", wtools::ToUtf8(path),
                      wtools::ToUtf8(settings.user));
            starting_dir = GetUserHomeDir(settings.hUser);

            if (!settings.run_limited) {
                launched = CreateProcessWithLogonW(
                    user.c_str(), domain.empty() ? nullptr : domain.c_str(),
                    settings.password.c_str(),
                    settings.dont_load_profile ? 0 : LOGON_WITH_PROFILE,
                    nullptr, path.data(), start_flags, environment,
                    starting_dir.empty() ? nullptr : starting_dir.c_str(), &si,
                    &pi);
                launch_gle = ::GetLastError();

                if (0 != launch_gle) {
                    XLOG::t(
                        "Launch (launchGLE={:X}) params: user=[{}] "
                        "domain=[{}] "
                        "prof=[{}] ",
                        launch_gle, wtools::ToUtf8(user),
                        wtools::ToUtf8(domain),
                        settings.dont_load_profile ? 0 : LOGON_WITH_PROFILE);
                    XLOG::t(
                        "path=[{}] flags=[x{:X}],"
                        " pEnv=[{}],"
                        " dir=[{}],"
                        " stdin=[{}], stdout=[{}], stderr=x{}]",
                        wtools::ToUtf8(path), start_flags,
                        environment != nullptr ? "{env}" : "{null}",
                        starting_dir.empty() ? "{null}"
                                             : wtools::ToUtf8(starting_dir),
                        si.hStdInput, si.hStdOutput, si.hStdError);
                }
            } else
                launched = FALSE;  // force to run with CreateProcessAsUser so
                                   // rights can be limited

            // CreateProcessWithLogonW can't be called from LocalSystem on
            // Win2003 and earlier, so LogonUser/CreateProcessAsUser must be
            // used. Might as well try for everyone
            if ((launched == FALSE) && !wtools::IsBadHandle(settings.hUser)) {
                XLOG::t(
                    "Failed CreateProcessWithLogonW - trying CreateProcessAsUser");

                EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
                EnablePrivilege(SE_INCREASE_QUOTA_NAME);
                EnablePrivilege(SE_IMPERSONATE_NAME);
                auto impersonated = ::ImpersonateLoggedOnUser(settings.hUser);
                if (impersonated == FALSE)
                    XLOG::d("Failed to impersonate [{}]", ::GetLastError());

                launched = ::CreateProcessAsUserW(
                    settings.hUser, nullptr, path.data(), nullptr, nullptr,
                    TRUE,
                    CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT |
                        CREATE_NEW_CONSOLE,
                    environment, starting_dir.c_str(), &si, &pi);
                if (0 == ::GetLastError())
                    launch_gle = 0;  // mark as successful, otherwise return our
                                     // original error
                if (0 != launch_gle)
                    XLOG::t(
                        "Launch (launchGLE={}) params: user=[{}] path=[{}] pEnv=[{}], dir=[{}], stdin=[{}], stdout=[{}], stderr=[{}]",
                        launch_gle, settings.hUser, wtools::ToUtf8(path),
                        environment != nullptr ? "{env}" : "{null}",
                        starting_dir.empty() ? "{null}"
                                             : wtools::ToUtf8(starting_dir),
                        si.hStdInput, si.hStdOutput, si.hStdError);
                ::RevertToSelf();
            }
        } else {
            XLOG::d.i("Exec starting process [{}] as current user",
                      wtools::ToUtf8(path));

            EnablePrivilege(SE_ASSIGNPRIMARYTOKEN_NAME);
            EnablePrivilege(SE_INCREASE_QUOTA_NAME);
            EnablePrivilege(SE_IMPERSONATE_NAME);

            if (settings.hUser != nullptr)
                launched = ::CreateProcessAsUser(
                    settings.hUser, nullptr, path.data(), nullptr, nullptr,
                    TRUE, start_flags, environment, starting_dir.c_str(), &si,
                    &pi);
            if (launched == FALSE)
                launched = CreateProcess(nullptr, path.data(), nullptr, nullptr,
                                         TRUE, start_flags, environment,
                                         starting_dir.c_str(), &si, &pi);

            if (launched == FALSE)
                launch_gle = ::GetLastError();
            else
                launch_gle = 0;

            XLOG::d.i(
                "Launch (launchGLE={}) params: path=[{}] user=[{}], pEnv=[{}], dir=[{}], stdin=[{}], stdout=[{}], stderr=[{}]",
                launch_gle, wtools::ToUtf8(path),
                settings.hUser != nullptr ? "{non-null}" : "{null}",
                environment != nullptr ? "{env}" : "{null}",
                starting_dir.empty() ? "{null}" : wtools::ToUtf8(starting_dir),
                si.hStdInput, si.hStdOutput, si.hStdError);
        }
    }

    if (launched == TRUE) {
        if (g_in_service) XLOG::d.i("Successfully launched");

        settings.hProcess = pi.hProcess;
        settings.pid = pi.dwProcessId;

        SetAffinityMask(pi.hProcess, settings.allowed_processors);

        auto ret = ::SetPriorityClass(pi.hProcess, settings.priority);
        if (ret == FALSE) XLOG::l(XLOG_FLINE + " error [{}]", ::GetLastError());
        ResumeThread(pi.hThread);
        ret = ::CloseHandle(pi.hThread);
        if (ret == FALSE) XLOG::l(XLOG_FLINE + " error [{}]", ::GetLastError());

    } else {
        XLOG::l("Failed to start {} [{}]", wtools::ToUtf8(path), launch_gle);
        if ((ERROR_ELEVATION_REQUIRED == launch_gle) && (!g_in_service))
            XLOG::l("HINT: Exec probably needs to be 'Run As Administrator'");
    }

    if (ci.bPreped) CleanUpInteractiveProcess(&ci);

    if (settings.disable_file_redirection) krnl::RevertFileRedirection();

    if (profile_loaded == TRUE)
        UnloadUserProfile(settings.hUser, profile.hProfile);

    if (!wtools::IsBadHandle(settings.hUser)) {
        CloseHandle(settings.hUser);
        settings.hUser = nullptr;
    }

    return launched == TRUE;
}

// Tree controlling command
// returns [ProcId, JobHandle, ProcessHandle]
std::tuple<DWORD, HANDLE, HANDLE> RunAsJob(
    std::wstring_view user_name,  // serg
    std::wstring_view password,   // my_pass
    std::wstring_view command,    // "c.bat"
    BOOL /*inherit_handles*/,     // not optimal, but default
    HANDLE stdio_handle,          // when we want to catch output
    HANDLE stderr_handle,         // same
    DWORD /*creation_flags*/,     // never checked this
    DWORD /*start_flags*/) {
    auto *job_handle = CreateJobObjectA(nullptr, nullptr);

    if (job_handle == nullptr) return {0, nullptr, nullptr};

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
