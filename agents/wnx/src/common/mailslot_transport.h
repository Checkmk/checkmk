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

namespace cma {
class MailSlot;
bool IsMailApiTraced() noexcept;
std::string GetMailApiLog();

template <typename... Args>
void MailSlotLog(Args... args) {
    xlog::l(IsMailApiTraced(), args...).filelog(GetMailApiLog());
}

// This is Thread Callback definition
// Slot is a your slot, just to have
// Data & Len is self explanatory
// Context is parameter supplied by YOU, my friend when you creates mailbox,
// it may be nullptr or something important like an address of an object of
// a class to which callback should deliver data
using MailBoxThreadProc = bool (*)(const MailSlot *slot, const void *data,
                                   int len, void *context);

constexpr int DEFAULT_THREAD_SLEEP = 20;

class MailSlot {
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

    MailSlot(const MailSlot &) = delete;
    MailSlot &operator=(const MailSlot &) = delete;
    MailSlot(MailSlot &&) = delete;
    MailSlot &operator=(MailSlot &&) = delete;

    /// convert slot name into fully qualified global object
    static std::string BuildMailSlotName(std::string_view slot_name, int id,
                                         std::string_view pc_name);

    MailSlot(std::string_view name, int id, std::string_view pc_name)
        : name_{BuildMailSlotName(name, id, pc_name)} {}

    MailSlot(std::string_view name, int id)
        : name_{BuildMailSlotName(name, id, ".")} {}

    explicit MailSlot(std::string_view name) : name_(name) {}

    ~MailSlot() { Close(); }

    // Accessors
    [[nodiscard]] bool IsOwner() const noexcept {
        return mode_ == Mode::server;
    }
    [[nodiscard]] bool IsClient() const noexcept {
        return mode_ == Mode::client;
    }
    [[nodiscard]] const char *GetName() const noexcept { return name_.c_str(); }
    [[nodiscard]] HANDLE GetHandle() const noexcept { return handle_; }

    bool ConstructThread(MailBoxThreadProc foo, int sleep_ms, void *context,
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
    OVERLAPPED
    CreateOverlapped() const noexcept;
    std::optional<DWORD> CheckMessageSize();

    void MailBoxThread(MailBoxThreadProc foo, int sleep_value, void *context);

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
};  // namespace cma
