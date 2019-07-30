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
#include <chrono>
#include <iosfwd>
#include <memory>
#include <string>
#include <utility>
#include <vector>
#include "data_encoding.h"
class CSVSeparators;
class Logger;

enum class OutputFormat { csv, broken_csv, json, python, python3 };

struct Null {};

struct PlainChar {
    char _ch;
};

struct HexEscape {
    char _ch;
};

struct RowFragment {
    std::string _str;
    bool operator<(const RowFragment &other) const { return _str < other._str; }
};

class Renderer {
public:
    static std::unique_ptr<Renderer> make(OutputFormat format, std::ostream &os,
                                          Logger *logger,
                                          const CSVSeparators &separators,
                                          Encoding data_encoding);

    virtual ~Renderer();

    // default implementation for (un)signed int/long
    template <typename T>
    void output(T value) {
        _os << std::to_string(value);
    }

    void output(double value);
    void output(PlainChar value);
    void output(HexEscape value);
    void output(const RowFragment &value);
    void output(char16_t value);
    void output(char32_t value);
    void output(Null value);
    void output(const std::vector<char> &value);
    void output(const std::string &value);
    void output(std::chrono::system_clock::time_point value);

    // A whole query.
    virtual void beginQuery() = 0;
    virtual void separateQueryElements() = 0;
    virtual void endQuery() = 0;

    // Output a single row returned by lq.
    virtual void beginRow() = 0;
    virtual void beginRowElement() = 0;
    virtual void endRowElement() = 0;
    virtual void separateRowElements() = 0;
    virtual void endRow() = 0;

    // Output a list-valued column.
    virtual void beginList() = 0;
    virtual void separateListElements() = 0;
    virtual void endList() = 0;

    // Output a list-valued value within a list-valued column.
    virtual void beginSublist() = 0;
    virtual void separateSublistElements() = 0;
    virtual void endSublist() = 0;

    // Output a dictionary, see CustomVarsDictColumn.
    virtual void beginDict() = 0;
    virtual void separateDictElements() = 0;
    virtual void separateDictKeyValue() = 0;
    virtual void endDict() = 0;

protected:
    std::ostream &_os;
    const Encoding _data_encoding;

    Renderer(std::ostream &os, Logger *logger, Encoding data_encoding);

    void outputByteString(const std::string &prefix,
                          const std::vector<char> &value);
    void outputUnicodeString(const std::string &prefix, const char *start,
                             const char *end, Encoding data_encoding);

private:
    Logger *const _logger;

    void outputUTF8(const char *start, const char *end);
    void outputLatin1(const char *start, const char *end);
    void outputMixed(const char *start, const char *end);
    void truncatedUTF8();
    void invalidUTF8(unsigned char ch);

    virtual void outputNull() = 0;
    virtual void outputBlob(const std::vector<char> &value) = 0;
    virtual void outputString(const std::string &value) = 0;
};

enum class EmitBeginEnd { on, off };

class QueryRenderer {
public:
    class BeginEnd {
    public:
        explicit BeginEnd(QueryRenderer &query) : _query(query) {
            if (_query._first) {
                _query._first = false;
            } else {
                _query.renderer().separateQueryElements();
            }
        }

    private:
        QueryRenderer &_query;
    };

    QueryRenderer(Renderer &rend, EmitBeginEnd emitBeginEnd)
        : _renderer(rend), _emitBeginEnd(emitBeginEnd), _first(true) {
        if (_emitBeginEnd == EmitBeginEnd::on) {
            renderer().beginQuery();
        }
    }

    ~QueryRenderer() {
        if (_emitBeginEnd == EmitBeginEnd::on) {
            renderer().endQuery();
        }
    }

    Renderer &renderer() const { return _renderer; }
    EmitBeginEnd emitBeginEnd() const { return _emitBeginEnd; }

private:
    Renderer &_renderer;
    EmitBeginEnd _emitBeginEnd;
    bool _first;
};

class RowRenderer {
public:
    class BeginEnd {
    public:
        explicit BeginEnd(RowRenderer &row) : _row(row) {
            _row.separate();
            _row.renderer().beginRowElement();
        }
        ~BeginEnd() { _row.renderer().endRowElement(); }

    private:
        RowRenderer &_row;
    };

    explicit RowRenderer(QueryRenderer &query)
        : _query(query), _be(query), _first(true) {
        if (_query.emitBeginEnd() == EmitBeginEnd::on) {
            renderer().beginRow();
        }
    }

    ~RowRenderer() {
        if (_query.emitBeginEnd() == EmitBeginEnd::on) {
            renderer().endRow();
        }
    }

    Renderer &renderer() const { return _query.renderer(); }

    void output(const RowFragment &value) {
        separate();
        renderer().output(std::move(value));
    }

    template <typename T>
    void output(T value) {
        BeginEnd be(*this);
        renderer().output(value);
    }

private:
    QueryRenderer &_query;
    QueryRenderer::BeginEnd _be;
    bool _first;

    void separate() {
        if (_first) {
            _first = false;
        } else {
            renderer().separateRowElements();
        }
    }
};

class ListRenderer {
public:
    class BeginEnd {
    public:
        explicit BeginEnd(ListRenderer &list) : _list(list) {
            if (_list._first) {
                _list._first = false;
            } else {
                _list.renderer().separateListElements();
            }
        }

    private:
        ListRenderer &_list;
    };

    explicit ListRenderer(RowRenderer &row)
        : _row(row), _be(row), _first(true) {
        renderer().beginList();
    }

    ~ListRenderer() { renderer().endList(); }

    Renderer &renderer() const { return _row.renderer(); }

    template <typename T>
    void output(T value) {
        BeginEnd be(*this);
        renderer().output(value);
    }

private:
    RowRenderer &_row;
    RowRenderer::BeginEnd _be;
    bool _first;
};

class SublistRenderer {
public:
    class BeginEnd {
    public:
        explicit BeginEnd(SublistRenderer &sublist) : _sublist(sublist) {
            if (_sublist._first) {
                _sublist._first = false;
            } else {
                _sublist.renderer().separateSublistElements();
            }
        }

    private:
        SublistRenderer &_sublist;
    };

    explicit SublistRenderer(ListRenderer &list)
        : _list(list), _be(list), _first(true) {
        renderer().beginSublist();
    }

    ~SublistRenderer() { renderer().endSublist(); }

    Renderer &renderer() const { return _list.renderer(); }

    template <typename T>
    void output(T value) {
        BeginEnd be(*this);
        renderer().output(value);
    }

private:
    ListRenderer &_list;
    ListRenderer::BeginEnd _be;
    bool _first;
};

class DictRenderer {
public:
    class BeginEnd {
    public:
        explicit BeginEnd(DictRenderer &dict) : _dict(dict) {
            if (_dict._first) {
                _dict._first = false;
            } else {
                _dict.renderer().separateDictElements();
            }
        }

    private:
        DictRenderer &_dict;
    };

    explicit DictRenderer(RowRenderer &row)
        : _row(row), _be(row), _first(true) {
        renderer().beginDict();
    }

    ~DictRenderer() { renderer().endDict(); }

    Renderer &renderer() const { return _row.renderer(); }

    void output(const std::string &key, const std::string &value) {
        BeginEnd be(*this);
        renderer().output(key);
        renderer().separateDictKeyValue();
        renderer().output(value);
    }

private:
    RowRenderer &_row;
    RowRenderer::BeginEnd _be;
    bool _first;
};

#endif  // Renderer_h
