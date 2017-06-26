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
#include "dynamic_func.h"
#include "stringutil.h"
#include "types.h"
#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#include <winevt.h>

/////////////////////////////////////////////////////////////
// Careful! All Evt-Functions have to be used through the
//          function pointers
/////////////////////////////////////////////////////////////

class EventLogRecordVista : public IEventLogRecord {
    EVT_HANDLE _event;
    EvtFunctionMap *_evt;
    std::vector<BYTE> _buffer;
    std::wstring _eventData;

    enum WinEventLevel {
        Audit = 0,
        Critical = 1,
        Error = 2,
        Warning = 3,
        Information = 4,
        Verbose = 5
    };

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

public:
    EventLogRecordVista(EVT_HANDLE event, EvtFunctionMap *evt,
                        EVT_HANDLE renderContext)
        : _event(event), _evt(evt) {
        DWORD required = 0;
        DWORD property_count = 0;
        _evt->render(renderContext, _event, EvtRenderEventValues,
                     _buffer.size(), &_buffer[0], &required, &property_count);
        _buffer.resize(required);
        _evt->render(renderContext, _event, EvtRenderEventValues,
                     _buffer.size(), &_buffer[0], &required, &property_count);
    }

    static EVT_HANDLE createRenderContext(EvtFunctionMap &evt) {
        std::vector<LPCWSTR> fields{L"/Event/System/Provider/@Name",
                                    L"/Event/System/EventID",
                                    L"/Event/System/EventID/@Qualifiers",
                                    L"/Event/System/EventRecordID",
                                    L"/Event/System/Level",
                                    L"/Event/System/TimeCreated/@SystemTime",
                                    L"/Event/EventData/Data"};

        return evt.createRenderContext(fields.size(), &fields[0],
                                       EvtRenderContextValues);
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
        switch (values[4].ByteVal) {
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
        std::wstring result;
        result.resize(128);
        auto publisher_meta = std::make_unique<ManagedEventHandle>(
            *_evt,
            _evt->openPublisherMetadata(nullptr, source().c_str(), nullptr, 0,
                                        0));
        if (publisher_meta->get_handle() != nullptr) {
            for (;;) {
                DWORD required;
                if (_evt->formatMessage(publisher_meta->get_handle(), _event, 0,
                                        0, nullptr, EvtFormatMessageEvent,
                                        result.size(), &result[0], &required)) {
                    result.resize(required);
                    break;
                } else if (::GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
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

        std::replace_if(result.begin(), result.end(),
                        [](wchar_t ch) { return ch == '\n' || ch == '\r'; },
                        ' ');
        return result;
    }
};

EventLogVista::EventLogVista(LPCWSTR path) : _path(path), _handle(nullptr) {
    _evt = std::make_shared<EvtFunctionMap>();
    if (_evt->openLog == nullptr) {
        throw UnsupportedException();
    }

    _signal = std::make_unique<ManagedHandle>(
        CreateEvent(nullptr, TRUE, TRUE, nullptr));

    _render_context = std::make_unique<ManagedEventHandle>(
        *_evt, EventLogRecordVista::createRenderContext(*_evt));

    if (_render_context->get_handle() == nullptr) {
        throw win_exception("failed to create render context");
    }

    reset();
}

EventLogVista::~EventLogVista() noexcept { reset(); }

EvtFunctionMap &EventLogVista::evt() const { return *_evt; }

std::wstring EventLogVista::getName() const { return _path; }

void EventLogVista::reset() {
    for (HANDLE event : _events) {
        evt().close(event);
    }
    _next_event = 0;
    _events.resize(0);
    _events.resize(EVENT_BLOCK_SIZE, nullptr);
}

std::wstring EventLogVista::renderBookmark(EVT_HANDLE bookmark) const {
    std::wstring buffer;
    buffer.resize(64);

    DWORD required, count;

    for (;;) {
        if (evt().render(nullptr, bookmark, EvtRenderBookmark,
                         buffer.size() * sizeof(wchar_t),
                         reinterpret_cast<void *>(&buffer[0]), &required,
                         &count)) {
            buffer.resize(required);
            break;
        } else if (::GetLastError() == ERROR_INSUFFICIENT_BUFFER) {
            buffer.resize(required);
        } else {
            throw win_exception("failed to render bookmark");
        }
    }

    return buffer;
}

uint64_t EventLogVista::seek(uint64_t record_id) {
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

        auto log = std::make_unique<EventLogWrapper>(*_evt, flags, _path);

        EVT_HANDLE event_handle;
        DWORD num_events = 0;
        BOOL success = evt().next(log->get_handle(), 1, &event_handle, INFINITE,
                                  0, &num_events);

        if (success) {
            auto event =
                std::make_unique<ManagedEventHandle>(*_evt, event_handle);

            EventLogRecordVista record(event->get_handle(), _evt.get(),
                                       _render_context->get_handle());
            if ((record_id < record.recordId()) ||
                (record_id == std::numeric_limits<uint64_t>::max())) {
                record_id = record.recordId();
            } else
                record_id--;
        } else {
            // We expect an ERROR_NO_MORE_ITEMS!
            // I've experienced a TIMEOUT_ERROR before, which totally broke the
            // record_id handling
            // Fixed it by setting the evt().next(..) timeout above to INFINITE
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

    std::unique_ptr<ManagedEventHandle> bookmark =
        std::make_unique<ManagedEventHandle>(
            *_evt, evt().createBookmark(bookmarkXml.c_str()));

    _handle = std::make_unique<ManagedEventHandle>(
        *_evt,
        evt().subscribe(nullptr, _signal->get_handle(), _path.c_str(), L"*",
                        bookmark->get_handle(), nullptr, nullptr,
                        EvtSubscribeStartAfterBookmark));

    if (_handle->get_handle() == nullptr) {
        throw win_exception(
            (std::string("failed to subscribe to ") + to_utf8(_path.c_str()))
                .c_str());
    }

    return record_id;
}

std::shared_ptr<IEventLogRecord> EventLogVista::read() {
    if ((_next_event == _events.size()) || (_events[_next_event] == nullptr)) {
        if (!fillBuffer()) {
            return std::shared_ptr<IEventLogRecord>();
        }
    }
    return std::make_shared<EventLogRecordVista>(
        _events[_next_event++], _evt.get(), _render_context->get_handle());
}

bool EventLogVista::fillBuffer() {
    // this ensures all previous event handles are closed and nulled
    reset();
    // don't wait, just query the signal
    DWORD res = ::WaitForSingleObject(_signal->get_handle(), 0);
    if (res == WAIT_OBJECT_0) {
        DWORD num_events = 0;
        BOOL success = evt().next(_handle->get_handle(), _events.size(),
                                  &_events[0], INFINITE, 0, &num_events);
        if (!success) {
            if (::GetLastError() != ERROR_NO_MORE_ITEMS) {
                throw win_exception("failed to enumerate events");
            } else {
                return false;
            }
        }

        _next_event = 0;
        return true;
    }

    // we reach here if waiting for the signal would have blocked or
    // if the call to EvtNext reported no more errors
    ::ResetEvent(_signal->get_handle());
    return false;
}
