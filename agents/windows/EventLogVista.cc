// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "EventLogVista.h"
#include <algorithm>
#include <cstdint>
#include "WinApiInterface.h"
#include "dynamic_func.h"
#include "stringutil.h"

/////////////////////////////////////////////////////////////
// Careful! All Evt-Functions have to be used through the
//          function pointers
/////////////////////////////////////////////////////////////

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
    EventLogRecordVista(EVT_HANDLE event, const EvtFunctionMap &evt,
                        EVT_HANDLE renderContext, const WinApiInterface &winapi)
        : _event(event), _evt(evt), _winapi(winapi) {
        DWORD required = 0;
        DWORD property_count = 0;

        if (_evt.render == nullptr)
            throw win_exception(_winapi,
                                "EvtRender function not found in wevtapi.dll");

        _evt.render(renderContext, _event, EvtRenderEventValues,
                    static_cast<DWORD>(_buffer.size()), &_buffer[0], &required,
                    &property_count);
        _buffer.resize(required);
        _evt.render(renderContext, _event, EvtRenderEventValues,
                    static_cast<DWORD>(_buffer.size()), &_buffer[0], &required,
                    &property_count);
    }

    static EVT_HANDLE createRenderContext(const WinApiInterface &winapi,
                                          const EvtFunctionMap &evt) {
        if (evt.createRenderContext == nullptr)
            throw win_exception(
                winapi,
                "EvtCreateRenderContext function not found in wevtapi.dll");

        std::vector<LPCWSTR> fields{L"/Event/System/Provider/@Name",
                                    L"/Event/System/EventID",
                                    L"/Event/System/EventID/@Qualifiers",
                                    L"/Event/System/EventRecordID",
                                    L"/Event/System/Level",
                                    L"/Event/System/TimeCreated/@SystemTime",
                                    L"/Event/EventData/Data"};

        return evt.createRenderContext(static_cast<DWORD>(fields.size()),
                                       &fields[0], EvtRenderContextValues);
    }

    virtual uint16_t eventId() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        // I believe type is always UInt16 but since MS can't do documentation
        // I'm not
        // sure
        switch (values[1].Type) {
            case EvtVarTypeUInt16:
                return values[1].UInt16Val;
            case EvtVarTypeUInt32:
                return static_cast<uint16_t>(values[1].UInt32Val);
            default:
                return static_cast<uint16_t>(values[1].UInt64Val);
        }
    }

    virtual uint16_t eventQualifiers() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        switch (values[2].Type) {
            case EvtVarTypeUInt16:
                return values[2].UInt16Val;
            case EvtVarTypeUInt32:
                return static_cast<uint16_t>(values[2].UInt32Val);
            default:
                return static_cast<uint16_t>(values[2].UInt64Val);
        }
    }

    virtual uint64_t recordId() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        return values[3].UInt64Val;
    }

    virtual time_t timeGenerated() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        ULONGLONG ullTimeStamp = values[5].FileTimeVal;
        static const ULONGLONG time_offset = 116444736000000000;
        return (ullTimeStamp - time_offset) / 10000000;
    }

    virtual std::wstring source() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        return values[0].StringVal;
    }

    virtual Level level() const override {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        switch (static_cast<WinEventLevel>(values[4].ByteVal)) {
            case WinEventLevel::Error:
            case WinEventLevel::Critical:
                return Level::Error;
            case WinEventLevel::Warning:
                return Level::Warning;
            case WinEventLevel::Information:
                return Level::Information;
            case WinEventLevel::Audit:
                return Level::AuditSuccess;
            case WinEventLevel::Verbose:
                return Level::Success;
            default:
                return Level::Error;
        }
    }

    virtual std::wstring message() const override {
        if (_evt.formatMessage == nullptr)
            throw win_exception(
                _winapi, "EvtFormatMessage function not found in wevtapi.dll");

        if (_evt.openPublisherMetadata == nullptr)
            throw win_exception(
                _winapi,
                "EvtOpenPublisherMetadata function not found in wevtapi.dll");

        std::wstring result;
        result.resize(128);
        EventHandleVista publisher_meta(
            _evt.openPublisherMetadata(nullptr, source().c_str(), nullptr, 0,
                                       0),
            _evt);
        if (publisher_meta.get() != nullptr) {
            for (;;) {
                DWORD required;
                if (_evt.formatMessage(publisher_meta.get(), _event, 0, 0,
                                       nullptr, EvtFormatMessageEvent,
                                       static_cast<DWORD>(result.size()),
                                       &result[0], &required)) {
                    result.resize(required);
                    break;
                } else if (_winapi.GetLastError() ==
                           ERROR_INSUFFICIENT_BUFFER) {
                    result.resize(required);
                } else {
                    result.resize(0);
                    break;
                }
            }
        } else {
            result.resize(0);
        }

        if (result.empty()) {
            // failed to resolve message, just use the data the caller stored
            result = eventData();
        }

        // EvtFormatMessage delivers the formatted message with trailing null
        // character within the required buffer size! Later, this would cause
        // the socket output to be cut at the 1st null character, so we need to
        // trim trailing null away here.
        while (!result.empty() && result.back() == L'\0') {
            result.pop_back();
        }

        std::replace_if(result.begin(), result.end(),
                        [](wchar_t ch) { return ch == L'\n' || ch == L'\r'; },
                        ' ');
        return result;
    }

private:
    std::wstring eventData() const {
        const EVT_VARIANT *values =
            reinterpret_cast<const EVT_VARIANT *>(&_buffer[0]);
        static const size_t IDX = 6;

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

    EVT_HANDLE _event;
    const EvtFunctionMap &_evt;
    std::vector<BYTE> _buffer;
    std::wstring _eventData;
    const WinApiInterface &_winapi;
};

EventApiModule::EventApiModule(const WinApiInterface &winapi)
    : _mod(winapi.LoadLibraryW(L"wevtapi.dll")), _winapi(winapi) {}

EventApiModule::~EventApiModule() {
    if (_mod != nullptr) {
        _winapi.FreeLibrary(_mod);
    }
}

#define GET_FUNC(func) \
    ((decltype(&func))winapi.GetProcAddress(_mod->get_module(), #func))

EvtFunctionMap::EvtFunctionMap(const WinApiInterface &winapi)
    : _mod(std::make_unique<EventApiModule>(winapi)) {
    if (_mod->get_module() == nullptr) {
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

EventLogVista::EventLogVista(const std::wstring &path,
                             const WinApiInterface &winapi)
    : _evt(winapi)
    , _path(path)
    , _winapi(winapi)
    , _handle(nullptr, _evt)
    , _render_context(EventLogRecordVista::createRenderContext(winapi, _evt),
                      _evt)
    , _signal(winapi.CreateEvent(nullptr, TRUE, TRUE, nullptr), winapi) {
    if (_evt.openLog == nullptr) {
        throw UnsupportedException();
    }

    if (_render_context.get() == nullptr) {
        throw win_exception(_winapi, "failed to create render context");
    }

    _events.reserve(EVENT_BLOCK_SIZE);
}

std::wstring EventLogVista::getName() const { return _path; }

std::wstring EventLogVista::renderBookmark(EVT_HANDLE bookmark) const {
    if (_evt.render == nullptr)
        throw win_exception(_winapi,
                            "EvtRender function not found in wevtapi.dll");

    std::wstring buffer;
    buffer.resize(64);

    DWORD required, count;

    for (;;) {
        if (_evt.render(nullptr, bookmark, EvtRenderBookmark,
                        static_cast<DWORD>(buffer.size() * sizeof(wchar_t)),
                        reinterpret_cast<void *>(&buffer[0]), &required,
                        &count)) {
            buffer.resize(required);
            break;
        } else if (_winapi.GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
            buffer.resize(required);
        } else {
            throw win_exception(_winapi, "failed to render bookmark");
        }
    }

    return buffer;
}

namespace {
EVT_HANDLE create_log_handle(const EvtFunctionMap &evt, EVT_QUERY_FLAGS flags,
                             const std::wstring &path,
                             const WinApiInterface &winapi) {
    if (evt.query == nullptr) {
        throw win_exception(winapi,
                            "EvtQuery function not found in wevtapi.dll");
    }

    EVT_HANDLE handle =
        evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryChannelPath);

    if (handle == nullptr) {
        handle =
            evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryFilePath);
    }

    if (handle == nullptr) {
        throw win_exception(winapi, "failed to open log");
    }
    return handle;
}

}  // namespace

void EventLogVista::seek(uint64_t record_id) {
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

        EventHandleVista logHandle(
            create_log_handle(_evt, flags, _path, _winapi), _evt);

        EVT_HANDLE event_handle;
        DWORD num_events = 0;
        auto nextFunc = _evt.next;
        const BOOL success = nextFunc
                                 ? nextFunc(logHandle.get(), 1, &event_handle,
                                            INFINITE, 0, &num_events)
                                 : false;

        if (success) {
            auto event = std::make_unique<EventHandleVista>(event_handle, _evt);

            EventLogRecordVista record(event->get(), _evt,
                                       _render_context.get(), _winapi);
            if ((record_id < record.recordId()) ||
                (record_id == std::numeric_limits<uint64_t>::max())) {
                record_id = record.recordId();
            } else
                record_id--;
        } else {
            // We expect an ERROR_NO_MORE_ITEMS!
            // I've experienced a TIMEOUT_ERROR before, which totally broke the
            // record_id handling
            // Fixed it by setting the _evt.next(..) timeout above to INFINITE
            // DWORD lastError = GetLastError();
            // std::cout << " GetLastError returned " << lastError << "." <<
            // std::endl;
            record_id = 0;
        }
    }

    std::wstring bookmarkXml =
        std::wstring(L"<BookmarkList><Bookmark Channel='") + _path +
        L"' RecordId='" + std::to_wstring(record_id) +
        L"' IsCurrent='true'/></BookmarkList>";

    if (_evt.createBookmark == nullptr)
        throw win_exception(
            _winapi, "EvtCreateBookmark function not found in wevtapi.dll");
    if (_evt.subscribe == nullptr)
        throw win_exception(_winapi,
                            "EvtSubscribe function not found in wevtapi.dll");
    EventHandleVista bookmark(_evt.createBookmark(bookmarkXml.c_str()), _evt);

    _handle =
        EventHandleVista(_evt.subscribe(nullptr, _signal.get(), _path.c_str(),
                                        L"*", bookmark.get(), nullptr, nullptr,
                                        EvtSubscribeStartAfterBookmark),
                         _evt);

    if (_handle.get() == nullptr) {
        throw win_exception(
            _winapi, std::string("failed to subscribe to ") + to_utf8(_path));
    }
}

std::unique_ptr<EventLogRecordBase> EventLogVista::read() {
    if ((_next_event == _events.size()) ||
        (_events[_next_event].get() == nullptr)) {
        if (!fillBuffer()) {
            return std::unique_ptr<EventLogRecordBase>();
        }
    }
    return std::make_unique<EventLogRecordVista>(
        _events[_next_event++].get(), _evt, _render_context.get(), _winapi);
}

uint64_t EventLogVista::getLastRecordId() {
    EventHandleVista logHandle(
        create_log_handle(_evt, EvtQueryReverseDirection, _path, _winapi),
        _evt);

    EVT_HANDLE event_handle = nullptr;
    DWORD num_events = 0;
    if (_evt.next && _evt.next(logHandle.get(), 1, &event_handle, INFINITE, 0,
                               &num_events)) {
        EventHandleVista event(event_handle, _evt);

        return EventLogRecordVista(event.get(), _evt, _render_context.get(),
                                   _winapi)
            .recordId();
    } else {
        return 0;
    }
}

bool EventLogVista::fillBuffer() {
    // don't wait, just query the signal
    DWORD res = _winapi.WaitForSingleObject(_signal.get(), 0);
    if (res == WAIT_OBJECT_0) {
        std::vector<EVT_HANDLE> rawEvents(EVENT_BLOCK_SIZE, nullptr);
        DWORD num_events = 0;
        BOOL success =
            _evt.next(_handle.get(), static_cast<DWORD>(rawEvents.size()),
                      rawEvents.data(), INFINITE, 0, &num_events);
        if (!success) {
            if (_winapi.GetLastError() != ERROR_NO_MORE_ITEMS) {
                throw win_exception(_winapi, "failed to enumerate events");
            } else {
                return false;
            }
        }

        // clear() ensures all wrapped event handles are closed and nulled
        _events.clear();
        // Wrap event handles -> they get closed when wrapper is destructed.
        std::transform(
            rawEvents.cbegin(), rawEvents.cend(), std::back_inserter(_events),
            [this](EVT_HANDLE e) { return EventHandleVista(e, _evt); });
        _next_event = 0;
        return true;
    }

    // we reach here if waiting for the signal would have blocked or
    // if the call to EvtNext reported no more errors
    _winapi.ResetEvent(_signal.get());
    return false;
}
