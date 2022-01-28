// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RendererBrokenCSV_h
#define RendererBrokenCSV_h

#include "config.h"  // IWYU pragma: keep

#include <iosfwd>
#include <string>
#include <utility>
#include <vector>

#include "Renderer.h"
enum class Encoding;
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
    RendererBrokenCSV(std::ostream &os, Logger *logger,
                      CSVSeparators separators, Encoding data_encoding)
        : Renderer(os, logger, data_encoding)
        , _separators(std::move(separators)) {}

    void outputNull() override;
    void outputBlob(const std::vector<char> &value) override;
    void outputString(const std::string &value) override;

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
