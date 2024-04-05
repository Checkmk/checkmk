// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableDowntimes_h
#define TableDowntimes_h

#include <string>

#include "livestatus/Table.h"
class ICore;
class Query;
class User;

class TableDowntimes : public Table {
public:
    explicit TableDowntimes(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user, ICore &core) override;
};

#endif  // TableDowntimes_h
