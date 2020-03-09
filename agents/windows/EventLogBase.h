// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef EventLogBase_h
#define EventLogBase_h

#include <memory>
#include <string>

class Logger;
class WinApiInterface;

class EventLogRecordBase {
public:
    enum class Level {
        Error,
        Warning,
        Information,
        AuditFailure,
        AuditSuccess,
        Success
    };

    EventLogRecordBase() = default;
    virtual ~EventLogRecordBase() = default;
    EventLogRecordBase(const EventLogRecordBase &) = delete;
    EventLogRecordBase &operator=(const EventLogRecordBase &) = delete;

    virtual uint64_t recordId() const = 0;
    virtual uint16_t eventId() const = 0;
    virtual uint16_t eventQualifiers() const = 0;
    virtual time_t timeGenerated() const = 0;
    virtual std::wstring source() const = 0;
    virtual Level level() const = 0;
    virtual std::wstring message() const = 0;
};

class EventLogBase {
public:
    EventLogBase() = default;
    virtual ~EventLogBase() = default;
    EventLogBase(const EventLogBase &) = delete;
    EventLogBase &operator=(const EventLogBase &) = delete;

    /**
     * return the name/path of the eventlog monitored
     **/
    virtual std::wstring getName() const = 0;

    /**
     * seek to the specified record on the next read or, if the record_number is
     * older than the oldest existing record, seek to the beginning. If the
     * record_number is the highest representable uint32_t, seek to the end of
     * the log such that only future events are retrieved
     *
     * WARNING:
     * The implementations for pre-Vista and post-Vista are completely
     * different.
     * We *must not* return any value as it is different between pre/post Vista.
     * For obtaining the ID of the last record in eventlog, please use
     * getLastRecordId instead. It has own implementations for pre/post Vista
     * but return a uniformly correct value.
     */
    virtual void seek(uint64_t record_id) = 0;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will be
     * quick most of the time but occasionally cause a fetch via api that takes
     * longer
     */
    virtual std::unique_ptr<EventLogRecordBase> read() = 0;

    /**
     * return the ID of the last record in eventlog
     */
    virtual uint64_t getLastRecordId() = 0;
};

std::unique_ptr<EventLogBase> open_eventlog(const std::wstring &name_or_path,
                                            bool try_vista_api, Logger *logger,
                                            const WinApiInterface &winapi);

#endif  // EventLogBase_h
