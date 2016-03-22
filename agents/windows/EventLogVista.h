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
#include "IEventLog.h"

// forward declaration
struct EvtFunctionMap;

class UnsupportedException : public std::exception {};

class EventLogVista : public IEventLog {
public:
    // constructor
    // This throws an UnsupportedException if the vista-api is not supported.
    EventLogVista(LPCWSTR path);

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
    std::wstring _path;
    HANDLE _handle;
    HANDLE _signal;
    // HANDLE _bookmark;
    HANDLE _render_context;
    EvtFunctionMap *_evt;
    std::vector<HANDLE> _events;
    size_t _next_event{0};
};

#endif  // EventLogVista_h
