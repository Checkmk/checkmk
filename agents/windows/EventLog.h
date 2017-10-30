// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

#ifndef EventLog_h
#define EventLog_h

#include <map>
#include "IEventLog.h"
#include "stringutil.h"
#include "types.h"
#include "win_error.h"

class Logger;
class WinApiAdaptor;

typedef struct HINSTANCE__ *HMODULE;

class HModuleWrapper {
public:
    HModuleWrapper(HMODULE &hmodule, const WinApiAdaptor &winapi)
        : _hmodule(hmodule), _winapi(winapi) {}

    ~HModuleWrapper() { close(); }

    HModuleWrapper(const HModuleWrapper &) = delete;  // Delete copy constructor

    HModuleWrapper &operator=(const HModuleWrapper &) =
        delete;  // Delete assignment operator

    HModuleWrapper(HModuleWrapper &&from)
        : _hmodule(from._hmodule), _winapi(from._winapi) {  // Move constructor
        from._hmodule = nullptr;
    }

    HModuleWrapper &operator=(HModuleWrapper &&from) =
        delete;  // Move assignment operator

    //    HModuleWrapper &operator=(HModuleWrapper &&from) {              //
    //    Move assignment operator
    //        close();
    //        _hmodule = from._hmodule;
    //        from._hmodule = nullptr;
    //        return *this;
    //    }

    HMODULE getHModule() { return _hmodule; };

private:
    HMODULE _hmodule;
    const WinApiAdaptor &_winapi;

    void close();
};

class EventlogHandle {
public:
    EventlogHandle(const std::wstring &name, const WinApiAdaptor &winapi)
        : _name(name), _winapi(winapi), _handle(open()) {}

    ~EventlogHandle() { close(); }

    EventlogHandle(const EventlogHandle &logHandle) = delete;

    void reopen() {
        close();
        _handle = open();
    }

    bool ReadEventLogW(DWORD dwReadFlags, DWORD dwRecordOffset,
                       std::vector<BYTE> &buffer, DWORD *pnBytesRead,
                       DWORD *pnMinNumberOfBytesNeeded) const;
    DWORD GetOldestEventLogRecord(PDWORD record) const;
    DWORD GetNumberOfEventLogRecords(PDWORD record) const;

private:
    HANDLE open() const;

    void close() const;

private:
    std::wstring _name;
    const WinApiAdaptor &_winapi;
    HANDLE _handle;
};

class MessageResolver {
public:
    MessageResolver(const std::wstring &logName, Logger *logger,
                    const WinApiAdaptor &winapi)
        : _name(logName), _logger(logger), _winapi(winapi) {}

    std::wstring resolve(DWORD eventID, LPCWSTR source,
                         LPCWSTR *parameters) const;

private:
    std::vector<std::wstring> getMessageFiles(LPCWSTR source) const;
    std::wstring resolveInt(DWORD eventID, LPCWSTR dllpath,
                            LPCWSTR *parameters) const;

    std::wstring _name;
    mutable std::map<std::wstring, HModuleWrapper> _cache;
    Logger *_logger;
    const WinApiAdaptor &_winapi;
};

class EventLog : public IEventLog {
public:
    /**
     * Construct a reader for the named eventlog
     */
    EventLog(const std::wstring &name, Logger *logger,
             const WinApiAdaptor &winapi);

    virtual ~EventLog();

    /**
     * return to reading from the beginning of the log
     */
    virtual void reset() override;

    virtual std::wstring getName() const override;

    /**
     * seek to the specified record on the next read or, if the record_number is
     * older than the oldest existing record, seek to the beginning.
     * Note: there is a bug in the MS eventlog code that prevents seeking on
     * large eventlogs.
     * In this case this function will still work as expected but the next read
     * will be slow.
     */
    virtual void seek(uint64_t record_id) override;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will be
     * quick most of the time but occasionally cause a fetch via api that takes
     * longer
     */
    virtual std::unique_ptr<IEventLogRecord> read() override;

    /**
     * return the ID of the last record in eventlog
     */
    virtual uint64_t getLastRecordId() override;

    /**
     * get a list of dlls that contain eventid->message mappings for this
     * eventlog and the specified source
     */
    std::vector<std::string> getMessageFiles(const char *source) const;

private:
    bool fillBuffer();

private:
    static const size_t INIT_BUFFER_SIZE = 64 * 1024;

    std::wstring _name;
    EventlogHandle _log;
    DWORD _record_offset{0};
    bool _seek_possible{true};
    std::vector<BYTE> _buffer;
    DWORD _buffer_offset{0};
    DWORD _buffer_used{0};

    DWORD _last_record_read{0};

    const MessageResolver _resolver;
    Logger *_logger;
    const WinApiAdaptor &_winapi;
};

#endif  // EventLog_h
