// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RendererCSV_h
#define RendererCSV_h

#include <iosfwd>
#include <string>

#include "livestatus/Renderer.h"

enum class Encoding;
class Logger;

// Note: The CSV format is a bit underspecified, but the most "authoritative"
// reference seems to be https://tools.ietf.org/html/rfc4180.
class RendererCSV : public Renderer {
public:
    RendererCSV(std::ostream &os, Logger *logger, Encoding data_encoding);

    [[nodiscard]] bool useSurrogatePairs() const override;
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
    void outputEscaped(char ch);
};

#endif  // RendererCSV_h
