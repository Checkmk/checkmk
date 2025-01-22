// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RendererCSV.h"

#include <ostream>
#include <vector>

class Logger;

RendererCSV::RendererCSV(std::ostream &os, Logger *logger,
                         Encoding data_encoding)
    : Renderer(os, logger, data_encoding) {}

// --------------------------------------------------------------------------

void RendererCSV::beginQuery() {}
void RendererCSV::separateQueryElements() {}
void RendererCSV::endQuery() {}

// --------------------------------------------------------------------------

void RendererCSV::beginRow() {}
void RendererCSV::beginRowElement() { _os << R"(")"; }  // "
void RendererCSV::endRowElement() { _os << R"(")"; }    // "
void RendererCSV::separateRowElements() { _os << ","; }
void RendererCSV::endRow() { _os << "\r\n"; }

// --------------------------------------------------------------------------

void RendererCSV::beginList() {}
void RendererCSV::separateListElements() { _os << ","; }
void RendererCSV::endList() {}

// --------------------------------------------------------------------------

void RendererCSV::beginSublist() {}
void RendererCSV::separateSublistElements() { _os << "|"; }
void RendererCSV::endSublist() {}

// --------------------------------------------------------------------------

void RendererCSV::beginDict() {}
void RendererCSV::separateDictElements() { _os << ","; }
void RendererCSV::separateDictKeyValue() { _os << "|"; }
void RendererCSV::endDict() {}

// --------------------------------------------------------------------------

bool RendererCSV::useSurrogatePairs() const { return false; };

void RendererCSV::outputNull() {}

void RendererCSV::outputEscaped(char ch) {
    _os << (ch == '"' ? R"("")" : std::string(1, ch));
}

void RendererCSV::outputBlob(const std::vector<char> &value) {
    for (auto ch : value) {
        outputEscaped(ch);
    }
}

void RendererCSV::outputString(const std::string &value) {
    for (auto ch : value) {
        outputEscaped(ch);
    }
}
