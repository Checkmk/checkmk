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
    // for friend declarations
    class Row;
    class List;
    class Sublist;
    class Dict;

    class Query {
    public:
        explicit Query(Renderer *renderer) : _renderer(renderer), _first(true) {
            _renderer->startQuery();
        }

        ~Query() { _renderer->endQuery(); }

    private:
        Renderer *const _renderer;
        bool _first;

        void next() {
            if (_first) {
                _first = false;
            } else {
                _renderer->separateQueryElements();
            }
        }

        Renderer *renderer() const { return _renderer; }

        // for next() and renderer()
        friend class Renderer::Row;
    };

    class Row {
    public:
        explicit Row(Query &query) : _query(query), _first(true) {
            _query.next();
            renderer()->startRow();
        }

        ~Row() { renderer()->endRow(); }

        void next() {
            if (_first) {
                _first = false;
            } else {
                renderer()->separateRowElements();
            }
        }

        void outputNull() { renderer()->outputNull(); }
        void outputBlob(const std::vector<char> *blob) {
            renderer()->outputBlob(blob);
        }
        void outputString(const char *value) {
            renderer()->outputString(value);
        }
        void outputInteger(int32_t value) { renderer()->outputInteger(value); }
        void outputTime(int32_t value) { renderer()->outputTime(value); }
        void outputUnsignedLong(unsigned long value) {
            renderer()->outputUnsignedLong(value);
        }
        void outputCounter(counter_t value) {
            renderer()->outputCounter(value);
        }
        void outputDouble(double value) { renderer()->outputDouble(value); }

    private:
        Query &_query;
        bool _first;

        Renderer *renderer() const { return _query.renderer(); }

        // for renderer()
        friend class Renderer::List;

        // for renderer()
        friend class Renderer::Dict;
    };

    class List {
    public:
        explicit List(Row &row) : _row(row), _first(true) {
            renderer()->startList();
        }

        ~List() { renderer()->endList(); }

        void next() {
            if (_first) {
                _first = false;
            } else {
                renderer()->separateListElements();
            }
        }

        void outputString(const char *value) {
            renderer()->outputString(value);
        }
        void outputUnsignedLong(unsigned long value) {
            renderer()->outputUnsignedLong(value);
        }
        void outputTime(int32_t value) { renderer()->outputTime(value); }
        void outputDouble(double value) { renderer()->outputDouble(value); }

    private:
        Row &_row;
        bool _first;

        Renderer *renderer() const { return _row.renderer(); }

        // for renderer()
        friend class Renderer::Sublist;
    };

    class Sublist {
    public:
        explicit Sublist(List &list) : _list(list), _first(true) {
            _list.next();
            renderer()->startSublist();
        }

        ~Sublist() { renderer()->endSublist(); }

        void next() {
            if (_first) {
                _first = false;
            } else {
                renderer()->separateSublistElements();
            }
        }

        void outputInteger(int32_t value) { renderer()->outputInteger(value); }
        void outputTime(int32_t value) { renderer()->outputTime(value); }
        void outputUnsignedLong(unsigned long value) {
            renderer()->outputUnsignedLong(value);
        }
        void outputString(const char *value) {
            renderer()->outputString(value);
        }

    private:
        List &_list;
        bool _first;

        Renderer *renderer() const { return _list.renderer(); }
    };

    class Dict {
    public:
        explicit Dict(Renderer::Row &row) : _row(row), _first(true) {
            renderer()->startDict();
        }

        ~Dict() { renderer()->endDict(); }

        void renderKeyValue(std::string key, std::string value) {
            next();
            renderer()->outputString(key.c_str());
            renderer()->separateDictKeyValue();
            renderer()->outputString(value.c_str());
        }

    private:
        Row &_row;
        bool _first;

        void next() {
            if (_first) {
                _first = false;
            } else {
                renderer()->separateDictElements();
            }
        }

        Renderer *renderer() const { return _row.renderer(); }
    };

    static std::unique_ptr<Renderer> make(
        OutputBuffer *output, OutputBuffer::ResponseHeader response_header,
        bool do_keep_alive, std::string invalid_header_message,
        OutputFormat format, std::string field_separator,
        std::string dataset_separator, std::string list_separator,
        std::string host_service_separator, int timezone_offset);

    virtual ~Renderer();

    void setError(OutputBuffer::ResponseCode code, const std::string &message);
    std::size_t size() const;

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

    // A whole query.
    virtual void startQuery() = 0;
    virtual void separateQueryElements() = 0;
    virtual void endQuery() = 0;

    // Output a single row returned by lq.
    virtual void startRow() = 0;
    virtual void separateRowElements() = 0;
    virtual void endRow() = 0;

    // Output a list-valued column.
    virtual void startList() = 0;
    virtual void separateListElements() = 0;
    virtual void endList() = 0;

    // Output a list-valued value within a list-valued column.
    virtual void startSublist() = 0;
    virtual void separateSublistElements() = 0;
    virtual void endSublist() = 0;

    // Output a dictionary, see CustomVarsColumn.
    virtual void startDict() = 0;
    virtual void separateDictElements() = 0;
    virtual void separateDictKeyValue() = 0;
    virtual void endDict() = 0;
};

#endif  // Renderer_h
