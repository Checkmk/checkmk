// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableQueryHelper_h
#define TableQueryHelper_h

#include <list>
#include <string>
class Table;

namespace mk::test {

std::string query(Table &table, const std::list<std::string> &q);

}  // namespace mk::test

#endif
