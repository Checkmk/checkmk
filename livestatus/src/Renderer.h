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
#include <memory>
#include <string>
#include <vector>
#include "OutputBuffer.h"
#include "global_counters.h"

enum class OutputFormat { csv, json, python };

class Renderer {
public:
    static std::unique_ptr<Renderer> make(
        OutputBuffer *output, OutputBuffer::ResponseHeader response_header,
        bool do_keep_alive, std::string invalid_header_message,
        OutputFormat format, std::string field_separator,
        std::string dataset_separator, std::string list_separator,
        std::string host_service_separator, int timezone_offset);

    virtual ~Renderer();

    void setError(OutputBuffer::ResponseCode code, const std::string &message);
    std::size_t size() const;

    virtual void startOfQuery() = 0;
    virtual void outputDataSetSeparator() = 0;
    virtual void endOfQuery() = 0;

    // Output a single row returned by lq.
    virtual void outputDatasetBegin() = 0;
    virtual void outputFieldSeparator() = 0;
    virtual void outputDatasetEnd() = 0;

    // Output a list-valued column.
    virtual void outputBeginList() = 0;
    virtual void outputListSeparator() = 0;
    virtual void outputEndList() = 0;

    // Output a list-valued value within a list-valued column.
    virtual void outputBeginSublist() = 0;
    virtual void outputSublistSeparator() = 0;
    virtual void outputEndSublist() = 0;

    // Output a dictionary, see CustomVarsColumn.
    virtual void outputBeginDict() = 0;
    virtual void outputDictSeparator() = 0;
    virtual void outputDictValueSeparator() = 0;
    virtual void outputEndDict() = 0;

    virtual void outputNull() = 0;
    virtual void outputBlob(const std::vector<char> *blob) = 0;
    // len = -1 -> use strlen(), len >= 0: consider output as blob, do not
    // handle UTF-8.
    virtual void outputString(const char *value, int len = -1) = 0;

    void outputInteger(int32_t value);
    void outputInteger64(int64_t value);
    void outputTime(int32_t value);
    void outputUnsignedLong(unsigned long value);
    void outputCounter(counter_t value);
    void outputDouble(double value);
    void outputAsciiEscape(char value);
    void outputUnicodeEscape(unsigned value);

protected:
    Renderer(OutputBuffer *output, OutputBuffer::ResponseHeader response_header,
             bool do_keep_alive, std::string invalid_header_message,
             int timezone_offset);

    void add(const std::string &str);
    void add(const std::vector<char> &blob);
    void outputChars(const char *value, int len);

private:
    OutputBuffer *const _output;
    const int _timezone_offset;
};

#endif  // Renderer_h
