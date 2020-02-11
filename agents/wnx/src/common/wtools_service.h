// wtools_service.h
//
// Windows Specific Tools to control service
//
#pragma once

#ifndef wtools_service_h__
#define wtools_service_h__

#include "wtools.h"

namespace wtools {
class WinService {
public:
    enum class StartMode { disabled, stopped, started };
    enum class ErrorMode { ignore, log };
    explicit WinService(std::wstring_view name);

    static constexpr std::string_view kRegErrorControl = "ErrorControl";
    static constexpr std::string_view kRegStart = "Start";

    // API to simple access to configuration
    static uint32_t ReadUint32(std::wstring_view service,
                               std::string_view name);

    // no copy
    WinService(const WinService& rhs) = delete;
    WinService& operator=(const WinService& rhs) = delete;

    // move
    WinService(WinService&& rhs) noexcept {
        std::lock_guard lk(rhs.lock_);
        handle_ = rhs.handle_;
        rhs.handle_ = nullptr;
    }

    WinService& operator=(WinService&& rhs) noexcept {
        std::unique_lock lk(rhs.lock_);
        auto handle = rhs.handle_;
        rhs.handle_ = nullptr;
        lk.unlock();

        std::lock_guard l(lock_);
        if (IsHandleValid(handle_)) ::CloseServiceHandle(handle_);
        handle_ = handle;
    }

    ~WinService() {
        if (isOpened()) ::CloseServiceHandle(handle_);
    }

    bool isOpened() const noexcept {
        std::lock_guard lk(lock_);
        return IsHandleValid(handle_);
    }
    LocalResource<SERVICE_FAILURE_ACTIONS> GetServiceFailureActions();

    bool configureRestart(bool restart);

    bool configureStart(StartMode mode);

    bool configureError(ErrorMode log_mode);

private:
    mutable std::mutex lock_;
    SC_HANDLE handle_ = nullptr;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class WtoolsService;
    FRIEND_TEST(WtoolsService, All);
    FRIEND_TEST(WtoolsService, Ctor);
#endif
};

}  // namespace wtools

#endif  // wtools_service_h__
