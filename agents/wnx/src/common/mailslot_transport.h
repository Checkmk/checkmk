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
#include <string>
#include <strstream>
#include <thread>

#include "tools/_process.h"  // folders
#include "tools/_win.h"      // trace and log
#include "tools/_xlog.h"     // trace and log

// to be moved outside
namespace wtools {
// we are using custom allocator because of Windows taking care about memory
// allocated
inline void* ProcessHeapAlloc(size_t size) {
    return HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, size);
}

inline void ProcessHeapFree(void* data) {
    if (data) HeapFree(GetProcessHeap(), 0, data);
}

// legacy from the past
inline ACL* BuildSDAcl() {
    SID_IDENTIFIER_AUTHORITY siaWorld = SECURITY_WORLD_SID_AUTHORITY;
    SID_IDENTIFIER_AUTHORITY siaCreator = SECURITY_CREATOR_SID_AUTHORITY;

    char buf_everyone_sid[32];
    char buf_creator_sid[32];

    auto everyone_sid = reinterpret_cast<SID*>(buf_everyone_sid);
    auto owner_sid = reinterpret_cast<SID*>(buf_creator_sid);

    // initialize well known SID's
    if (!InitializeSid(everyone_sid, &siaWorld, 1) ||
        !InitializeSid(owner_sid, &siaCreator, 1))
        return nullptr;

    *GetSidSubAuthority(everyone_sid, 0) = SECURITY_WORLD_RID;
    *GetSidSubAuthority(owner_sid, 0) = SECURITY_CREATOR_OWNER_RID;

    // compute size of acl
    auto acl_size = sizeof(ACL) +
                    2 * (sizeof(ACCESS_ALLOWED_ACE) - sizeof(DWORD)) +
                    GetSidLengthRequired(1) +  // well-known Everyone Sid
                    GetSidLengthRequired(1);   // well-known Creator Owner Sid

    // create ACL
    auto acl = static_cast<ACL*>(ProcessHeapAlloc(acl_size));

    // init ACL
    if (acl && InitializeAcl(acl, (int32_t)acl_size, ACL_REVISION) &&
        AddAccessAllowedAce(acl, ACL_REVISION, FILE_ALL_ACCESS, everyone_sid) &&
        AddAccessAllowedAce(acl, ACL_REVISION, FILE_ALL_ACCESS, owner_sid))
        return acl;

    // FAILURE is HERE
    ProcessHeapFree(acl);
    return nullptr;
}

// RAII class to keep MS Windows Security Descriptor temporary
class SecurityAttributeKeeper {
public:
    SecurityAttributeKeeper() {
        if (!allocAll()) cleanupAll();  // failed here
    }
    ~SecurityAttributeKeeper() { cleanupAll(); }

    const SECURITY_ATTRIBUTES* get() const { return sa_; }
    SECURITY_ATTRIBUTES* get() { return sa_; }

private:
    bool allocAll() {
        acl_ = BuildSDAcl();  // this trash is referenced in the Security
                              // Descriptor, we should keepit safe
        sd_ = static_cast<SECURITY_DESCRIPTOR*>(
            ProcessHeapAlloc(sizeof(SECURITY_DESCRIPTOR)));
        sa_ = static_cast<SECURITY_ATTRIBUTES*>(
            ProcessHeapAlloc(sizeof(SECURITY_ATTRIBUTES)));

        if (acl_ && sd_ && sa_ &&  // <--- alloc check
            InitializeSecurityDescriptor(sd_, SECURITY_DESCRIPTOR_REVISION) &&
            SetSecurityDescriptorDacl(sd_, TRUE, acl_, FALSE)) {
            sa_->nLength = sizeof(SECURITY_ATTRIBUTES);
            sa_->lpSecurityDescriptor = sd_;
            sa_->bInheritHandle = FALSE;
            return true;
        }
        return false;
    }
    void cleanupAll() {
        if (acl_) ProcessHeapFree(acl_);
        if (sd_) ProcessHeapFree(sd_);
        if (sa_) ProcessHeapFree(sa_);
        acl_ = nullptr;
        sd_ = nullptr;
        sa_ = nullptr;
    }

    // below are allocated using ProcessHeapAlloc values
    SECURITY_DESCRIPTOR* sd_{nullptr};
    SECURITY_ATTRIBUTES* sa_{nullptr};
    ACL* acl_{nullptr};
};

}  // namespace wtools

namespace cma {
class MailSlot;

constexpr bool kUsePublicProfileLog = true;  // to Profile(not to Windows)

constexpr const char* const kMailSlotLogFilePrivate =
    "\\Logs\\cmk_mail_log.log";
constexpr const char* const kMailSlotLogFileName = "cmk_mail.log";

inline bool IsMailApiTraced() { return true; }

// #TODO gtest
inline const std::string GetMailApiLog() {
    using namespace cma::tools;
    namespace fs = std::filesystem;

    if (kUsePublicProfileLog) {
        fs::path path = win::GetSomeSystemFolder(FOLDERID_Public);
        if (!path.empty()) return (path / kMailSlotLogFileName).u8string();
    }

    fs::path win_path = win::GetSomeSystemFolder(FOLDERID_Windows);

    if (!win_path.empty())
        return (win_path / "Logs" / kMailSlotLogFileName).u8string();

    return {};
}

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
using MailBoxThreadFoo = bool (*)(const MailSlot* slot, const void* data,
                                  int len, void* context);

constexpr int DEFAULT_THREAD_SLEEP = 20;

class MailSlot {
public:
    enum ErrCodes {
        SUCCESS = 0,
        FAILED_READ = -1,
        TOO_SMALL = -2,
        FAILED_INFO = -3,
        FAILED_INIT = -4,
        FAILED_CREATE = -5
    };

    MailSlot(const MailSlot&) = delete;
    MailSlot& operator=(const MailSlot&) = delete;

    MailSlot(MailSlot&&) = delete;
    MailSlot& operator=(MailSlot&&) = delete;

public:
    // convert slot name into fully qualified global object
    static std::string BuildMailSlotName(const char* slot_name, int id,
                                         const char* pc_name) {
        std::string name = "\\\\";
        name += pc_name;
        name += "\\mailslot\\Global\\";  // this work. ok. don't touch.
        name += slot_name;
        name += "_";
        name += std::to_string(id);  // session id or something unique
        return name;
    }
    MailSlot(const char* name, int id, const char* pc_name) {
        name_ = BuildMailSlotName(name, id, pc_name);
    }

    MailSlot(const char* name, int id) {
        name_ = BuildMailSlotName(name, id, ".");
    }

    // with prepared mail slot
    explicit MailSlot(const char* name) : name_(name) {}

    ~MailSlot() { Close(); }

    // API below

    // Accessors
    [[nodiscard]] bool IsOwner() const noexcept {
        return owner_;
    }  // true, if mailslot had been "created", false if "opened"
    [[nodiscard]] bool IsPostman() const noexcept { return !owner_; }
    [[nodiscard]] const char* GetName() const noexcept { return name_.c_str(); }
    [[nodiscard]] HANDLE GetHandle() const noexcept { return handle_; }

    bool ConstructThread(cma::MailBoxThreadFoo foo, int sleep_ms,
                         void* context) {
        return ConstructThread(foo, sleep_ms, context, false);
    }

    // mailbox start here
    bool ConstructThread(cma::MailBoxThreadFoo foo, int sleep_ms, void* context,
                         bool force_open) {
        if (main_thread_) {
            MailSlotLog(XLOG_FUNC + " Double call is forbidden");
            return false;
        }

        keep_running_ = true;
        if (force_open) {
            // future use only or will be removed
            for (int i = 0; i < 10; i++) {
                auto ret = Create();
                if (ret) break;
                Close();
                using namespace std::chrono;
                std::this_thread::sleep_for(100ms);
            }
        } else
            while (!Create()) {
                name_ += "x";
            }

        main_thread_ = std::make_unique<std::thread>(
            &MailSlot::MailBoxThread, this, foo, sleep_ms, context);
        return true;
    }

    // mailbox dies here
    void DismantleThread() {
        keep_running_ = false;
        if (main_thread_) {
            if (main_thread_->joinable()) main_thread_->join();
            main_thread_.reset();
        }
        Close();
    }

    // postman the only operation
    bool ExecPost(const void* data, uint64_t length) {
        auto len = static_cast<int>(length);
        if (data == nullptr && len != 0) {
            MailSlotLog("Bad data for \"%s\"posting %p %d", name_.c_str(), data,
                        len);
            return false;
        }

        if (Open()) {
            auto ret = Post(data, len);
            Close();
            return ret;
        }

        MailSlotLog("Can't open mail slot \"%s\"", name_.c_str());
        return false;
    }

    // returns false on duplicated name
    bool Create() {
        std::lock_guard<std::mutex> lck(lock_);

        if (handle_) return true;  // bad(already exists) call

        handle_ = createMailSlot(name_.c_str());

        if (handle_ == nullptr &&
            ::GetLastError() == 183)  // duplicated file name
        {
            MailSlotLog("Duplicated OWN mail slot \"%s\" Retry with OPEN",
                        name_.c_str());
            return false;
        }

        if (handle_ != nullptr) {
            owner_ = true;  // we create -> we own
            MailSlotLog("OWN Mail slot \"%s\" was opened", name_.c_str());
        } else {
            MailSlotLog("Fail open OWN mail slot \"%s\" %d", name_.c_str(),
                        ::GetLastError());
        }

        return true;
    }

    bool Open() {
        std::lock_guard<std::mutex> lck(lock_);

        if (handle_) return true;  // bad(already exists) call
        handle_ = openMailSlotWrite(name_.c_str());

        if (wtools::IsInvalidHandle(handle_)) {
            auto error = ::GetLastError();
            handle_ = nullptr;
            MailSlotLog("Fail open mail slot \"%s\" %d", name_.c_str(), error);
        } else
            MailSlotLog("Mail slot \"%s\" was opened", name_.c_str());

        return handle_ != nullptr;
    }

    bool Close() {
        std::lock_guard<std::mutex> lck(lock_);
        if (nullptr == handle_) return true;

        auto ret = ::CloseHandle(handle_);
        if (ret)
            handle_ = nullptr;
        else {
            // if failed do not clean value
            auto error = ::GetLastError();
            MailSlotLog("Fail CLOSE mail slot \"%s\" %d", name_.c_str(), error);
        }

        return true;
    }

    bool Post(const void* Data, int Len) {
        std::lock_guard<std::mutex> lck(lock_);
        if (!handle_ || IsOwner()) {
            MailSlotLog("Bad situation %p %d", handle_, (int)IsOwner());
            return false;
        }

        DWORD written = 0;
        auto success = ::WriteFile(handle_, Data, Len, &written, nullptr);

        if (success) return true;

        MailSlotLog("Bad write %d", ::GetLastError());
        return false;
    }

    int Get(void* data, unsigned int max_len) {
        std::lock_guard<std::mutex> lck(lock_);
        if (!handle_ || IsPostman()) return ErrCodes::FAILED_INIT;
        auto event = ::CreateEvent(nullptr, FALSE, FALSE, nullptr);
        if (nullptr == event) {
            auto error = ::GetLastError();
            MailSlotLog("Failed Create Event with error %d", error);

            return ErrCodes::FAILED_CREATE;
        }
        ON_OUT_OF_SCOPE(::CloseHandle(event));

        OVERLAPPED ov = {0};
        ov.Offset = 0;
        ov.OffsetHigh = 0;
        ov.hEvent = event;

        DWORD message_size = 0;
        DWORD message_count = 0;

        auto success = ::GetMailslotInfo(handle_,  // mailslot handle
                                         nullptr,  // no maximum message size
                                         &message_size,  // size of next message
                                         &message_count,  // number of messages
                                         nullptr);        // no read time-out

        if (!success) return ErrCodes::FAILED_INFO;

        if (message_size == MAILSLOT_NO_MESSAGE) return ErrCodes::SUCCESS;

        if (data == nullptr) return message_size;

        if (max_len < message_size) return ErrCodes::TOO_SMALL;

        DWORD message_read = 0;
        success = ::ReadFile(handle_, data, message_size, &message_read, &ov);

        if (success) return message_read;

        auto error = ::GetLastError();
        MailSlotLog("Failed read mail slot with error %d", error);

        return ErrCodes::FAILED_READ;
    }

    void MailBoxThread(cma::MailBoxThreadFoo foo, int sleep_value,
                       void* context) {
        int buffer_size = 16000;
        char* buffer = new char[buffer_size];
        while (keep_running_) {
            auto required_size = Get(nullptr, buffer_size);
            if (required_size > buffer_size) {
                delete[] buffer;
                buffer = new char[required_size];
                buffer_size = required_size;
            }

            auto read_size = Get(buffer, buffer_size);
            if (read_size > 0) {
                foo(this, buffer, read_size, context);
            } else if (read_size < 0) {
            }

            ::Sleep(sleep_value > 0
                        ? sleep_value
                        : cma::DEFAULT_THREAD_SLEEP);  // we need sleep to
                                                       // prevent polling
        }
        delete[] buffer;
    }

    // typically called from the ::Open, to write data in
    static HANDLE openMailSlotWrite(const char* name) {
        return ::CreateFileA(name, GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                             OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    }

    static HANDLE createMailSlot(const char* name) {
        wtools::SecurityAttributeKeeper
            security_attribute_keeper;  // black magic behind, do not try to
                                        // understand, RAII auto-destroy
        auto sa = security_attribute_keeper.get();
        if (nullptr == sa) {
            MailSlotLog("Failed to create security descriptor");
            return nullptr;
        }

        return CreateMailslotA(
            name,                   // name
            0,                      // no maximum message size
            MAILSLOT_WAIT_FOREVER,  // no time-out for operations
            sa);                    // black magic resulted SECURITY_ATTRIBUTES
    }

private:
    std::mutex lock_;          // protect data
    std::string name_;         // fully qualified mailslot name
    HANDLE handle_ = nullptr;  // handle to the mailslot
    bool owner_ = false;       // true - we receive data, false - we send data

    std::atomic<bool> keep_running_ = true;  // thread flag
    std::unique_ptr<std::thread>
        main_thread_{};  // controlled by Construct/Dismantle
};
};  // namespace cma
