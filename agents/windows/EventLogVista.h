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

// implements reading the eventlog with a newer api introduced in vista.
// This is required to read the "channels" introduce with vista

#ifndef EventLogVista_h
#define EventLogVista_h

#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#include <winsock2.h>
#include <windows.h>
#include <winevt.h>
#include <exception>
#include <functional>
#include <string>
#include <vector>
#include "IEventLog.h"
#include "types.h"
#include "win_error.h"

class UnsupportedException : public std::exception {};
class WinApiAdaptor;

class EventApiModule {
public:
    explicit EventApiModule(const WinApiAdaptor &winapi);

    ~EventApiModule();

    //    void *getAddress(const std::string& name) const { return
    //    GetProcAddress(_mod, name.c_str()); }
    HMODULE get_module() { return _mod; }

private:
    HMODULE _mod;
    const WinApiAdaptor &_winapi;
};

struct EvtFunctionMap {
    explicit EvtFunctionMap(const WinApiAdaptor &winapi);

    std::unique_ptr<EventApiModule> _mod;
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
};

struct EventHandleTraitsVista {
    using HandleT = EVT_HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const EvtFunctionMap &evt) {
        if (evt.close) {
            evt.close(value);
        }
    }
};

using EventHandleVista = WrappedHandle<EventHandleTraitsVista, EvtFunctionMap>;

class EventLogVista : public IEventLog {
    static const int EVENT_BLOCK_SIZE = 16;

public:
    // constructor
    // This throws an UnsupportedException if the vista-api is not supported.
    EventLogVista(const std::wstring &path, const WinApiAdaptor &winapi);

    virtual std::wstring getName() const override;

    virtual void seek(uint64_t record_id) override;

    virtual std::unique_ptr<IEventLogRecord> read() override;

    virtual uint64_t getLastRecordId() override;

private:
    bool fillBuffer();
    std::wstring renderBookmark(HANDLE bookmark) const;

    const EvtFunctionMap _evt;
    std::wstring _path;
    const WinApiAdaptor &_winapi;
    EventHandleVista _handle;
    const EventHandleVista _render_context;
    WrappedHandle<NullHandleTraits> _signal;
    std::vector<EventHandleVista> _events;
    size_t _next_event{0};
};

#endif  // EventLogVista_h
