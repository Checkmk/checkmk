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

#ifndef RendererBrokenCSV_h
#define RendererBrokenCSV_h

#include "config.h"  // IWYU pragma: keep
#include <iosfwd>
#include <string>
#include <utility>
#include <vector>
#include "Renderer.h"
#include "data_encoding.h"
class Logger;

class CSVSeparators {
public:
    CSVSeparators(std::string dataset, std::string field, std::string list,
                  std::string host_service)
        : _dataset(std::move(dataset))
        , _field(std::move(field))
        , _list(std::move(list))
        , _host_service(std::move(host_service)) {}

    [[nodiscard]] std::string dataset() const { return _dataset; }
    [[nodiscard]] std::string field() const { return _field; }
    [[nodiscard]] std::string list() const { return _list; }
    [[nodiscard]] std::string hostService() const { return _host_service; }

private:
    std::string _dataset;
    std::string _field;
    std::string _list;
    std::string _host_service;
};

// A broken CSV renderer, just for backwards compatibility with old Livestatus
// versions.
class RendererBrokenCSV : public Renderer {
public:
    RendererBrokenCSV(std::ostream& os, Logger* logger,
                      CSVSeparators separators, Encoding data_encoding)
        : Renderer(os, logger, data_encoding)
        , _separators(std::move(separators)) {}

    void outputNull() override;
    void outputBlob(const std::vector<char>& value) override;
    void outputString(const std::string& value) override;

    void beginQuery() override;
    void separateQueryElements() override;
    void endQuery() override;

    void beginRow() override;
    void beginRowElement() override;
    void endRowElement() override;
    void separateRowElements() override;
    void endRow() override;

    void beginList() override;
    void separateListElements() override;
    void endList() override;

    void beginSublist() override;
    void separateSublistElements() override;
    void endSublist() override;

    void beginDict() override;
    void separateDictElements() override;
    void separateDictKeyValue() override;
    void endDict() override;

private:
    const CSVSeparators _separators;
};

#endif  // RendererBrokenCSV_h
