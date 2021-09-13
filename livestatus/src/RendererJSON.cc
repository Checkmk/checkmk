// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "RendererJSON.h"

#include <ostream>

#include "data_encoding.h"

RendererJSON::RendererJSON(std::ostream &os, Logger *logger,
                           Encoding data_encoding)
    : Renderer(os, logger, data_encoding) {}

// --------------------------------------------------------------------------

void RendererJSON::beginQuery() { _os << "["; }
void RendererJSON::separateQueryElements() { _os << ",\n"; }
void RendererJSON::endQuery() { _os << "]\n"; }

// --------------------------------------------------------------------------

void RendererJSON::beginRow() { _os << "["; }
void RendererJSON::beginRowElement() {}
void RendererJSON::endRowElement() {}
void RendererJSON::separateRowElements() { _os << ","; }
void RendererJSON::endRow() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererJSON::beginList() { _os << "["; }
void RendererJSON::separateListElements() { _os << ","; }
void RendererJSON::endList() { _os << "]"; }

// --------------------------------------------------------------------------

void RendererJSON::beginSublist() { beginList(); }
void RendererJSON::separateSublistElements() { separateListElements(); }
void RendererJSON::endSublist() { endList(); }

// --------------------------------------------------------------------------

void RendererJSON::beginDict() { _os << "{"; }
void RendererJSON::separateDictElements() { _os << ","; }
void RendererJSON::separateDictKeyValue() { _os << ":"; }
void RendererJSON::endDict() { _os << "}"; }

// --------------------------------------------------------------------------

void RendererJSON::outputNull() { _os << "null"; }

void RendererJSON::outputBlob(const std::vector<char> &value) {
    outputUnicodeString("", &value[0], &value[value.size()], Encoding::latin1);
}

void RendererJSON::outputString(const std::string &value) {
    outputUnicodeString("", &value[0], &value[value.size()], _data_encoding);
}
