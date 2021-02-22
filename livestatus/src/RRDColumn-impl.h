// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef RRDColumn_impl_h
#define RRDColumn_impl_h

#include "config.h"  // IWYU pragma: keep

#include <optional>
#include <string>
#include <utility>

#include "RRDColumn.h"

template <class T>
class RRDColumn<T>::Host : public RRDColumn<T> {
public:
    using RRDColumn::RRDColumn;

private:
    [[nodiscard]] std::optional<std::pair<std::string, std::string>>
    getHostNameServiceDesc(Row row) const override {
        if (const auto *hst{columnData<host>(row)}) {
            return {{hst->name, dummy_service_description()}};
        }
        return {};
    }
};

template <class T>
class RRDColumn<T>::Service : public RRDColumn<T> {
public:
    using RRDColumn::RRDColumn;

private:
    [[nodiscard]] std::optional<std::pair<std::string, std::string>>
    getHostNameServiceDesc(Row row) const override {
        if (const auto *svc{columnData<service>(row)}) {
            return {{svc->host_name, svc->description}};
        }
        return {};
    }
};
#endif
