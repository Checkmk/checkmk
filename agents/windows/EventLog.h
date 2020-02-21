// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef EventLog_h
#define EventLog_h

#include <map>
#include "EventLogBase.h"
#include "stringutil.h"
#include "types.h"
#include "win_error.h"

class Logger;
class WinApiInterface;

class MessageResolver {
public:
    MessageResolver(const std::wstring &logName, Logger *logger,
                    const WinApiInterface &winapi)
        : _name(logName), _logger(logger), _winapi(winapi) {}
    MessageResolver(const MessageResolver &) = delete;
    MessageResolver &operator=(const MessageResolver &) = delete;

    std::wstring resolve(DWORD eventID, LPCWSTR source,
                         LPCWSTR *parameters) const;

private:
    std::vector<std::wstring> getMessageFiles(LPCWSTR source) const;
    std::wstring resolveInt(DWORD eventID, LPCWSTR dllpath,
                            LPCWSTR *parameters) const;

    std::wstring _name;
    mutable std::map<std::wstring, HModuleHandle> _cache;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

struct EventHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return nullptr; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        winapi.CloseEventLog(value);
    }
};

using EventHandle = WrappedHandle<EventHandleTraits>;

class EventLog : public EventLogBase {
    static const size_t INIT_BUFFER_SIZE = 64 * 1024;

public:
    /**
     * Construct a reader for the named eventlog
     */
    EventLog(const std::wstring &name, Logger *logger,
             const WinApiInterface &winapi);

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
    virtual std::unique_ptr<EventLogRecordBase> read() override;

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

    std::wstring _name;
    EventHandle _handle;
    DWORD _record_offset{0};
    bool _seek_possible{true};
    std::vector<BYTE> _buffer;
    DWORD _buffer_offset{0};
    DWORD _buffer_used{0};
    DWORD _last_record_read{0};

    const MessageResolver _resolver;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

#endif  // EventLog_h
