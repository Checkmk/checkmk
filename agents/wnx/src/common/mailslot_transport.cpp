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

#include <stdafx.h>
//
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <strstream>
#include <thread>

#include "common/mailslot_transport.h"
#include "tools/_xlog.h"  // trace and log
#include "wtools.h"

namespace cma {
constexpr bool kUsePublicProfileLog = true;  // to Profile(not to Windows)
constexpr const char *const kMailSlotLogFileName = "cmk_mail.log";

bool IsMailApiTraced() noexcept { return false; }

std::string GetMailApiLog() {
    if (kUsePublicProfileLog) {
        std::filesystem::path path{
            tools::win::GetSomeSystemFolder(FOLDERID_Public)};
        if (!path.empty()) {
            return wtools::ToUtf8((path / kMailSlotLogFileName).wstring());
        }
    }

    if (std::filesystem::path win_path =
            tools::win::GetSomeSystemFolder(FOLDERID_Windows);
        !win_path.empty()) {
        return wtools::ToUtf8(
            (win_path / "Logs" / kMailSlotLogFileName).wstring());
    }

    return {};
}

std::string MailSlot::BuildMailSlotName(std::string_view slot_name, int id,
                                        std::string_view pc_name) {
    std::string name = "\\\\";
    name += pc_name;
    name += R"(\mailslot\Global\)";  // this work. ok. don't touch.
    name += slot_name;
    name += "_";
    name += std::to_string(id);  // session id or something unique
    return name;
}

bool MailSlot::ConstructThread(MailBoxThreadProc foo, int sleep_ms,
                               void *context, wtools::SecurityLevel sl) {
    if (main_thread_) {
        MailSlotLog(XLOG_FUNC + " Double call is forbidden");
        return false;
    }

    keep_running_ = true;
    while (!Create(sl)) {
        name_ += "x";
    }

    main_thread_ = std::make_unique<std::thread>(&MailSlot::MailBoxThread, this,
                                                 foo, sleep_ms, context);
    return true;
}

void MailSlot::DismantleThread() {
    keep_running_ = false;
    if (main_thread_) {
        if (main_thread_->joinable()) {
            main_thread_->join();
        }
        main_thread_.reset();
    }
    Close();
}

bool MailSlot::ExecPost(const void *data, uint64_t length) {
    const auto len = static_cast<int>(length);
    if (data == nullptr && len != 0) {
        MailSlotLog("Bad data for \"%s\"posting %p %d", name_.c_str(), data,
                    len);
        return false;
    }

    if (Open()) {
        const auto ret = Post(data, len);
        Close();
        return ret;
    }

    MailSlotLog("Can't open mail slot \"%s\"", name_.c_str());
    return false;
}

bool MailSlot::Create(wtools::SecurityLevel sl) {
    std::lock_guard<std::mutex> lck(lock_);

    if (handle_ != nullptr) {
        return true;  // bad(already exists) call
    }

    handle_ = createMailSlot(name_, sl);

    if (handle_ == nullptr && ::GetLastError() == 183)  // duplicated file name
    {
        MailSlotLog("Duplicated OWN mail slot \"%s\" Retry with OPEN",
                    name_.c_str());
        return false;
    }

    if (handle_ != nullptr) {
        mode_ = Mode::server;
        MailSlotLog("OWN Mail slot \"%s\" was opened", name_.c_str());
    } else {
        MailSlotLog("Fail open OWN mail slot \"%s\" %d", name_.c_str(),
                    ::GetLastError());
    }

    return true;
}

bool MailSlot::Open() {
    std::lock_guard<std::mutex> lck(lock_);

    if (handle_ != nullptr) {
        return true;  // bad(already exists) call
    }
    handle_ = openMailSlotWrite(name_);

    if (wtools::IsInvalidHandle(handle_)) {
        handle_ = nullptr;
        MailSlotLog("Fail open mail slot \"%s\" %d", name_.c_str(),
                    ::GetLastError());
    } else {
        MailSlotLog("Mail slot \"%s\" was opened", name_.c_str());
    }

    return handle_ != nullptr;
}

bool MailSlot::Close() {
    std::lock_guard<std::mutex> lck(lock_);
    if (handle_ == nullptr) {
        return true;
    }

    if (::CloseHandle(handle_) != 0) {
        handle_ = nullptr;
    } else {
        // do not clean `handle_`
        MailSlotLog("Fail CLOSE mail slot \"%s\" %d", name_.c_str(),
                    ::GetLastError());
    }

    return true;
}

bool MailSlot::Post(const void *data, int len) {
    std::lock_guard<std::mutex> lck(lock_);
    if ((handle_ == nullptr) || IsOwner()) {
        MailSlotLog("Bad situation %p %d", handle_,
                    static_cast<int>(IsOwner()));
        return false;
    }

    if (DWORD written{0U};
        ::WriteFile(handle_, data, len, &written, nullptr) != 0) {
        return true;
    }

    MailSlotLog("Bad write %d", ::GetLastError());
    return false;
}

int MailSlot::Get(void *data, unsigned int max_len) {
    std::lock_guard<std::mutex> lck(lock_);
    if ((handle_ == nullptr) || IsClient()) {
        return ErrCodes::FAILED_INIT;
    }
    auto msg_size = CheckMessageSize();
    if (!msg_size.has_value()) {
        return ErrCodes::FAILED_INFO;
    }
    auto message_size = *msg_size;

    if (message_size == MAILSLOT_NO_MESSAGE) {
        return ErrCodes::SUCCESS;
    }
    if (data == nullptr) {
        return message_size;
    }
    if (max_len < message_size) {
        return ErrCodes::TOO_SMALL;
    }

    OVERLAPPED ov = CreateOverlapped();
    if (ov.hEvent == nullptr) {
        MailSlotLog("Failed Create Event with error %d", ::GetLastError());
        return ErrCodes::FAILED_CREATE;
    }
    ON_OUT_OF_SCOPE(::CloseHandle(ov.hEvent));
    if (DWORD message_read{0U};
        ::ReadFile(handle_, data, message_size, &message_read, &ov) != 0) {
        return static_cast<int>(message_read);
    }

    MailSlotLog("Failed read mail slot with error %d", ::GetLastError());

    return ErrCodes::FAILED_READ;
}

OVERLAPPED MailSlot::CreateOverlapped() const noexcept {
    OVERLAPPED ov = {0};
    ov.Offset = 0;
    ov.OffsetHigh = 0;
    ov.hEvent = ::CreateEvent(nullptr, FALSE, FALSE, nullptr);

    return ov;
}

std::optional<DWORD> MailSlot::CheckMessageSize() {
    DWORD message_size = 0;
    DWORD message_count = 0;

    if (::GetMailslotInfo(handle_,         // mailslot handle
                          nullptr,         // no maximum message size
                          &message_size,   // size of next message
                          &message_count,  // number of messages
                          nullptr)         // no read time-out
        == FALSE) {
        return {};
    }

    return message_size;
}

void MailSlot::MailBoxThread(MailBoxThreadProc foo, int sleep_value,
                             void *context) {
    int buffer_size = 16000;
    auto buffer = std::make_unique<char[]>(buffer_size);
    while (keep_running_) {
        if (const auto required_size = Get(nullptr, buffer_size);
            required_size > buffer_size) {
            buffer = std::make_unique<char[]>(required_size);
            buffer_size = required_size;
        }

        if (const auto read_size = Get(buffer.get(), buffer_size);
            read_size > 0 && foo != nullptr) {
            foo(this, buffer.get(), read_size, context);
        }

        ::Sleep(sleep_value > 0 ? sleep_value
                                : DEFAULT_THREAD_SLEEP);  // we need sleep to
                                                          // prevent polling
    }
}

HANDLE MailSlot::openMailSlotWrite(const std::string &name) noexcept {
    return ::CreateFileA(name.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                         OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
}

HANDLE MailSlot::createMailSlot(const std::string &name,
                                wtools::SecurityLevel sl) {
    wtools::SecurityAttributeKeeper security_attribute_keeper(sl);
    auto *sa = security_attribute_keeper.get();
    if (sa == nullptr) {
        MailSlotLog("Failed to create security descriptor");
        return nullptr;
    }

    return ::CreateMailslotA(
        name.c_str(),           // name
        0,                      // no maximum message size
        MAILSLOT_WAIT_FOREVER,  // no time-out for operations
        sa);                    // black magic resulted SECURITY_ATTRIBUTES
}

}  // namespace cma
