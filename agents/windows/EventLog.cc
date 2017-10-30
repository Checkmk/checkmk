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
#include <windows.h>
#include <algorithm>
#include <map>
#include <string>

// loads a dll with support for environment variables in the path
HMODULE load_library_ext(LPCWSTR dllpath) {
    HMODULE dll = nullptr;

    // this should be sufficient most of the time
    static const size_t INIT_BUFFER_SIZE = 128;

    std::wstring dllpath_expanded;
    dllpath_expanded.resize(INIT_BUFFER_SIZE, '\0');
    DWORD required = ExpandEnvironmentStringsW(dllpath, &dllpath_expanded[0],
                                               dllpath_expanded.size());
    if (required > dllpath_expanded.size()) {
        dllpath_expanded.resize(required + 1);
        required = ExpandEnvironmentStringsW(dllpath, &dllpath_expanded[0],
                                             dllpath_expanded.size());
    } else if (required == 0) {
        dllpath_expanded = dllpath;
    }
    if (required != 0) {
        // required includes the zero terminator
        dllpath_expanded.resize(required - 1);
    }

    // load the library as a datafile without loading refernced dlls. This is
    // quicker but most of all it prevents problems if dependent dlls can't be
    // loaded.
    dll =
        LoadLibraryExW(dllpath_expanded.c_str(), nullptr,
                       DONT_RESOLVE_DLL_REFERENCES | LOAD_LIBRARY_AS_DATAFILE);
    return dll;
}

class MessageResolver {
    std::wstring _name;
    std::map<std::wstring, HModuleWrapper> _cache;

    std::vector<std::wstring> getMessageFiles(LPCWSTR source) const {
        static const std::wstring base =
            std::wstring(L"SYSTEM\\CurrentControlSet\\Services\\EventLog");
        std::wstring regpath = base + L"\\" + _name + L"\\" + source;

        HKEY key;
        DWORD ret = RegOpenKeyExW(HKEY_LOCAL_MACHINE, regpath.c_str(), 0,
                                  KEY_READ, &key);
        if (ret != ERROR_SUCCESS) {
            crash_log("failed to open HKLM:%ls", regpath.c_str());
            return std::vector<std::wstring>();
        }

        OnScopeExit close_key([&]() { RegCloseKey(key); });

        DWORD size = 64;
        std::vector<BYTE> buffer(size);
        // first try with fixed-size buffer
        DWORD res = ::RegQueryValueExW(key, L"EventMessageFile", nullptr,
                                       nullptr, &buffer[0], &size);
        if (res == ERROR_MORE_DATA) {
            buffer.resize(size);
            // actual read
            res = RegQueryValueExW(key, L"EventMessageFile", nullptr, nullptr,
                                   &buffer[0], &size);
        }
        if (res != ERROR_SUCCESS) {
            crash_log("failed to read at EventMessageFile in HKLM:%ls : %s",
                      regpath.c_str(), get_win_error_as_string(res).c_str());
            return std::vector<std::wstring>();
        }

        // result may be multiple dlls
        std::vector<std::wstring> result;
        std::wstringstream str(reinterpret_cast<wchar_t *>(&buffer[0]));
        std::wstring dll_path;
        while (std::getline(str, dll_path, L';')) {
            result.push_back(dll_path);
        }
        return result;
    }

    std::wstring resolveInt(DWORD eventID, LPCWSTR dllpath,
                            LPCWSTR *parameters) {
        HMODULE dll = nullptr;

        if (dllpath) {
            auto iter = _cache.find(dllpath);
            if (iter == _cache.end()) {
                dll = load_library_ext(dllpath);
                _cache.emplace(std::wstring(dllpath),
                               std::move(HModuleWrapper(dll)));
            } else {
                dll = iter->second.getHModule();
            }

            if (!dll) {
                crash_log("     --> failed to load %ls", dllpath);
                return L"";
            }
        } else {
            dll = nullptr;
        }

        std::wstring result;
        // maximum supported size
        result.resize(8192);

        DWORD dwFlags =
            FORMAT_MESSAGE_ARGUMENT_ARRAY | FORMAT_MESSAGE_FROM_SYSTEM;
        if (dll) dwFlags |= FORMAT_MESSAGE_FROM_HMODULE;

        crash_log("Event ID: %lu.%lu",
                  eventID / 65536,   // "Qualifiers": no idea what *that* is
                  eventID % 65536);  // the actual event id

        crash_log("Formatting Message");
        DWORD len =
            FormatMessageW(dwFlags, dll, eventID,
                           0,  // accept any language
                           &result[0], result.size(), (char **)parameters);
        crash_log("Formatting Message - DONE");

        // this trims the result string or empties it if formatting failed
        result.resize(len);
        return result;
    }

public:
    MessageResolver(const std::wstring &logName) : _name(logName) {}

    std::wstring resolve(DWORD eventID, LPCWSTR source, LPCWSTR *parameters) {
        std::wstring result;
        for (const std::wstring &dllpath : getMessageFiles(source)) {
            result = resolveInt(eventID, dllpath.c_str(), parameters);
            if (!result.empty()) {
                break;
            }
        }

        if (result.empty()) {
            // failed to resolve message, create an output_message
            // that simply concatenates all parameters
            for (int i = 0; parameters[i] != nullptr; ++i) {
                if (i > 0) {
                    result += L" ";
                }
                result += parameters[i];
            }
        }
        std::replace_if(result.begin(), result.end(),
                        [](wchar_t ch) { return ch == '\n' || ch == '\r'; },
                        ' ');
        return result;
    }
};

class EventLogRecord : public IEventLogRecord {
    EVENTLOGRECORD *_record;
    std::shared_ptr<MessageResolver> _resolver;

public:
    EventLogRecord(EVENTLOGRECORD *record,
                   const std::shared_ptr<MessageResolver> &resolver)
        : _record(record), _resolver(resolver) {}

    virtual uint64_t recordId() const override {
        return static_cast<uint64_t>(_record->RecordNumber);
    }

    virtual uint16_t eventId() const override {
        return _record->EventID % 65536;
    }

    virtual uint16_t eventQualifiers() const override {
        return _record->EventID / 65536;
    }

    virtual time_t timeGenerated() const override {
        return _record->TimeGenerated;
    }

    virtual std::wstring source() const override {
        return std::wstring(reinterpret_cast<LPCWSTR>(_record + 1));
    }

    virtual Level level() const override {
        switch (_record->EventType) {
            case EVENTLOG_ERROR_TYPE:
                return Level::Error;
            case EVENTLOG_WARNING_TYPE:
                return Level::Warning;
            case EVENTLOG_INFORMATION_TYPE:
                return Level::Information;
            case EVENTLOG_AUDIT_SUCCESS:
                return Level::AuditSuccess;
            case EVENTLOG_SUCCESS:
                return Level::Success;
            case EVENTLOG_AUDIT_FAILURE:
                return Level::AuditFailure;
            default:
                return Level::Error;
        }
    }

    virtual std::wstring message() const override {
        // prepare array of zero terminated strings to be inserted
        // into message template.
        std::vector<LPCWSTR> strings;
        LPCWSTR string = (WCHAR *)(((char *)_record) + _record->StringOffset);
        for (int i = 0; i < _record->NumStrings; ++i) {
            strings.push_back(string);
            string += wcslen(string) + 1;
        }
        // Sometimes the eventlog record does not provide
        // enough strings for the message template. Causes crash...
        // -> Fill the rest with empty strings
        strings.resize(63, L"");
        // end marker in array
        strings.push_back(nullptr);

        return _resolver->resolve(_record->EventID, source().c_str(),
                                  &strings[0]);
    }
};

EventLog::EventLog(LPCWSTR name)
    : _name(name), _log(name), _resolver(new MessageResolver(name)) {
    _buffer.resize(INIT_BUFFER_SIZE);
}

EventLog::~EventLog() {}

void EventLog::reset() {
    _log.reopen();
    _buffer_offset = _buffer_used;  // enforce that a new chunk is fetched
}

std::wstring EventLog::getName() const { return _name; }

void EventLog::seek(uint64_t record_number) {
    DWORD oldest_record, record_count;

    if (_log.GetOldestEventLogRecord(&oldest_record) &&
        (record_number < oldest_record)) {
        // Beyond the oldest record:
        _record_offset = oldest_record;
    } else if (_log.GetNumberOfEventLogRecords(&record_count) &&
               (record_number >= oldest_record + record_count)) {
        // Beyond the newest record. Note: set offset intentionally to the next
        // record after the currently last one!
        _record_offset = oldest_record + record_count;
    } else {
        // Within bounds, the offset for the next actual read:
        _record_offset = record_number;
    }
    _buffer_offset = _buffer_used;  // enforce that a new chunk is fetched
}

std::shared_ptr<IEventLogRecord> EventLog::read() {
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
    if (result != nullptr) {
        _last_record_read = result->RecordNumber;
        return std::shared_ptr<IEventLogRecord>(
            new EventLogRecord(result, _resolver));
    } else {
        return std::shared_ptr<IEventLogRecord>();
    }
}

uint64_t EventLog::getLastRecordId() {
    DWORD oldestRecord = 0;
    DWORD recordCount = 0;
    if (_log.GetOldestEventLogRecord(&oldestRecord) &&
        _log.GetNumberOfEventLogRecords(&recordCount) &&
        oldestRecord + recordCount > 0) {
        return oldestRecord + recordCount - 1;
    } else {
        return 0;
    }
}

bool EventLog::fillBuffer() {
    _buffer_offset = 0;

    // test if we're at the end of the log, as we don't get
    // a proper error message when reading beyond the last log record
    DWORD oldest_record, record_count;
    if (_log.GetOldestEventLogRecord(&oldest_record) &&
        _log.GetNumberOfEventLogRecords(&record_count)) {
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

    if (_log.ReadEventLogW(flags, _record_offset, _buffer, &_buffer_used,
                           &bytes_required)) {
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

        throw win_exception(
            std::string("Can't read eventlog ") + to_utf8(_name.c_str()),
            error);
    }
}
