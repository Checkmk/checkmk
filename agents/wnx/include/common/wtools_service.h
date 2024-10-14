// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// wtools_service.h
//
// Windows Specific Tools to control service
//
#pragma once

#ifndef wtools_service_h__
#define wtools_service_h__

#include "tools/_win.h"
#include "wtools.h"

namespace wtools {
class WinService final {
public:
    enum class StartMode { disabled, stopped, started, delayed };
    enum class ErrorMode { ignore, log };
    explicit WinService(std::wstring_view name);

    static constexpr std::string_view kRegErrorControl = "ErrorControl";
    static constexpr std::string_view kRegStart = "Start";

    // API to simple access to configuration
    static uint32_t readUint32(std::wstring_view service_name,
                               std::string_view value_name);

    // no copy
    WinService(const WinService &rhs) = delete;
    WinService &operator=(const WinService &rhs) = delete;

    // move
    WinService(WinService &&rhs) noexcept {
        std::lock_guard lk(rhs.lock_);
        handle_ = rhs.handle_;
        rhs.handle_ = nullptr;
    }

    WinService &operator=(WinService &&rhs) noexcept {
        std::unique_lock lk(rhs.lock_);
        auto *handle = rhs.handle_;
        rhs.handle_ = nullptr;
        lk.unlock();

        std::lock_guard l(lock_);
        if (IsGoodHandle(handle_)) {
            ::CloseServiceHandle(handle_);
        }
        handle_ = handle;
        return *this;
    }

    ~WinService() {
        if (isOpened()) {
            ::CloseServiceHandle(handle_);
        }
    }

    bool isOpened() const noexcept {
        std::lock_guard lk(lock_);
        return IsGoodHandle(handle_);
    }
    LocalResource<SERVICE_FAILURE_ACTIONS> GetServiceFailureActions() const;

    static std::string pathToRegistry(std::wstring_view service);

    [[maybe_unused]] bool configureRestart(bool restart) const;

    bool configureStart(StartMode mode) const;

    [[maybe_unused]] bool configureError(ErrorMode log_mode) const;

private:
    mutable std::mutex lock_;
    SC_HANDLE handle_ = nullptr;
};

}  // namespace wtools

#endif  // wtools_service_h__
