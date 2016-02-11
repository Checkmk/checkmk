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


#ifndef EventLog_h
#define EventLog_h


#include <windows.h>
#include "types.h"
#include "stringutil.h"
#include "logging.h"

class EventLog {
public:
    /**
     * Construct a reader for the named eventlog
     */
    EventLog(LPCSTR name);

    ~EventLog();

    /**
     * return to reading from the beginning of the log
     */
    void reset();

    std::string getName() const;

    /**
     * seek to the specified record on the next read or, if the record_number is
     * older than the oldest existing record, seek to the beginning.
     * Note: there is a bug in the MS eventlog code that prevents seeking on
     * large eventlogs.
     * In this case this function will still work as expected but the next read
     * will be slow.
     */
    void seek(DWORD record_number);

    /**
     * read the next eventlog record
     * Note: records are retrieved from the api in chunks, so this read will be
     * quick most of the time but occasionally cause a fetch via api that takes
     * longer
     */
    EVENTLOGRECORD *read();

    /**
     * get a list of dlls that contain eventid->message mappings for this
     * eventlog and the specified source
     */
    std::vector<std::string> getMessageFiles(const char *source) const;

private:
    void open();

    void close();

    bool fillBuffer();

private:
    static const size_t INIT_BUFFER_SIZE = 64 * 1024;

    std::string _name;
    HANDLE _log;
    DWORD _record_offset{0};
    bool _seek_possible{true};
    std::vector<BYTE> _buffer;
    DWORD _buffer_offset{0};
    DWORD _buffer_used{0};
};

#endif // EventLog_h

