#include "stdafx.h"

#include "eventlogvista.h"

#include <algorithm>
#include <cstdint>

#include "logger.h"
#include "tools/_raii.h"

/////////////////////////////////////////////////////////////
// Careful! All Evt-Functions have to be used through the
//          function pointers. The reason is possible crash
//          on incompatible(old) systems
/////////////////////////////////////////////////////////////
namespace cma::evl {

EvtFunctionMap g_evt;

class EventLogRecordVista : public EventLogRecordBase {
    enum class WinEventLevel {
        Audit = 0,
        Critical = 1,
        Error = 2,
        Warning = 3,
        Information = 4,
        Verbose = 5
    };

public:
    // non-owning access to the Handles and this is DISASTER
    EventLogRecordVista(EVT_HANDLE event_handle, EVT_HANDLE render_handle)
        : event_handle_(event_handle) {
        if (g_evt.render == nullptr) {
            XLOG::l("EvtRender function not found in wevtapi.dll");
            return;
        }

        if (event_handle_ == nullptr) {
            XLOG::l("INVALID CALL: No more entries");
            return;
        }

        DWORD required = 0;
        DWORD property_count = 0;
        g_evt.render(render_handle, event_handle_, EvtRenderEventValues, 0,
                     nullptr, &required, &property_count);
        buffer_.resize(required);
        g_evt.render(render_handle, event_handle_, EvtRenderEventValues,
                     static_cast<DWORD>(buffer_.size()), &buffer_[0], &required,
                     &property_count);
    }

    static EVT_HANDLE createRenderContext() {
        if (g_evt.createRenderContext == nullptr) {
            XLOG::l("EvtCreateRenderContext function not found in wevtapi.dll");
            return nullptr;
        }

        std::vector<LPCWSTR> fields{L"/Event/System/Provider/@Name",
                                    L"/Event/System/EventID",
                                    L"/Event/System/EventID/@Qualifiers",
                                    L"/Event/System/EventRecordID",
                                    L"/Event/System/Level",
                                    L"/Event/System/TimeCreated/@SystemTime",
                                    L"/Event/EventData/Data"};

        return g_evt.createRenderContext(static_cast<DWORD>(fields.size()),
                                         &fields[0], EvtRenderContextValues);
    }

    enum Index {
        kSource = 0,
        kEventId = 1,
        kEventQualifiers = 2,
        kRecordId = 3,
        kLevel = 4,
        kTimeGenerated = 5

    };

    const EVT_VARIANT &getValByType(int index) const {
        const auto *values = reinterpret_cast<const EVT_VARIANT *>(&buffer_[0]);

        return values[index];
    }

    uint16_t eventId() const override {
        // I believe type is always UInt16 but since MS can't do documentation
        // I'm not sure
        auto val = getValByType(kEventId);
        switch (val.Type) {
            case EvtVarTypeUInt16:
                return val.UInt16Val;
            case EvtVarTypeUInt32:
                return static_cast<uint16_t>(val.UInt32Val);
            default:
                return static_cast<uint16_t>(val.UInt64Val);
        }
    }

    uint16_t eventQualifiers() const override {
        auto val = getValByType(kEventQualifiers);
        switch (val.Type) {
            case EvtVarTypeUInt16:
                return val.UInt16Val;
            case EvtVarTypeUInt32:
                return static_cast<uint16_t>(val.UInt32Val);
            default:
                return static_cast<uint16_t>(val.UInt64Val);
        }
    }

    uint64_t recordId() const override {
        return getValByType(kRecordId).UInt64Val;
    }

    time_t timeGenerated() const override {
        auto val = getValByType(kTimeGenerated);
        auto ullTimeStamp = val.FileTimeVal;
        constexpr ULONGLONG time_offset = 116444736000000000;
        return (ullTimeStamp - time_offset) / 10000000;
    }

    std::wstring source() const override {
        return getValByType(kSource).StringVal;
    }

    Level eventLevel() const override {
        auto val = getValByType(kLevel);
        auto b = static_cast<WinEventLevel>(val.ByteVal);
        switch (b) {
            case WinEventLevel::Error:
            case WinEventLevel::Critical:
                return Level::error;
            case WinEventLevel::Warning:
                return Level::warning;
            case WinEventLevel::Information:
                return Level::information;
            case WinEventLevel::Audit:
                return Level::audit_success;
            case WinEventLevel::Verbose:
                return Level::success;
            default:
                return Level::error;
        }
    }

    std::wstring makeMessage() const override {
        if (g_evt.formatMessage == nullptr) {
            XLOG::l("EvtFormatMessage function not found in wevtapi.dll");
            return L"bad_message 1";
        }

        if (g_evt.openPublisherMetadata == nullptr) {
            XLOG::l(
                "EvtOpenPublisherMetadata function not found in wevtapi.dll");
            return L"bad_message 2";
        }

        std::wstring result;
        result.resize(128);
        auto publisher_meta = g_evt.openPublisherMetadata(
            nullptr, source().c_str(), nullptr, 0, 0);

        if (publisher_meta) {
            ON_OUT_OF_SCOPE(g_evt.close(publisher_meta));
            while (true) {
                DWORD required{0};
                if (g_evt.formatMessage(publisher_meta, event_handle_, 0, 0,
                                        nullptr, EvtFormatMessageEvent,
                                        static_cast<DWORD>(result.size()),
                                        &result[0], &required) == TRUE) {
                    result.resize(required);
                    break;
                }

                if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
                    result.resize(required);
                } else {
                    result.resize(0);
                    break;
                }
            }
        } else {
            // can't read from the system, this may happen
            auto n = ::GetLastError();
            XLOG::t("open publishing meta error [{}] '{}", n,
                    wtools::ToUtf8(source().c_str()));
            result.resize(0);
        }

        if (result.empty()) {
            // failed to resolve message, just use the data the caller
            // stored
            result = eventData();
        }

        // EvtFormatMessage delivers the formatted message with trailing
        // null character within the required buffer size! Later, this would
        // cause the socket output to be cut at the 1st null character, so
        // we need to trim trailing null away here.
        while (!result.empty() && result.back() == L'\0') {
            result.pop_back();
        }

        std::ranges::replace_if(
            result, [](auto ch) { return ch == L'\n' || ch == L'\r'; }, ' ');
        return result;
    }

private:
    // ultra-legacy code from 1.5
    std::wstring eventData() const {
        const auto *values = reinterpret_cast<const EVT_VARIANT *>(&buffer_[0]);
        constexpr size_t IDX = 6;  // ??? what ???

        std::wstring result;

        if (values[IDX].Count > 0) {
            if ((values[IDX].Type & 128) != 0) {
                for (unsigned int i = 0; i < values[IDX].Count; ++i) {
                    if (i > 0) {
                        result += L" ";
                    }
                    if (values[IDX].StringArr[i] != nullptr) {
                        result += values[IDX].StringArr[i];
                    } else {
                        result += L"<null>";
                    }
                }
            } else if (values[IDX].StringVal != nullptr) {
                result = values[IDX].StringVal;
            }
        }
        return result;
    }

    EVT_HANDLE event_handle_;
    std::vector<BYTE> buffer_;
};

// Legacy code, I'm sorry.
#define GET_FUNC(func) \
    ((decltype(&func))::GetProcAddress(module_handle_, #func))

EvtFunctionMap::EvtFunctionMap() {
    module_handle_ = ::LoadLibraryW(L"wevtapi.dll");
    if (module_handle_ == nullptr) {
        XLOG::l("CRIT ERROR");
        return;
    }
    this->openLog = GET_FUNC(EvtOpenLog);
    this->query = GET_FUNC(EvtQuery);
    this->close = GET_FUNC(EvtClose);
    this->seek = GET_FUNC(EvtSeek);
    this->next = GET_FUNC(EvtNext);
    this->createBookmark = GET_FUNC(EvtCreateBookmark);
    this->updateBookmark = GET_FUNC(EvtUpdateBookmark);
    this->createRenderContext = GET_FUNC(EvtCreateRenderContext);
    this->render = GET_FUNC(EvtRender);
    this->subscribe = GET_FUNC(EvtSubscribe);
    this->formatMessage = GET_FUNC(EvtFormatMessage);
    this->getEventMetadataProperty = GET_FUNC(EvtGetEventMetadataProperty);
    this->openPublisherMetadata = GET_FUNC(EvtOpenPublisherMetadata);
    this->getLogInfo = GET_FUNC(EvtGetLogInfo);
}

EvtFunctionMap::~EvtFunctionMap() {
    if (module_handle_ != nullptr) {
        ::FreeLibrary(module_handle_);
    }
}

EventLogVista::EventLogVista(const std::wstring &path)
    : log_name_(path), subscription_handle_(nullptr) {
    event_signal_ = CreateEvent(nullptr, TRUE, TRUE, nullptr);
    event_table_.reserve(EVENT_BLOCK_SIZE);
    render_context_ = EventLogRecordVista::createRenderContext();
}

std::wstring EventLogVista::getName() const { return log_name_; }

std::wstring EventLogVista::renderBookmark(EVT_HANDLE bookmark) const {
    if (g_evt.render == nullptr) {
        return {};
    }

    std::wstring buffer;
    buffer.resize(64);

    DWORD required = 0;
    DWORD count = 0;

    while (true) {
        if (g_evt.render(nullptr, bookmark, EvtRenderBookmark,
                         static_cast<DWORD>(buffer.size() * sizeof(wchar_t)),
                         reinterpret_cast<void *>(&buffer[0]), &required,
                         &count) == TRUE) {
            buffer.resize(required);
            break;
        }

        if (GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
            buffer.resize(required);
        } else {
            XLOG::l("failed to render bookmark");
            return buffer;
        }
    }

    return buffer;
}

namespace {
EVT_HANDLE CreateLogHandle(EVT_QUERY_FLAGS flags, const std::wstring &path) {
    if (g_evt.query == nullptr) {
        XLOG::l("EvtQuery function not found in wevtapi.dll");
        return nullptr;
    }

    auto *handle =
        g_evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryChannelPath);

    if (handle != nullptr) {
        return handle;
    }

    handle = g_evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryFilePath);

    if (handle == nullptr) {
        XLOG::l("failed to open log '{}'", wtools::ToUtf8(path));
    }
    return handle;
}

}  // namespace

void EventLogVista::seek(uint64_t record_id) {
    if (g_evt.createBookmark == nullptr || g_evt.subscribe == nullptr) {
        XLOG::l.crit("g_evt is invalid");
        return;
    }

    {
        // The api to retrieve the oldest event log id is bugged. bloody hell...
        // to get the right offset if record_id is beyond the valid range, we
        // read one event from start or end
        // if there is none we assume there have never been events.
        // That is wrong of course but can't be helped. thanks a lot MS.

        EVT_QUERY_FLAGS flags =
            record_id == std::numeric_limits<uint64_t>::max()
                ? EvtQueryReverseDirection
                : EvtQueryForwardDirection;

        auto *log_handle = CreateLogHandle(flags, log_name_);
        ON_OUT_OF_SCOPE(if (log_handle) g_evt.close(log_handle));

        DWORD num_events = 0;
        if (g_evt.next != nullptr) {
            EVT_HANDLE event_handle = nullptr;
            g_evt.next(log_handle, 1, &event_handle, INFINITE, 0, &num_events);
            if (event_handle == nullptr) {
                XLOG::t("Record [{}] not found in '{}'", record_id,
                        wtools::ToUtf8(log_name_));
                return;
            }
            ON_OUT_OF_SCOPE(g_evt.close(event_handle));

            EventLogRecordVista record(event_handle, render_context_);
            if ((record_id < record.recordId()) ||
                (record_id == std::numeric_limits<uint64_t>::max())) {
                record_id = record.recordId();
            } else {
                --record_id;
            }
        } else {
            // We expect an ERROR_NO_MORE_ITEMS!
            // I've experienced a TIMEOUT_ERROR before, which totally broke the
            // record_id handling
            // Fixed it by setting the g_evt.next(..) timeout above to INFINITE
            // DWORD lastError = GetLastError();
            // std::cout << " GetLastError returned " << lastError << "." <<
            // std::endl;
            record_id = 0;
        }
    }

    std::wstring bookmark_xml =
        std::wstring(L"<BookmarkList><Bookmark Channel='") + log_name_ +
        L"' RecordId='" + std::to_wstring(record_id) +
        L"' IsCurrent='true'/></BookmarkList>";

    auto *bookmark_handle = g_evt.createBookmark(bookmark_xml.c_str());
    ON_OUT_OF_SCOPE(if (bookmark_handle) g_evt.close(bookmark_handle));

    if (subscription_handle_ != nullptr) {
        g_evt.close(subscription_handle_);
    }

    subscription_handle_ = g_evt.subscribe(
        nullptr, event_signal_, log_name_.c_str(), L"*", bookmark_handle,
        nullptr, nullptr, EvtSubscribeStartAfterBookmark);

    if (subscription_handle_ == nullptr) {
        XLOG::l("failed to subscribe to {}", wtools::ToUtf8(log_name_));
    }
}

EventLogRecordBase *EventLogVista::readRecord() {
    // rebuild event handle table
    if ((index_in_events_ == event_table_.size()) ||
        (event_table_[index_in_events_] == nullptr)) {
        if (!fillBuffer()) {
            return nullptr;
        }
    }

    return new EventLogRecordVista(event_table_[index_in_events_++],
                                   render_context_);
}

// open/close to see what happens
bool EventLogVista::isLogValid() const {
    auto *handle = CreateLogHandle(EvtQueryReverseDirection, log_name_);
    if (handle == nullptr) {
        return false;
    }
    g_evt.close(handle);
    return true;
}

uint64_t EventLogVista::getLastRecordId() {
    if (g_evt.next == nullptr || g_evt.close == nullptr) {
        XLOG::l("SHOT in the HEAD ERROR ERROR 1");
        return 0;
    }

    auto handle = CreateLogHandle(EvtQueryReverseDirection, log_name_);
    if (handle == nullptr) {
        XLOG::d("SHOT in the HEAD ERROR ERROR 2 '{}'",
                wtools::ToUtf8(log_name_));
        return 0;
    }
    ON_OUT_OF_SCOPE(if (handle != nullptr) { g_evt.close(handle); });

    EVT_HANDLE event_handle = nullptr;
    DWORD num_events = 0;
    if (g_evt.next(handle, 1, &event_handle, INFINITE, 0, &num_events) ==
        FALSE) {
        return 0;
    }

    ON_OUT_OF_SCOPE(g_evt.close(event_handle));

    EventLogRecordVista record(event_handle, render_context_);

    return record.recordId();
}

bool EventLogVista::fillBuffer() {
    // don't wait, just query the signal <-- this is damned polling, my friends
    if (subscription_handle_ == nullptr) {
        return false;
    }

    DWORD res = WaitForSingleObject(event_signal_, 0);
    if (res == WAIT_OBJECT_0) {
        EVT_HANDLE events[EVENT_BLOCK_SIZE];
        memset(events, 0, sizeof(events));

        DWORD num_events = 0;
        BOOL success = g_evt.next(subscription_handle_, EVENT_BLOCK_SIZE,
                                  events, INFINITE, 0, &num_events);
        if (success == FALSE) {
            auto error = GetLastError();
            if (error != ERROR_NO_MORE_ITEMS) {
                XLOG::d("failed to enumerate events '{}' error = {}",
                        wtools::ToUtf8(log_name_), error);
            }
            return false;
        }

        // clear() ensures all wrapped event handles are closed and nulled
        destroyEvents();
        // Wrap event handles -> they get closed when wrapper is destructed.
        for (auto &h : events) {
            event_table_.push_back(h);
        }
        index_in_events_ = 0;
        return true;
    }

    // we reach here if waiting for the signal would have blocked or
    // if the call to EvtNext reported no more errors
    ResetEvent(event_signal_);
    return false;
}
}  // namespace cma::evl
