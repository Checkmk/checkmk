// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RendererJSON.h"

#include <ostream>
#include <vector>

#include "livestatus/data_encoding.h"

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

bool RendererJSON::useSurrogatePairs() const { return true; };

void RendererJSON::outputNull() { _os << "null"; }

void RendererJSON::outputBlob(const std::vector<char> &value) {
    outputUnicodeString(value.data(), &value[value.size()], Encoding::latin1);
}

void RendererJSON::outputString(const std::string &value) {
    outputUnicodeString(value.data(), &value[value.size()], _data_encoding);
}
