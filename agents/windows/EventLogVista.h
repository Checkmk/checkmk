// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// implements reading the eventlog with a newer api introduced in vista.
// This is required to read the "channels" introduce with vista

#ifndef EventLogVista_h
#define EventLogVista_h

// Windows Event Log API is available from Windows Vista
#undef _WIN32_WINNT
#define _WIN32_WINNT _WIN32_WINNT_VISTA
#include <winsock2.h>
#include <windows.h>
#include <winevt.h>
#include <exception>
#include <functional>
#include <string>
#include <vector>
#include "EventLogBase.h"
#include "types.h"
#include "win_error.h"

class UnsupportedException : public std::exception {};
class WinApiInterface;

class EventApiModule {
public:
    explicit EventApiModule(const WinApiInterface &winapi);

    ~EventApiModule();

    HMODULE get_module() { return _mod; }

private:
    HMODULE _mod;
    const WinApiInterface &_winapi;
};

struct EvtFunctionMap {
    explicit EvtFunctionMap(const WinApiInterface &winapi);

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

class EventLogVista : public EventLogBase {
    static const int EVENT_BLOCK_SIZE = 16;

public:
    // constructor
    // This throws an UnsupportedException if the vista-api is not supported.
    EventLogVista(const std::wstring &path, const WinApiInterface &winapi);

    virtual std::wstring getName() const override;

    virtual void seek(uint64_t record_id) override;

    virtual std::unique_ptr<EventLogRecordBase> read() override;

    virtual uint64_t getLastRecordId() override;

private:
    bool fillBuffer();
    std::wstring renderBookmark(HANDLE bookmark) const;

    const EvtFunctionMap _evt;
    std::wstring _path;
    const WinApiInterface &_winapi;
    EventHandleVista _handle;
    const EventHandleVista _render_context;
    WrappedHandle<NullHandleTraits> _signal;
    std::vector<EventHandleVista> _events;
    size_t _next_event{0};
};

#endif  // EventLogVista_h
