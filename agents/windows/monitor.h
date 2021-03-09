#pragma once

#include <psapi.h>
//
#include <windows.h>

inline void RestartService() {
    STARTUPINFO si{0};
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags |= STARTF_USESTDHANDLES;
    si.hStdOutput = si.hStdError = nullptr;

    PROCESS_INFORMATION pi{0};

    // simple windows shell command to restart service
    const char *damned_windows =
        "cmd.exe /C net stop check_mk_agent & net start check_mk_agent";

    Logger *logger = Logger::getLogger("winagent");
    Error(logger) << "Restarting service pid is " << ::GetCurrentProcessId();

    if (!::CreateProcessA(nullptr, (char *)damned_windows, nullptr, nullptr,
                          TRUE, 0, nullptr, nullptr, &si, &pi)) {
        Error(logger) << "Failed restart service error, is " << GetLastError();
    }
}

size_t GetOwnVirtualSize() noexcept {
#if defined(_WIN32)
    PROCESS_MEMORY_COUNTERS_EX pmcx = {};
    pmcx.cb = sizeof(pmcx);
    ::GetProcessMemoryInfo(GetCurrentProcess(),
                           reinterpret_cast<PROCESS_MEMORY_COUNTERS *>(&pmcx),
                           pmcx.cb);

    return pmcx.WorkingSetSize;
#else
#error "Not implemented"
    return 0;
#endif
}

namespace monitor {
inline bool EnableHealthMonitor = false; // set to true only on a wish
constexpr size_t kMaxMemoryAllowed = 200'000'000;
inline bool IsAgentHealthy() noexcept {
    return GetOwnVirtualSize() < kMaxMemoryAllowed;
}
}  // namespace monitor
