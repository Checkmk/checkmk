#include "stdafx.h"

#include "eventlog/eventlogvista.h"

#include <algorithm>
#include <cstdint>

#include "tools/_misc.h"
#include "wnx/logger.h"

/////////////////////////////////////////////////////////////
// Careful! All Evt-Functions have to be used through the
//          function pointers. The reason is possible crash
//          on incompatible(old) systems
/////////////////////////////////////////////////////////////
namespace cma::evl {

namespace win {
// This safe wrapper for Vista API when Vista API is not accessible(XP/2003)
class EvtFunctionMap {
public:
    explicit EvtFunctionMap();
    EvtFunctionMap(const EvtFunctionMap &) = delete;
    EvtFunctionMap &operator=(const EvtFunctionMap &) = delete;
    EvtFunctionMap(EvtFunctionMap &&) = delete;
    EvtFunctionMap &operator=(EvtFunctionMap &&) = delete;
    ~EvtFunctionMap();

    decltype(&EvtOpenLog) openLog;
    decltype(&EvtQuery) query;
    decltype(&EvtClose) close;
    decltype(&EvtSeek) seek;
    decltype(&EvtNext) next;
    decltype(&EvtCreateBookmark) createBookmark;
    decltype(&EvtUpdateBookmark) updateBookmark;
    decltype(&EvtCreateRenderContext) createRenderContext;
    decltype(&EvtRender) render;
    decltype(&EvtSubscribe) subscribe;
    decltype(&EvtFormatMessage) formatMessage;
    decltype(&EvtGetEventMetadataProperty) getEventMetadataProperty;
    decltype(&EvtOpenPublisherMetadata) openPublisherMetadata;
    decltype(&EvtGetLogInfo) getLogInfo;

    [[nodiscard]] bool ready() const noexcept {
        return module_handle_ != nullptr && openLog != nullptr &&
               close != nullptr;
    }

private:
    HMODULE module_handle_;
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

EvtFunctionMap g_evt;

[[nodiscard]] bool ObtainEventHandles(EVT_HANDLE subscription, DWORD count,
                                      PEVT_HANDLE events,
                                      DWORD &returned_num_events) noexcept {
    if (g_evt.next == nullptr) {
        return false;
    }
    return g_evt.next(subscription, count, events, INFINITE, 0,
                      &returned_num_events) == TRUE;
}

[[nodiscard]] EvtHandle NextEventHandle(EVT_HANDLE subscription) noexcept {
    if (g_evt.next == nullptr) {
        return nullptr;
    }
    EVT_HANDLE h{nullptr};
    DWORD num_events{0};
    if (g_evt.next(subscription, 1, &h, INFINITE, 0, &num_events) == TRUE) {
        return EvtHandle{h};
    }

    return nullptr;
}

void RenderValues(EVT_HANDLE context, EVT_HANDLE fragment,
                  std::vector<BYTE> &buffer) noexcept {
    if (g_evt.render == nullptr) {
        return;
    }
    DWORD required = 0;
    DWORD property_count = 0;
    g_evt.render(context, fragment, EvtRenderEventValues, 0, nullptr, &required,
                 &property_count);
    buffer.resize(required);
    g_evt.render(context, fragment, EvtRenderEventValues,
                 static_cast<DWORD>(buffer.size()), buffer.data(), &required,
                 &property_count);
}

[[nodiscard]] EVT_HANDLE CreateRenderContext() {
    if (g_evt.createRenderContext == nullptr) {
        XLOG::l("EvtCreateRenderContext function not found in wevtapi.dll");
        return nullptr;
    }

    std::vector fields{L"/Event/System/Provider/@Name",
                       L"/Event/System/EventID",
                       L"/Event/System/EventID/@Qualifiers",
                       L"/Event/System/EventRecordID",
                       L"/Event/System/Level",
                       L"/Event/System/TimeCreated/@SystemTime",
                       L"/Event/EventData/Data"};

    return g_evt.createRenderContext(static_cast<DWORD>(fields.size()),
                                     fields.data(), EvtRenderContextValues);
}

void EvtHandleClose(EVT_HANDLE handle) noexcept {
    if (g_evt.close == nullptr || handle == nullptr) {
        return;
    }
    g_evt.close(handle);
}

[[nodiscard]] EvtHandle OpenPublisherMetadata(
    const std::wstring_view source) noexcept {
    if (g_evt.openPublisherMetadata == nullptr) {
        XLOG::l("EvtOpenPublisherMetadata function not found in wevtapi.dll");
        return nullptr;
    }

    return EvtHandle{
        g_evt.openPublisherMetadata(nullptr, source.data(), nullptr, 0, 0)};
}

std::wstring FormatMessage(EVT_HANDLE publisher_meta, EVT_HANDLE event_handle) {
    if (g_evt.formatMessage == nullptr) {
        return {};
    }

    std::wstring result;
    result.resize(128);  //
    while (true) {
        DWORD required{0};
        if (g_evt.formatMessage(publisher_meta, event_handle, 0, 0, nullptr,
                                EvtFormatMessageEvent,
                                static_cast<DWORD>(result.size()),
                                result.data(), &required) == TRUE) {
            result.resize(required);
            break;
        }
        if (::GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
            result.resize(required);
        } else {
            return {};
        }
    }
    return result;
}

std::wstring RenderBookmark(EVT_HANDLE bookmark) {
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
                         buffer.data(), &required, &count) == TRUE) {
            buffer.resize(required);
            break;
        }

        if (::GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
            buffer.resize(required);
        } else {
            XLOG::l("failed to render bookmark");
            return {};
        }
    }

    return buffer;
}

[[nodiscard]] EvtHandle CreateLogHandle(EVT_QUERY_FLAGS flags,
                                        const std::wstring &path) {
    if (g_evt.query == nullptr) {
        XLOG::l("EvtQuery function not found in wevtapi.dll");
        return nullptr;
    }

    for (auto f : {EvtQueryChannelPath, EvtQueryFilePath}) {
        if (auto *handle = g_evt.query(nullptr, path.c_str(), L"*", flags | f);
            handle != nullptr) {
            return EvtHandle{handle};
        }
    }
    XLOG::l("failed to open log '{}'", wtools::ToUtf8(path));
    return nullptr;
}

[[nodiscard]] EvtHandle CreateBookmark(std::wstring_view text) {
    if (g_evt.createBookmark == nullptr) {
        XLOG::l.crit("g_evt is invalid, bookmark");
        return nullptr;
    }
    return EvtHandle{g_evt.createBookmark(text.data())};
}

[[nodiscard]] EvtHandle Subscribe(HANDLE event, std::wstring_view log_name,
                                  EVT_HANDLE bookmark) {
    if (g_evt.subscribe == nullptr) {
        XLOG::l.crit("g_evt is invalid subscribe");
        return nullptr;
    }

    return EvtHandle{g_evt.subscribe(nullptr, event, log_name.data(), L"*",
                                     bookmark, nullptr, nullptr,
                                     EvtSubscribeStartAfterBookmark)};
}

}  // namespace win

void EvtHandleDeleter::operator()(EVT_HANDLE h) const noexcept {
    if (h != nullptr) {
        win::EvtHandleClose(h);
    }
}

bool IsEvtApiAvailable() noexcept { return win::g_evt.ready(); }

class EventLogRecordVista final : public EventLogRecordBase {
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
        if (event_handle_ == nullptr) {
            XLOG::l("INVALID CALL: No more entries");
            return;
        }
        win::RenderValues(render_handle, event_handle_, buffer_);
    }

    enum Index {
        kSource = 0,
        kEventId = 1,
        kEventQualifiers = 2,
        kRecordId = 3,
        kLevel = 4,
        kTimeGenerated = 5

    };

    [[nodiscard]] const EVT_VARIANT &getValByType(int index) const {
        const auto *values =
            reinterpret_cast<const EVT_VARIANT *>(buffer_.data());

        return values[index];
    }

    [[nodiscard]] uint16_t eventId() const override {
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

    [[nodiscard]] uint16_t eventQualifiers() const override {
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

    [[nodiscard]] uint64_t recordId() const override {
        return getValByType(kRecordId).UInt64Val;
    }

    [[nodiscard]] time_t timeGenerated() const override {
        const auto val = getValByType(kTimeGenerated);
        const auto time_stamp = val.FileTimeVal;
        constexpr ULONGLONG time_offset = 116444736000000000ULL;
        return (time_stamp - time_offset) / 10000000;
    }

    [[nodiscard]] std::wstring source() const override {
        return getValByType(kSource).StringVal;
    }

    [[nodiscard]] Level eventLevel() const override {
        const auto val = getValByType(kLevel);
        const auto b = static_cast<WinEventLevel>(val.ByteVal);
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
        }
        // unreachable
        return Level::error;
    }

    [[nodiscard]] std::wstring makeMessage() const override {
        std::wstring result = formatMessage();
        postProcessMessage(result);
        return result;
    }

private:
    [[nodiscard]] std::wstring formatMessage() const {
        std::wstring result;
        auto publisher_meta = win::OpenPublisherMetadata(source());

        if (publisher_meta) {
            result = win::FormatMessage(publisher_meta.get(), event_handle_);
        } else {
            // can't read from the system, this may happen, ok
            XLOG::t("Open publishing meta fail [{}] '{}", ::GetLastError(),
                    wtools::ToUtf8(source()));
        }

        if (result.empty()) {
            // failed to resolve message -> use the data the caller stored
            result = eventData();
        }
        return result;
    }
    void postProcessMessage(std::wstring &result) const {
        // EvtFormatMessage delivers the formatted message with trailing
        // null character within the required buffer size! Later, this would
        // cause the socket output to be cut at the 1st null character, so
        // we need to trim trailing null away here.
        while (!result.empty() && result.back() == L'\0') {
            result.pop_back();
        }

        std::ranges::replace_if(
            result, [](auto ch) { return ch == L'\n' || ch == L'\r'; }, ' ');
    }

    // logic from 1.5
    [[nodiscard]] std::wstring eventData() const {
        constexpr size_t IDX = 6;  // six :)

        const auto *values =
            reinterpret_cast<const EVT_VARIANT *>(buffer_.data());
        const auto &event_data = values[IDX];
        if (event_data.Count == 0) {
            return {};
        }

        if ((event_data.Type & 128) != 0) {
            return collectMultiStr(event_data);
        }

        if (event_data.StringVal != nullptr) {
            return std::wstring{event_data.StringVal};
        }

        return {};
    }

    static std::wstring collectMultiStr(const EVT_VARIANT &event_data) {
        std::wstring result;
        for (unsigned int i = 0; i < event_data.Count; ++i) {
            const auto *str = event_data.StringArr[i];
            result += str == nullptr ? L"<null>" : str;
            result += L" ";
        }
        if (!result.empty()) {
            result.pop_back();
        }
        return result;
    }

    EVT_HANDLE event_handle_;
    std::vector<BYTE> buffer_;
};

namespace {
std::optional<int64_t> SeekPos(EVT_HANDLE render_context,
                               const std::wstring &log_name,
                               uint64_t record_id) {
    // The api to retrieve the oldest event log id is bugged. bloody hell...
    // to get the right offset if record_id is beyond the valid range, we
    // read one event from start or end
    // if there is none we assume there have never been events.
    // That is wrong of course but can't be helped. thanks a lot MS.
    EVT_QUERY_FLAGS flags = record_id == std::numeric_limits<uint64_t>::max()
                                ? EvtQueryReverseDirection
                                : EvtQueryForwardDirection;

    auto log = win::CreateLogHandle(flags, log_name);
    auto event = win::NextEventHandle(log.get());
    if (!event) {
        // We expect an ERROR_NO_MORE_ITEMS!
        // I've experienced a TIMEOUT_ERROR before, which totally broke the
        // record_id handling
        // Fixed it by setting the g_evt.next(..) timeout above to INFINITE
        // DWORD lastError = GetLastError();
        // std::cout << " GetLastError returned " << lastError << "." <<
        // std::endl;
        XLOG::t("Record [{}] not found in '{}'", record_id,
                wtools::ToUtf8(log_name));
        return {};
    }

    const EventLogRecordVista record(event.get(), render_context);
    if (record_id < record.recordId() ||
        record_id == std::numeric_limits<uint64_t>::max()) {
        record_id = record.recordId();
    } else {
        --record_id;
    }
    return record_id;
}

std::wstring MakeBookMarkXml(const std::wstring &log_name, int64_t record_id) {
    return std::wstring(L"<BookmarkList><Bookmark Channel='") + log_name +
           L"' RecordId='" + std::to_wstring(record_id) +
           L"' IsCurrent='true'/></BookmarkList>";
}

}  // namespace

EventLogVista::EventLogVista(const std::wstring &path)
    : log_name_(path), subscription_handle_(nullptr) {
    event_signal_ = ::CreateEvent(nullptr, TRUE, TRUE, nullptr);
    event_table_.reserve(EVENT_BLOCK_SIZE);
    render_context_.reset(win::CreateRenderContext());
}

EventLogVista::~EventLogVista() {
    if (event_signal_) {
        ::CloseHandle(event_signal_);
    }
    for (auto &h : event_table_) {
        win::EvtHandleClose(h);
    }
}

std::wstring EventLogVista::getName() const { return log_name_; }

void EventLogVista::seek(uint64_t record_id) {
    auto id = SeekPos(render_context_.get(), log_name_, record_id);
    if (!id.has_value()) {
        return;
    }

    std::wstring bookmark_xml = MakeBookMarkXml(log_name_, *id);
    auto bookmark_handle = win::CreateBookmark(bookmark_xml);

    subscription_handle_ =
        win::Subscribe(event_signal_, log_name_, bookmark_handle.get());

    if (!subscription_handle_) {
        XLOG::l("failed to subscribe to {}", wtools::ToUtf8(log_name_));
    }
}

bool EventLogVista::isNoMoreData() const noexcept {
    return index_in_table_ == event_table_.size() ||
           event_table_[index_in_table_] == nullptr;
}

EventLogRecordBase *EventLogVista::readRecord() {
    if (isNoMoreData() && !fillBuffer()) {
        return nullptr;
    }

    return new EventLogRecordVista(event_table_[index_in_table_++],
                                   render_context_.get());
}

// open/close to see what happens
bool EventLogVista::isLogValid() const {
    auto log = win::CreateLogHandle(EvtQueryReverseDirection, log_name_);
    return log.get() != nullptr;
}

uint64_t EventLogVista::getLastRecordId() {
    EvtHandle log{win::CreateLogHandle(EvtQueryReverseDirection, log_name_)};
    if (!log) {
        XLOG::d("getLastRecordId failed '{}'", wtools::ToUtf8(log_name_));
        return 0;
    }

    auto event = win::NextEventHandle(log.get());
    if (!event) {
        return 0;
    }

    EventLogRecordVista record(event.get(), render_context_.get());
    return record.recordId();
}

bool EventLogVista::fillBuffer() {
    // don't wait, just query the signal <-- this is damned polling, my friends
    if (!subscription_handle_) {
        return false;
    }
    if (WaitForSingleObject(event_signal_, 0) == WAIT_OBJECT_0) {
        resetData();
        return processEvents();
    }
    // we reach here if waiting for the signal would have blocked or
    // if the call to EvtNext reported no more errors
    ResetEvent(event_signal_);
    return false;
}

namespace {
struct EventTable {
    EVT_HANDLE events[EVENT_BLOCK_SIZE];
    DWORD num_events;
};

void LogProcessEventError(std::wstring_view log_name) {
    auto error = GetLastError();
    if (error != ERROR_NO_MORE_ITEMS) {
        XLOG::d("failed to enumerate events '{}' error = {}",
                wtools::ToUtf8(log_name), error);
    }
}

void CleanTable(std::vector<EVT_HANDLE> &event_table) noexcept {
    for (auto &h : event_table) {
        win::EvtHandleClose(h);
    }
    event_table.clear();
}

std::optional<EventTable> ReadEvents(EVT_HANDLE subscription_handle) {
    EventTable et;
    return win::ObtainEventHandles(subscription_handle, EVENT_BLOCK_SIZE,
                                   et.events, et.num_events)
               ? std::optional{et}
               : std::nullopt;
}
}  // namespace

bool EventLogVista::processEvents() {
    auto et = ReadEvents(subscription_handle_.get());
    if (!et.has_value()) {
        LogProcessEventError(log_name_);
        return false;
    }

    for (DWORD i = 0; i < et->num_events; ++i) {
        event_table_.push_back(et->events[i]);
    }

    return true;
}

void EventLogVista::resetData() {
    index_in_table_ = 0;
    CleanTable(event_table_);
}

}  // namespace cma::evl
