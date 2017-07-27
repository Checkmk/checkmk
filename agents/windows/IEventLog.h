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

#ifndef IEventLog_h
#define IEventLog_h

#include <memory>
#include <string>

class LoggerAdaptor;
class WinApiAdaptor;

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
     * the log such that only future events are retrieveda
     *
     * returns the actual record_id we seeked to, which may differ from the
     * input
     * if it was outside the available range
     */
    virtual uint64_t seek(uint64_t record_id) = 0;

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will be
     * quick most of the time but occasionally cause a fetch via api that takes
     * longer
     */
    virtual std::shared_ptr<IEventLogRecord> read() = 0;

    /**
     * get a list of dlls that contain eventid->message mappings for this
     * eventlog and the specified source
     */
    //    virtual std::vector<std::string> getMessageFiles(
    //        const char *source) const = 0;
};

std::unique_ptr<IEventLog> open_eventlog(const wchar_t *name_or_path,
                                         bool try_vista_api,
                                         const LoggerAdaptor &logger,
                                         const WinApiAdaptor &winapi);

#endif  // EventLog_h
