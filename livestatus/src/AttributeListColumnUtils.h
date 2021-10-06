// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef AttributeListColumnUtils_h
#define AttributeListColumnUtils_h

#include <string>
#include <vector>
class Logger;

namespace column::attribute_list {
std::string refValueFor(const std::string &value, Logger *logger);
std::vector<std::string> decode(unsigned long mask);
}  // namespace column::attribute_list

#endif
