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
    const EVT_HANDLE (*openLog)(EVT_HANDLE, LPCWSTR, DWORD);
    const EVT_HANDLE (*query)(EVT_HANDLE, LPCWSTR, LPCWSTR, DWORD);
    const WINBOOL (*close)(EVT_HANDLE);
    const WINBOOL (*seek)(EVT_HANDLE, LONGLONG, EVT_HANDLE, DWORD, DWORD);
    const WINBOOL (*next)(EVT_HANDLE, DWORD, EVT_HANDLE *, DWORD, DWORD,
                          PDWORD);
    const EVT_HANDLE (*createBookmark)(LPCWSTR);
    const WINBOOL (*updateBookmark)(EVT_HANDLE, EVT_HANDLE);
    const EVT_HANDLE (*createRenderContext)(DWORD, LPCWSTR *, DWORD);
    const WINBOOL (*render)(EVT_HANDLE, EVT_HANDLE, DWORD, DWORD, PVOID, PDWORD,
                            PDWORD);
    const EVT_HANDLE (*subscribe)(EVT_HANDLE, HANDLE, LPCWSTR, LPCWSTR,
                                  EVT_HANDLE, PVOID, EVT_SUBSCRIBE_CALLBACK,
                                  DWORD);
    const WINBOOL (*formatMessage)(EVT_HANDLE, EVT_HANDLE, DWORD, DWORD,
                                   PEVT_VARIANT, DWORD, DWORD, LPWSTR, PDWORD);
    const WINBOOL (*getEventMetadataProperty)(EVT_HANDLE,
                                              EVT_EVENT_METADATA_PROPERTY_ID,
                                              DWORD, DWORD, PEVT_VARIANT,
                                              PDWORD);
    const EVT_HANDLE (*openPublisherMetadata)(EVT_HANDLE, LPCWSTR, LPCWSTR,
                                              LCID, DWORD);
    const WINBOOL (*getLogInfo)(EVT_HANDLE, EVT_LOG_PROPERTY_ID, DWORD,
                                PEVT_VARIANT, PDWORD);
};

class ManagedEventHandle {
public:
    ManagedEventHandle(const EvtFunctionMap &evt, EVT_HANDLE handle)
        : _evt(evt), _handle(handle) {}

    ~ManagedEventHandle() {
        if (_handle && _evt.close) {
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
    const WinApiAdaptor &_winapi;

public:
    EventLogWrapper(const EvtFunctionMap &evt, EVT_QUERY_FLAGS flags,
                    const std::wstring &path, const WinApiAdaptor &winapi)
        : ManagedEventHandle(evt, create_log_handle(evt, flags, path))
        , _winapi(winapi) {}

private:
    EVT_HANDLE create_log_handle(const EvtFunctionMap &evt,
                                 EVT_QUERY_FLAGS flags,
                                 const std::wstring &path) {
        if (evt.query == nullptr) {
            throw win_exception(_winapi,
                                "EvtQuery function not found in wevtapi.dll");
        }

        EVT_HANDLE handle =
            evt.query(nullptr, path.c_str(), L"*", flags | EvtQueryChannelPath);

        if (handle == nullptr) {
            handle = evt.query(nullptr, path.c_str(), L"*",
                               flags | EvtQueryFilePath);
        }

        if (handle == nullptr) {
            throw win_exception(_winapi, "failed to open log");
        }
        return handle;
    }
};

class EventLogVista : public IEventLog {
public:
    // constructor
    // This throws an UnsupportedException if the vista-api is not supported.
    EventLogVista(const std::wstring &path, const WinApiAdaptor &winapi);

    EventLogVista(const EventLogVista &reference) = delete;

    virtual ~EventLogVista() noexcept;

    virtual std::wstring getName() const override;

    virtual void reset() override;

    virtual uint64_t seek(uint64_t record_id) override;

    virtual std::shared_ptr<IEventLogRecord> read() override;

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
    const WinApiAdaptor &_winapi;
};

#endif  // EventLogVista_h
