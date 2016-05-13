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


#include "EventLog.h"


EventLog::EventLog(LPCSTR name) : _name(name) {
    open();
    _buffer.resize(INIT_BUFFER_SIZE);
}

EventLog::~EventLog() { close(); }

void EventLog::reset() {
    close();
    open();
}

std::string EventLog::getName() const { return _name; }

void EventLog::seek(DWORD record_number) {
    DWORD oldest_record;
    if (::GetOldestEventLogRecord(_log, &oldest_record) &&
        (record_number < oldest_record)) {
        // can't seek to older record
        _record_offset = oldest_record;
    } else {
        // not actually seeking but storing for the next actual read
        _record_offset = record_number;
    }
    _buffer_offset = _buffer_used; // enforce that a new chunk is fetched
}

EVENTLOGRECORD *EventLog::read() {
    EVENTLOGRECORD *result = nullptr;
    while (result == nullptr) {
        while (_buffer_offset < _buffer_used) {
            EVENTLOGRECORD *temp =
                reinterpret_cast<EVENTLOGRECORD *>(&(_buffer[_buffer_offset]));
            _buffer_offset += temp->Length;
            // as long as seeking on this event log is possible this will
            // always be true.
            // otherwise this skips events we want to move past
            if (temp->RecordNumber >= _record_offset) {
                _record_offset = 0;  // don't need to keep the offset after
                                     // we moved past it
                result = temp;
                break;
            }
        }

        if (result == nullptr) {
            // no fitting record in our buffer, get the next couple of
            // records
            if (!fillBuffer()) {
                // no more events to read, break out of the loop
                break;
            }
        }
    }
    return result;
}

std::vector<std::string> EventLog::getMessageFiles(const char *source) const {
    static const std::string base =
        std::string("SYSTEM\\CurrentControlSet\\Services\\EventLog");
    std::string regpath = base + "\\" + _name + "\\" + source;

    HKEY key;
    DWORD ret =
        RegOpenKeyExA(HKEY_LOCAL_MACHINE, regpath.c_str(), 0, KEY_READ, &key);
    if (ret != ERROR_SUCCESS) {
        crash_log("failed to open HKLM:%s\n", regpath.c_str());
        return std::vector<std::string>();
    }

    OnScopeExit close_key([&]() { RegCloseKey(key); });

    DWORD size = 64;
    std::vector<BYTE> buffer(size);
    // first try with fixed-size buffer
    DWORD res = ::RegQueryValueExW(key, L"EventMessageFile", nullptr, nullptr,
                                   &buffer[0], &size);
    if (res == ERROR_MORE_DATA) {
        buffer.resize(size);
        // actual read
        res = RegQueryValueExW(key, L"EventMessageFile", nullptr, nullptr,
                               &buffer[0], &size);
    }
    if (res != ERROR_SUCCESS) {
        crash_log("failed to read at EventMessageFile in HKLM:%s : %s\n",
                  regpath.c_str(), get_win_error_as_string(res).c_str());
        return std::vector<std::string>();
    }

    // result may be multiple dlls
    std::vector<std::string> result;
    std::stringstream str(to_utf8((wchar_t *)&buffer[0]));
    std::string dll_path;
    while (std::getline(str, dll_path, ';')) {
        result.push_back(dll_path);
    }
    return result;
}

void EventLog::open() {
    if ((_log = OpenEventLogA(nullptr, _name.c_str())) == nullptr) {
        throw win_exception(std::string("failed to open eventlog: ") + _name);
    }

    _buffer_offset = _buffer_used; // enforce that a new chunk is fetched
}

void EventLog::close() { CloseEventLog(_log); }

bool EventLog::fillBuffer() {
    _buffer_offset = 0;

    // test if we're at the end of the log, as we don't get
    // a proper error message when reading beyond the last log record
    DWORD oldest_record, record_count;
    if (::GetOldestEventLogRecord(_log, &oldest_record) &&
        ::GetNumberOfEventLogRecords(_log, &record_count)) {
        if (_record_offset >= oldest_record + record_count) {
            return false;
        }
    }

    DWORD flags = EVENTLOG_FORWARDS_READ;
    if ((_record_offset != 0) && (_seek_possible)) {
        flags |= EVENTLOG_SEEK_READ;
    } else {
        flags |= EVENTLOG_SEQUENTIAL_READ;
    }

    crash_log("    . seek to %lu", _record_offset);

    DWORD bytes_required;

    if (ReadEventLogW(_log, flags, _record_offset,
                      static_cast<void *>(&_buffer[0]), _buffer.size(),
                      &_buffer_used, &bytes_required)) {
        return true;
    } else {
        DWORD error = GetLastError();
        if (error == ERROR_HANDLE_EOF) {
            // end of log, all good
            return false;
        } else if (error == ERROR_INSUFFICIENT_BUFFER) {
            // resize buffer and recurse
            _buffer.resize(bytes_required);
            return fillBuffer();
        } else if (error == ERROR_INVALID_PARAMETER) {
            if ((flags & EVENTLOG_SEEK_READ) == EVENTLOG_SEEK_READ) {
                // the most likely cause for this error (since our
                // parameters are good) is the following bug:
                // https://support.microsoft.com/en-us/kb/177199
                _seek_possible = false;
                return fillBuffer();
            }  // otherwise treat this like any other error
        }

        throw win_exception(std::string("Can't read eventlog ") + _name, error);
    }
}

