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

#ifndef IEventLog_h
#define IEventLog_h

#include <memory>
#include <string>

class IEventLogRecord {
public:
    enum class Level {
        Error,
        Warning,
        Information,
        AuditFailure,
        AuditSuccess,
        Success
    };

public:
    virtual uint64_t recordId() const = 0;
    virtual uint16_t eventId() const = 0;
    virtual uint16_t eventQualifiers() const = 0;
    virtual time_t timeGenerated() const = 0;
    virtual std::wstring source() const = 0;
    virtual Level level() const = 0;
    virtual std::wstring message() const = 0;
};

class IEventLog {
public:
    virtual ~IEventLog() {}

    /**
     * return to reading from the beginning of the log
     */
    virtual void reset() = 0;

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
    virtual std::shared_ptr<IEventLogRecord> read() = 0;

    /**
     * return the ID of the last record in eventlog
     */
    virtual uint64_t getLastRecordId() = 0;

    /**
     * get a list of dlls that contain eventid->message mappings for this
     * eventlog and the specified source
     */
    //    virtual std::vector<std::string> getMessageFiles(
    //        const char *source) const = 0;
};

std::unique_ptr<IEventLog> open_eventlog(const wchar_t *name_or_path,
                                         bool try_vista_api);

#endif  // EventLog_h
