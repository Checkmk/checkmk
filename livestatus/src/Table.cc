// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Table.h"

#include <cstdlib>
#include <stdexcept>

#include "Column.h"
#include "DynamicColumn.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "StringUtils.h"

Table::Table(MonitoringCore *mc) : _mc(mc) {}

Table::~Table() = default;

void Table::addColumn(std::unique_ptr<Column> col) {
    if (_columns.find(col->name()) != _columns.end()) {
        // NOTE: We can't uses Table::logger() here, because there might be no
        // monitoring core yet. We get called *very* early...
        Emergency(col->logger()) << "overwriting column '" << col->name()
                                 << "' in table '" << name() << "'";
        ::abort();
    }
    _columns.emplace(col->name(), std::move(col));
}

void Table::addDynamicColumn(std::unique_ptr<DynamicColumn> dyncol) {
    _dynamic_columns.emplace(dyncol->name(), std::move(dyncol));
}

std::shared_ptr<Column> Table::column(std::string colname) const {
    // Strip away a sequence of prefixes.
    while (mk::starts_with(colname, namePrefix())) {
        colname = colname.substr(namePrefix().size());
    }

    auto sep = colname.find(':');
    if (sep != std::string::npos) {
        // TODO(sp) Use shared_ptr
        return dynamicColumn(colname.substr(0, sep), colname.substr(sep + 1));
    }

    // First try exact match...
    auto it = _columns.find(colname);
    if (it != _columns.end()) {
        return it->second;
    }

    // ... then try to match with the prefix.
    it = _columns.find(namePrefix() + colname);
    if (it != _columns.end()) {
        return it->second;
    }

    throw std::runtime_error("table '" + name() + "' has no column '" +
                             colname + "'");
}

std::unique_ptr<Column> Table::dynamicColumn(const std::string &colname,
                                             const std::string &rest) const {
    auto it = _dynamic_columns.find(colname);
    if (it == _dynamic_columns.end()) {
        throw std::runtime_error("table '" + name() +
                                 "' has no dynamic column '" + colname + "'");
    }
    auto sep_pos = rest.find(':');
    if (sep_pos == std::string::npos) {
        throw std::runtime_error("missing separator in dynamic column '" +
                                 colname + "'");
    }
    std::string colname2 = rest.substr(0, sep_pos);
    if (colname2.empty()) {
        throw std::runtime_error("empty column name for dynamic column '" +
                                 colname + "'");
    }
    return it->second->createColumn(colname2, rest.substr(sep_pos + 1));
}

bool Table::isAuthorized(Row /*unused*/, const contact * /*unused*/) const {
    return true;
}

Row Table::get(const std::string & /*unused*/) const { return Row{nullptr}; }

Row Table::getDefault() const { return Row{nullptr}; }

Logger *Table::logger() const { return _mc->loggerLivestatus(); }
