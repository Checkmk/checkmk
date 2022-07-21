// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Simple Mail Slot Transport
// Windows only
// by SK
// CODE STYLE is a bit old-fashioned, this is mix of MSN example with
// very old implementation

// Thread Safe

// Sender is using postman
// Receiver is using mailbox (with thread/callback)

#pragma once
#include <windows.h>

#include <atomic>
#include <cstdint>
#include <filesystem>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <thread>

#include "common/wtools.h"
#include "tools/_xlog.h"  // trace and log

namespace cma::mailslot {
class Slot;
bool IsApiLogged() noexcept;
std::string GetApiLog();

template <typename... Args>
void ApiLog(Args... args) {
    xlog::l(IsApiLogged(), args...).filelog(GetApiLog());
}

// This is Thread Callback definition
// Slot is a your slot, just to have
// Data & Len is self explanatory
// Context is parameter supplied by YOU, my friend when you creates mailbox,
// it may be nullptr or something important like an address of an object of
// a class to which callback should deliver data
using ThreadProc = bool (*)(const Slot *slot, const void *data, int len,
                            void *context);

constexpr int DEFAULT_THREAD_SLEEP = 20;
constexpr std::string_view controller_slot_prefix{"WinAgentCtl"};

/// convert slot name into fully qualified global object
std::string BuildMailSlotName(std::string_view slot_name, uint32_t id,
                              std::string_view pc_name) noexcept;

class Slot {
public:
    enum class Mode { client, server };

    enum ErrCodes {
        SUCCESS = 0,
        FAILED_READ = -1,
        TOO_SMALL = -2,
        FAILED_INFO = -3,
        FAILED_INIT = -4,
        FAILED_CREATE = -5
    };

    Slot(const Slot &) = delete;
    Slot &operator=(const Slot &) = delete;
    Slot(Slot &&) = delete;
    Slot &operator=(Slot &&) = delete;

    Slot(std::string_view name, uint32_t id, std::string_view pc_name) noexcept
        : name_{BuildMailSlotName(name, id, pc_name)} {}

    Slot(std::string_view name, uint32_t id) noexcept
        : name_{BuildMailSlotName(name, id, ".")} {}

    explicit Slot(std::string_view name) : name_(name) {}

    ~Slot() { Close(); }

    // Accessors
    [[nodiscard]] bool IsOwner() const noexcept {
        return mode_ == Mode::server;
    }
    [[nodiscard]] bool IsClient() const noexcept {
        return mode_ == Mode::client;
    }
    [[nodiscard]] const char *GetName() const noexcept { return name_.c_str(); }
    [[nodiscard]] HANDLE GetHandle() const noexcept { return handle_; }

    bool ConstructThread(ThreadProc foo, int sleep_ms, void *context,
                         wtools::SecurityLevel sl);
    /// mailbox dies here
    void DismantleThread();
    /// postman the only operation
    bool ExecPost(const void *data, uint64_t length);
    /// returns false on duplicated name
    bool Create(wtools::SecurityLevel sl);
    bool Open();
    bool Close();
    bool Post(const void *data, int len);
    int Get(void *data, unsigned int max_len);

private:
    OVERLAPPED CreateOverlapped() const noexcept;
    std::optional<DWORD> CheckMessageSize();

    void MailBoxThread(ThreadProc foo, int sleep_value, void *context);

    static HANDLE openMailSlotWrite(const std::string &name) noexcept;
    static HANDLE createMailSlot(const std::string &name,
                                 wtools::SecurityLevel sl);

    std::mutex lock_;
    std::string name_;        // _fully_ qualified mailslot name
    HANDLE handle_{nullptr};  // handle to the mailslot
    Mode mode_{Mode::client};

    std::atomic<bool> keep_running_{true};  // thread flag
    std::unique_ptr<std::thread>
        main_thread_{};  // controlled by Construct/Dismantle
};

/// returns controller slot_name
inline std::string ControllerMailSlotName(uint32_t pid) noexcept {
    return BuildMailSlotName(controller_slot_prefix, pid, ".");
}

}  // namespace cma::mailslot
