// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableDummy_h
#define TableDummy_h

#include <string>

#include "livestatus/Table.h"
class ICore;

class TableDummy : public Table {
public:
    [[nodiscard]] std::string name() const override { return "dummy"; }
    [[nodiscard]] std::string namePrefix() const override { return "dummy_"; }
    void answerQuery(Query & /*unused*/, const User & /*unused*/,
                     const ICore & /*unused*/) override {}
};

#endif  //  TableDummy_h
