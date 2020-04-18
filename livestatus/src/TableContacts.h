// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableContacts_h
#define TableContacts_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Row.h"
#include "Table.h"
class MonitoringCore;
class Query;

#ifndef CMC
#include "contact_fwd.h"
#endif

class TableContacts : public Table {
public:
#ifndef CMC
    class IRow : virtual public Table::IRow {
    public:
        virtual const contact *getContact() const = 0;
    };
#endif
    explicit TableContacts(MonitoringCore *mc);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    [[nodiscard]] Row findObject(const std::string &objectspec) const override;

#ifdef CMC
    static void addColumns(Table *table, const std::string &prefix,
                           int indirect_offset);
#else
    static void addColumns(Table *table, const std::string &prefix);
#endif
};

#endif  // TableContacts_h
