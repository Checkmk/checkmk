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

#include <windows.h>
#include <exception>
#include <string>
#include <vector>
#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#include <winevt.h>
#include "IEventLog.h"
#include "types.h"

// forward declaration
class UnsupportedException : public std::exception {};

class EventApiModule {
public:
    EventApiModule() : _mod(LoadLibraryW(L"wevtapi.dll")){};

    ~EventApiModule() {
        if (_mod != nullptr) {
            FreeLibrary(_mod);
        }
    }

    //    void *getAddress(const std::string& name) const { return
    //    GetProcAddress(_mod, name.c_str()); }
    HMODULE get_module() { return _mod; }

private:
    HMODULE _mod;
};

struct EvtFunctionMap {
#define GET_FUNC(func) \
    ((decltype(&func))GetProcAddress(_mod->get_module(), #func))
    std::unique_ptr<EventApiModule> _mod;

    EvtFunctionMap() : _mod(std::make_unique<EventApiModule>()) {
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

class ManagedEventHandle {
public:
    ManagedEventHandle(const EvtFunctionMap &evt, EVT_HANDLE handle)
        : _evt(evt), _handle(handle) {}

    ~ManagedEventHandle() {
        if (_handle != nullptr) {
            _evt.close(_handle);
        }
    }

    EVT_HANDLE get_handle() { return _handle; };

private:
    const EvtFunctionMap &_evt;
    EVT_HANDLE _handle;

    // We own the handle, so don't allow any copies.
    ManagedEventHandle(const ManagedEventHandle &) = delete;
    ManagedEventHandle(ManagedEventHandle &&from) = delete;
    ManagedEventHandle &operator=(const ManagedEventHandle &) = delete;
    ManagedEventHandle &operator=(ManagedEventHandle &&from) = delete;
};

class EventLogWrapper : public ManagedEventHandle {
public:
    EventLogWrapper(const EvtFunctionMap &evt, EVT_QUERY_FLAGS flags,
                    const std::wstring &path)
        : ManagedEventHandle(evt, create_log_handle(evt, flags, path)) {}

private:
    EVT_HANDLE create_log_handle(const EvtFunctionMap &evt,
                                 EVT_QUERY_FLAGS flags,
                                 const std::wstring &path) {
        EVT_HANDLE handle =
            evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryChannelPath);

        if (handle == nullptr) {
            handle = evt.query(nullptr, path.c_str(), L"*",
                               flags | EvtQueryFilePath);
        }

        if (handle == nullptr) {
            throw win_exception("failed to open log");
        }
        return handle;
    }
};

class EventLogVista : public IEventLog {
public:
    // constructor
    // This throws an UnsupportedException if the vista-api is not supported.
    EventLogVista(LPCWSTR path);

    EventLogVista(const EventLogVista &reference) = delete;

    virtual ~EventLogVista() noexcept;

    virtual std::wstring getName() const override;

    virtual void reset() override;

    virtual void seek(uint64_t record_id) override;

    virtual std::shared_ptr<IEventLogRecord> read() override;

    virtual uint64_t getLastRecordId() override;

private:
    static const int EVENT_BLOCK_SIZE = 16;

    EvtFunctionMap &evt() const;
    bool fillBuffer();

    std::wstring renderBookmark(HANDLE bookmark) const;

private:
    std::shared_ptr<EvtFunctionMap> _evt;
    std::wstring _path;
    std::unique_ptr<ManagedEventHandle> _handle;
    std::unique_ptr<ManagedEventHandle> _render_context;
    std::unique_ptr<ManagedHandle> _signal;
    // HANDLE _bookmark;
    std::vector<HANDLE> _events;
    size_t _next_event{0};
};

#endif  // EventLogVista_h
