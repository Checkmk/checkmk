// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableTimeperiods_h
#define TableTimeperiods_h

#include <string>

#include "livestatus/Table.h"
class ICore;
class Query;
class User;

class TableTimeperiods : public Table {
public:
    explicit TableTimeperiods(ICore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user) override;
};

#endif  // TableTimeperiods_h
