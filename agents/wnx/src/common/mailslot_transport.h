
// Perfect Mail Slot Transport
// by SK
// Usage example - see GreatExampleReceiverBegin, GreatExampleReceiverEnd and
// GreatExampleSender.

// Sender is using postman
// Receiver is using mailbox (with thread/callback)

#pragma once
#include <windows.h>

#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <strstream>
#include <thread>

#include "tools/_process.h"  // folders
#include "tools/_xlog.h"     // trace and log
#include "wtools.h"

// to be moved outside
namespace wtools {}  // namespace wtools

namespace cma {
class MailSlot;

constexpr bool kUsePublicProfileLog = true;  // to Profile(not to Windows)

constexpr const char* const kMailSlotLogFilePrivate =
    "\\Logs\\cmk_mail_log.log";
constexpr const char* const kMailSlotLogFileName = "cmk_mail.log";

inline bool IsMailApiTraced() { return false; }

// #TODO gtest
inline const std::string GetMailApiLog() {
    static std::string folder_path = "";
    if (0 == folder_path[0]) {
        if (kUsePublicProfileLog) {
            std::string public_folder_path =
                cma::tools::win::GetSomeSystemFolderA(FOLDERID_Public);
            if (!public_folder_path.empty()) {
                folder_path = public_folder_path + kMailSlotLogFileName;
            }
        } else {
            char win_path[256];
            auto len = GetWindowsDirectoryA(win_path, 256);
            if (len) {
                folder_path = win_path;
                folder_path += "\\Logs";
                folder_path += kMailSlotLogFileName;
            }
        }
    }
    return folder_path;
}

// This is Thread Callback definition
// Slot is a your slot, just to have
// Data & Len is self explanatory
// Context is parameter supplied by YOU, my friend when you creates mailbox,
// it may be nullptr or something important like an address of an object of
// a class to which callback should deliver data
typedef bool (*MailBoxThreadFoo)(const MailSlot* Slot, const void* Data,
                                 int Len, void* Context);

// const char* const MAIL_SLOT_PREFIX     = "\\\\.\\mailslot\\";
const char* const MAIL_SLOT_VCAST_SERVER =
    "nc_vcast_server";  // created inside service
const char* const kVCastMailSlotPrefix =
    "nc_vcast_client";  // created inside app
const int DEFAULT_THREAD_SLEEP = 20;
const char* const kUseThisNamePrefix =
    "^^^:";  // send to the hosting app with answer channel
const char* const kInternalTestString =
    "*test*";  // send to the hosting app with answer channel

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

private:
    MailSlot(const MailSlot&) {}
    MailSlot& operator=(const MailSlot&) {}

public:
    // convert slot name into fully qualified global object
    static std::string BuildMailSlotName(const char* Name, int Id,
                                         const char* PcName = ".") {
        std::string name = "\\\\";
        name += PcName;
        name += "\\mailslot\\Global\\";  // this work. ok. don't touch.
        name += Name;
        name += "_";
        name +=
            std::to_string(Id);  // session id or something unique you prefer
        return name;
    }

    MailSlot(const char* Name, int Id, const char* PcName = ".")
        : handle_(0)
        , owner_(false)
        , keep_running_(true)
        , main_thread_(nullptr) {
        name_ = BuildMailSlotName(Name, Id, PcName);
    }

    // with prepapred mail slot
    MailSlot(const char* Name)
        : handle_(0)
        , owner_(false)
        , keep_running_(true)
        , main_thread_(nullptr)
        , name_(Name)

    {}

    ~MailSlot() { Close(); }

    // API below

    // Accessors
    bool IsOwner() const {
        return owner_;
    }  // true, if mailslot had been "created", false if "opened"
    [[nodiscard]] bool IsPostman() const noexcept { return !owner_; }
    [[nodiscard]] const char* GetName() const noexcept { return name_.c_str(); }
    [[nodiscard]] HANDLE GetHandle() const noexcept { return handle_; }

    // mailbox start here
    bool ConstructThread(cma::MailBoxThreadFoo Foo, int SleepValue,
                         void* Context, bool ForceOpen,
                         wtools::SecurityLevel sl) {
        if (main_thread_) {
            xlog::l(IsMailApiTraced(), XLOG_FUNC + " Double call is forbidden")
                .filelog(GetMailApiLog());
            return false;
        }
        keep_running_ = true;
        if (ForceOpen) {
            // future use only or wil be removed
            for (int i = 0; i < 10; i++) {
                auto ret = Create(sl);
                if (ret) break;
                Close();
                using namespace std::chrono;
                std::this_thread::sleep_for(100ms);
            }
        } else
            while (!Create(sl)) {
                name_ += "x";
            }

        main_thread_ = std::make_unique<std::thread>(
            &MailSlot::MailBoxThread, this, Foo, SleepValue, Context);
        return true;
    }

    bool ConstructThread(cma::MailBoxThreadFoo foo, int sleep_ms, void* context,
                         wtools::SecurityLevel sl) {
        return ConstructThread(foo, sleep_ms, context, false, sl);
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
    bool ExecPost(const void* Data, uint64_t Length) {
        auto len = static_cast<int>(Length);
        if (!Data && len) {
            xlog::l(IsMailApiTraced(), "Bad data for \"%s\"posting %p %d",
                    name_.c_str(), Data, len)
                .filelog(GetMailApiLog());
            return false;
        }

        if (Open()) {
            auto ret = Post(Data, len);
            Close();
            return ret;
        } else {
            xlog::l(IsMailApiTraced(), "Can't open mail slot \"%s\"",
                    name_.c_str())
                .filelog(GetMailApiLog());
            return false;
        }
    }

    // returns false on duplicated name
    bool Create(wtools::SecurityLevel sl) {
        std::lock_guard<std::mutex> lck(lock_);

        if (handle_) return true;  // bad(already exists) call

        handle_ = createMailSlot(name_.c_str(), sl);

        if (handle_ == INVALID_HANDLE_VALUE) handle_ = nullptr;

        if (!handle_ && GetLastError() == 183)  // duplicated file name
        {
            xlog::l(IsMailApiTraced(),
                    "Duplicated OWN mail slot \"%s\" Retry with OPEN",
                    name_.c_str())
                .filelog(GetMailApiLog());
            return false;
        }

        auto ret = handle_ != nullptr;

        if (ret) {
            owner_ = true;  // we create -> we own
            xlog::l(IsMailApiTraced(), "OWN Mail slot \"%s\" was opened",
                    name_.c_str())
                .filelog(GetMailApiLog());
        } else {
            xlog::l(IsMailApiTraced(), "Fail open OWN mail slot \"%s\" %d",
                    name_.c_str(), GetLastError())
                .filelog(GetMailApiLog());
        }

        return true;
    }

    bool Open() {
        std::lock_guard<std::mutex> lck(lock_);

        if (handle_) return true;  // bad(already exists) call
        handle_ = openMailSlotWrite(name_.c_str());

        if (handle_ == INVALID_HANDLE_VALUE) {
            auto error = GetLastError();
            handle_ = nullptr;
            // please do not use printf - chrome host app communicates with
            // chrome via stdin/stdout making printf breaks communication
            // printf("Error %d opening file %s\n", error, name_.c_str());
            xlog::l(IsMailApiTraced(), "Fail open mail slot \"%s\" %d",
                    name_.c_str(), error)
                .filelog(GetMailApiLog());
        } else
            xlog::l(IsMailApiTraced(), "Mail slot \"%s\" was opened",
                    name_.c_str())
                .filelog(GetMailApiLog());

        return handle_ != nullptr;
    }

    bool Close() {
        std::lock_guard<std::mutex> lck(lock_);
        if (handle_) {
            auto ret = CloseHandle(handle_);
            if (!ret) {
                // if failed do not clean value
                auto error = GetLastError();
                xlog::l(IsMailApiTraced(), "Fail CLOSE mail slot \"%s\" %d",
                        name_.c_str(), error)
                    .filelog(GetMailApiLog());
            } else
                handle_ = nullptr;
        }
        return true;
    }

    bool Post(const void* Data, int Len) {
        std::lock_guard<std::mutex> lck(lock_);
        if (!handle_ || IsOwner()) {
            xlog::l(IsMailApiTraced(), "Bad situation %p %d", handle_,
                    (int)IsOwner())
                .filelog(GetMailApiLog());
            return false;
        }

        DWORD cbWritten = 0;
        auto fResult = WriteFile(handle_, Data, Len, &cbWritten, nullptr);

        if (0 == fResult) {
            xlog::l(IsMailApiTraced(), "Bad write %d", GetLastError())
                .filelog(GetMailApiLog());

            return false;
        }

        return true;
    }

    int Get(void* Data, unsigned int MaxLen) {
        std::lock_guard<std::mutex> lck(lock_);
        if (!handle_ || IsPostman()) return FAILED_INIT;
        auto hEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);
        if (nullptr == hEvent) {
            auto error = GetLastError();
            xlog::l(IsMailApiTraced(), "Failed Create Event with error %d",
                    error)
                .filelog(GetMailApiLog());

            return FAILED_CREATE;
        }
        ON_OUT_OF_SCOPE(CloseHandle(hEvent));

        OVERLAPPED ov = {0};
        ov.Offset = 0;
        ov.OffsetHigh = 0;
        ov.hEvent = hEvent;

        DWORD message_size = 0;
        DWORD message_count = 0;

        auto fResult = GetMailslotInfo(handle_,  // mailslot handle
                                       nullptr,  // no maximum message size
                                       &message_size,   // size of next message
                                       &message_count,  // number of messages
                                       nullptr);        // no read time-out

        if (!fResult) return ErrCodes::FAILED_INFO;

        if (message_size == MAILSLOT_NO_MESSAGE) return ErrCodes::SUCCESS;

        if (Data == nullptr) {
            return message_size;
        }

        if (MaxLen < message_size) return ErrCodes::TOO_SMALL;

        DWORD message_read = 0;
        fResult = ReadFile(handle_, Data, message_size, &message_read, &ov);

        if (fResult) return message_read;

        auto error = GetLastError();
        xlog::l(IsMailApiTraced(), "Failed read mail slot with error %d", error)
            .filelog(GetMailApiLog());

        return ErrCodes::FAILED_READ;
    }

    void MailBoxThread(cma::MailBoxThreadFoo Foo, int SleepValue,
                       void* Context) {
        int buffer_size = 16000;
        char* buffer = new char[buffer_size];
        while (keep_running_) {
            auto required_size = Get(nullptr, buffer_size);
            if (required_size > buffer_size) {
                delete[] buffer;
                buffer = new char[required_size];
                if (buffer) {
                    buffer_size = required_size;
                }
            }

            auto read_size = Get(buffer, buffer_size);
            if (read_size > 0) {
                Foo(this, buffer, read_size, Context);
            } else if (read_size < 0) {
            }

            Sleep(SleepValue > 0
                      ? SleepValue
                      : cma::DEFAULT_THREAD_SLEEP);  // we need sleep to
                                                     // prevent polling
        }
        delete[] buffer;
    }

    // typically called from the ::Open, to write data in
    static HANDLE openMailSlotWrite(const char* Name) {
        return CreateFileA(Name, GENERIC_WRITE, FILE_SHARE_READ, nullptr,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    }

    static HANDLE createMailSlot(const char* Name, wtools::SecurityLevel sl) {
        wtools::SecurityAttributeKeeper security_attribute_keeper(
            sl);  // black magic behind, do not try to
                  // understand, RAII auto-destroy
        auto sa = security_attribute_keeper.get();
        if (nullptr == sa) {
            xlog::l(IsMailApiTraced(), "Failed to create security descriptor")
                .filelog(GetMailApiLog());
            return INVALID_HANDLE_VALUE;
        }

        return CreateMailslotA(
            Name,                   // name
            0,                      // no maximum message size
            MAILSLOT_WAIT_FOREVER,  // no time-out for operations
            sa);                    // black magic resulted SECURITY_ATTRIBUTES
    }

private:
    std::mutex lock_;   // protect data
    std::string name_;  // fully qualified mailslot name
    HANDLE handle_;     // handle to the mailslot
    bool owner_;        // true - we receive data, false - we send data

    std::atomic<bool> keep_running_;  // thread flag
    std::unique_ptr<std::thread>
        main_thread_;  // thread itself, Controlled by Construct/Dismantle
};
};  // namespace cma
