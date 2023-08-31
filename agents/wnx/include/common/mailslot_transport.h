// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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

constexpr int g_default_thread_sleep = 20;
constexpr std::string_view g_controller_slot_prefix{"WinAgentCtl"};

/// convert slot name into fully qualified global object
std::string BuildCustomMailSlotName(std::string_view slot_name, uint32_t id,
                                    std::string_view pc_name);

std::string BuildMailSlotNameStem(Modus modus, uint32_t id);
std::string BuildMailSlotNameRoot(std::string_view pc_name);
inline std::string BuildMailSlotNameRoot() {
    return BuildMailSlotNameRoot(".");
}

class Slot {
public:
    enum class Mode { client, server };

    enum ErrCodes {
        success = 0,
        failed_read = -1,
        too_small = -2,
        failed_info = -3,
        failed_init = -4,
        failed_create = -5
    };

    Slot(const Slot &) = delete;
    Slot &operator=(const Slot &) = delete;
    Slot(Slot &&) = delete;
    Slot &operator=(Slot &&) = delete;

    Slot(Modus modus, uint32_t id) noexcept
        : name_{BuildMailSlotNameRoot() + BuildMailSlotNameStem(modus, id)} {}

    Slot(std::string_view name, uint32_t id) noexcept
        : name_{BuildCustomMailSlotName(name, id, ".")} {}

    explicit Slot(std::string_view name) : name_(name) {}

    ~Slot() { Close(); }

    // Accessors
    [[nodiscard]] bool IsOwner() const noexcept {
        return mode_ == Mode::server;
    }
    [[nodiscard]] bool IsClient() const noexcept {
        return mode_ == Mode::client;
    }
    [[nodiscard]] std::string GetName() const noexcept { return name_; }
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
    int Get(void *data, unsigned int max_len);

private:
    bool Post(const void *data, int len);
    static OVERLAPPED CreateOverlapped() noexcept;
    std::optional<DWORD> CheckMessageSize() const;

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
    return BuildCustomMailSlotName(g_controller_slot_prefix, pid, ".");
}

}  // namespace cma::mailslot
