// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableServicesByGroup_h
#define TableServicesByGroup_h

#include <string>

#include "livestatus/Table.h"
class ICore;

class TableServicesByGroup : public Table {
public:
    explicit TableServicesByGroup(ICore *mc);
    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
    // NOTE: We do *not* implement findObject() here, because we don't know
    // which service group we should refer to: Every service can be part of many
    // service groups.
};

#endif  // TableServicesByGroup_h
