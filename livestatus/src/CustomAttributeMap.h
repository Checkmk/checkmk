// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomAttributeMap_h
#define CustomAttributeMap_h

#include <vector>

#include "MapUtils.h"
#include "MonitoringCore.h"

class CustomAttributeMap {
public:
    class Keys;
    class Values;
    CustomAttributeMap(const MonitoringCore *const mc, const AttributeKind kind)
        : mc_{mc}, kind_{kind} {}
    template <class T>
    Attributes operator()(const T &obj) {
        if (const auto *p = obj.custom_variables) {
            return mc_->customAttributes(&p, kind_);
        }
        return {};
    };

private:
    const MonitoringCore *const mc_;
    const AttributeKind kind_;
};

class CustomAttributeMap::Keys {
public:
    Keys(const MonitoringCore *const mc, const AttributeKind kind)
        : m_{mc, kind} {}
    template <class T>
    std::vector<Attributes::key_type> operator()(const T &obj) {
        return mk::map_keys(m_(obj));
    }

private:
    CustomAttributeMap m_;
};

class CustomAttributeMap::Values {
public:
    Values(const MonitoringCore *const mc, const AttributeKind kind)
        : m_{mc, kind} {}
    template <class T>
    std::vector<Attributes::mapped_type> operator()(const T &obj) {
        return mk::map_values(m_(obj));
    }

private:
    CustomAttributeMap m_;
};

#endif
