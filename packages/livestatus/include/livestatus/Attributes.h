// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Attributes_h
#define Attributes_h

#include <string>

#include "livestatus/Interface.h"
#include "livestatus/StringUtils.h"

inline std::tuple<AttributeKind, std::string> to_attribute_kind(
    const std::string &name) {
    if (name.starts_with("_TAG_")) {
        return {AttributeKind::tags, name.substr(5)};
    }
    if (name.starts_with("_LABEL_")) {
        return {AttributeKind::labels, name.substr(7)};
    }
    if (name.starts_with("_LABELSOURCE_")) {
        return {AttributeKind::label_sources, name.substr(13)};
    }
    return {AttributeKind::custom_variables, name};
}

#endif  // Attributes_h
