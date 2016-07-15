// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#ifndef Renderer_h
#define Renderer_h

#include "config.h"  // IWYU pragma: keep
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include "OutputBuffer.h"
#include "global_counters.h"

enum class OutputFormat { csv, json, python };

class Renderer {
public:
    Renderer(OutputBuffer *output, OutputBuffer::ResponseHeader response_header,
             bool do_keep_alive, std::string invalid_header_message,
             OutputFormat format, std::string field_separator,
             std::string dataset_separator, std::string list_separator,
             std::string host_service_separator, int timezone_offset);

    void setError(OutputBuffer::ResponseCode code, const std::string &message);
    std::size_t size() const;

    void add(const std::string &str);
    void add(const std::vector<char> &blob);

    void startOfQuery();
    void outputDataSetSeparator();
    void endOfQuery();

    void outputDatasetBegin();
    void outputDatasetEnd();
    void outputFieldSeparator();
    void outputInteger(int32_t value);
    void outputInteger64(int64_t value);
    void outputTime(int32_t value);
    void outputUnsignedLong(unsigned long value);
    void outputCounter(counter_t value);
    void outputDouble(double value);
    void outputNull();
    void outputAsciiEscape(char value);
    void outputUnicodeEscape(unsigned value);
    void outputBlob(const std::vector<char> *blob);
    void outputString(const char *value, int len = -1);
    void outputBeginList();
    void outputListSeparator();
    void outputEndList();
    void outputBeginSublist();
    void outputSublistSeparator();
    void outputEndSublist();
    void outputBeginDict();
    void outputDictSeparator();
    void outputDictValueSeparator();
    void outputEndDict();

private:
    OutputBuffer *const _output;
    const OutputFormat _format;
    const std::string _field_separator;
    const std::string _dataset_separator;
    const std::string _list_separator;
    const std::string _host_service_separator;
    const int _timezone_offset;

    void outputChars(const char *value, int len);
};

#endif  // Renderer_h
