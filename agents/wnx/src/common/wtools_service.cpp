// Windows Tools
#include "stdafx.h"

#include "wtools_service.h"

#include <cstdint>
#include <string_view>
#include <vector>

#include "logger.h"
#include "tools/_raii.h"
#include "tools/_win.h"

namespace wtools {

uint32_t WinService::ReadUint32(std::wstring_view service_name,
                                std::string_view value_name) {
    return LocalReadUint32(pathToRegistry(service_name).c_str(),
                           value_name.data(), -1);
}

std::string WinService::pathToRegistry(std::wstring_view service) {
    const std::string base{R"(SYSTEM\CurrentControlSet\Services\)"};
    return base + wtools::ToUtf8(service);
}

WinService::WinService(std::wstring_view name) {
    auto *manager_handle =
        ::OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (nullptr == manager_handle) {
        XLOG::l.crit("Cannot open SC Manager {}", ::GetLastError());
        return;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(manager_handle));

    handle_ = ::OpenService(manager_handle, name.data(), SERVICE_ALL_ACCESS);

    if (nullptr == handle_) {
        XLOG::l.crit("Cannot open Service {}, error =  {}",
                     wtools::ToUtf8(name), ::GetLastError());
    }
}

LocalResource<SERVICE_FAILURE_ACTIONS> WinService::GetServiceFailureActions() {
    SERVICE_FAILURE_ACTIONS *actions = nullptr;

    std::lock_guard lk(lock_);
    if (!IsGoodHandle(handle_)) return nullptr;

    DWORD bytes_needed = 0;

    if (::QueryServiceConfig2(handle_, SERVICE_CONFIG_FAILURE_ACTIONS, nullptr,
                              0, &bytes_needed) == TRUE) {
        XLOG::l("Bad idea to hit here");
        return nullptr;
    }

    auto last_error = ::GetLastError();
    if (ERROR_INSUFFICIENT_BUFFER != last_error) {
        XLOG::l("Received bad error code [{}]", last_error);
        return nullptr;
    }

    // allocation
    auto new_buf_size = bytes_needed;
    actions = reinterpret_cast<SERVICE_FAILURE_ACTIONS *>(
        ::LocalAlloc(LMEM_FIXED, new_buf_size));

    if (::QueryServiceConfig2(handle_, SERVICE_CONFIG_FAILURE_ACTIONS,
                              reinterpret_cast<BYTE *>(actions), new_buf_size,
                              &bytes_needed) == TRUE)
        return LocalResource<SERVICE_FAILURE_ACTIONS>(actions);

    XLOG::l("Attempt to query service config failed with error [{}]",
            ::GetLastError());

    // we have to kill our actions data here
    if (actions != nullptr) ::LocalFree(actions);

    return nullptr;
}

SERVICE_FAILURE_ACTIONS CreateServiceFailureAction(int delay) {
    SERVICE_FAILURE_ACTIONS failure_actions;
    failure_actions.dwResetPeriod =
        delay;                            // Reset Failures Counter, in Seconds
    failure_actions.lpCommand = nullptr;  // on service failure, not used
    failure_actions.lpRebootMsg = nullptr;  // Message during rebooting computer
                                            // due to service failure, not used

    failure_actions.cActions = 0;  // Number of failure action to manage
    failure_actions.lpsaActions = nullptr;

    return failure_actions;
}

/// \brief wraps low level win32 API-calls to make service restartable or not
bool WinService::configureRestart(bool restart) {
    auto action = restart ? SC_ACTION_RESTART : SC_ACTION_NONE;
    constexpr int count_of_actions = 3;  // in windows service
    std::vector<SC_ACTION> fail_actions(count_of_actions,
                                        SC_ACTION{action, 2000});

    auto service_fail_actions = CreateServiceFailureAction(3600);
    service_fail_actions.cActions = static_cast<int>(fail_actions.size());
    service_fail_actions.lpsaActions = fail_actions.data();

    std::lock_guard lk(lock_);
    if (!IsGoodHandle(handle_)) return false;

    auto result =
        ::ChangeServiceConfig2(handle_, SERVICE_CONFIG_FAILURE_ACTIONS,
                               &service_fail_actions);  // Apply above settings
    if (result == TRUE) return true;

    XLOG::l("Error [{}] configuring service", ::GetLastError());
    return false;
}

/// \brief change service parameters
///
/// returns last error
static uint32_t CallChangeServiceConfig(SC_HANDLE handle, DWORD start_type,
                                        DWORD error_control) {
    auto ret = ::ChangeServiceConfig(handle,
                                     SERVICE_NO_CHANGE,  // dwServiceType,
                                     start_type,         // dwStartType,
                                     error_control,      // dwErrorControl,
                                     nullptr,            // lpBinaryPathName,
                                     nullptr,            // lpLoadOrderGroup,
                                     nullptr,            // lpdwTagId,
                                     nullptr,            // lpDependencies,
                                     nullptr,            // lpServiceStartName,
                                     nullptr,            // lpPassword,
                                     nullptr             // lpDisplayName
    );

    return ret == TRUE ? 0 : ::GetLastError();
};

/// \brief set service delayed flag if configured
///
/// returns last error
static uint32_t CallChangeServiceDelay(SC_HANDLE handle, bool delayed) {
    SERVICE_DELAYED_AUTO_START_INFO dasi;
    dasi.fDelayedAutostart = delayed ? TRUE : FALSE;
    auto ret = ::ChangeServiceConfig2A(
        handle, SERVICE_CONFIG_DELAYED_AUTO_START_INFO, &dasi);

    return ret == TRUE ? 0 : ::GetLastError();
};

static uint32_t StartMode2WinApi(WinService::StartMode mode) {
    switch (mode) {
        case WinService::StartMode::disabled:
            return SERVICE_DISABLED;
        case WinService::StartMode::stopped:
            return SERVICE_DEMAND_START;
        case WinService::StartMode::started:
            [[fallthrough]];
        case WinService::StartMode::delayed:
            return SERVICE_AUTO_START;
    }

    return SERVICE_NO_CHANGE;
}

static uint32_t LogMode2WinApi(WinService::ErrorMode mode) {
    switch (mode) {
        case WinService::ErrorMode::ignore:
            return SERVICE_ERROR_IGNORE;
        case WinService::ErrorMode::log:
            return SERVICE_ERROR_NORMAL;
    }

    return SERVICE_NO_CHANGE;
}

bool WinService::configureStart(StartMode mode) {
    auto start_mode = StartMode2WinApi(mode);

    auto error_code_1 =
        CallChangeServiceConfig(handle_, start_mode, SERVICE_NO_CHANGE);

    auto error_code_2 =
        CallChangeServiceDelay(handle_, mode == StartMode::delayed);

    if (error_code_1 == 0 && error_code_2 == 0) return true;

    XLOG::l("Failed to set service start to [{}], errors are [{}] [{}]",
            start_mode, error_code_1, error_code_2);
    return false;
}

bool WinService::configureError(ErrorMode log_mode) {
    auto error_control = LogMode2WinApi(log_mode);
    auto error_code =
        CallChangeServiceConfig(handle_, SERVICE_NO_CHANGE, error_control);
    if (error_code == 0) return true;

    XLOG::l("Failed to set service error control to [{}], error isn [{}]",
            error_control, error_code);
    return false;
}

}  // namespace wtools
