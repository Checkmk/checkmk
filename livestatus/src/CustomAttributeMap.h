// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomAttributeMap_h
#define CustomAttributeMap_h

#include <vector>

#include "NagiosCore.h"
#include "livestatus/MapUtils.h"

class CustomAttributeMap {
public:
    class Keys;
    class Values;
    explicit CustomAttributeMap(const AttributeKind kind) : kind_{kind} {}
    template <class T>
    Attributes operator()(const T &obj) {
        if (const auto *p = obj.custom_variables) {
            return CustomAttributes(p, kind_);
        }
        return {};
    };

private:
    const AttributeKind kind_;
};

class CustomAttributeMap::Keys {
public:
    explicit Keys(const AttributeKind kind) : m_{kind} {}
    template <class T>
    std::vector<Attributes::key_type> operator()(const T &obj) {
        return mk::map_keys(m_(obj));
    }

private:
    CustomAttributeMap m_;
};

class CustomAttributeMap::Values {
public:
    explicit Values(const AttributeKind kind) : m_{kind} {}
    template <class T>
    std::vector<Attributes::mapped_type> operator()(const T &obj) {
        return mk::map_values(m_(obj));
    }

private:
    CustomAttributeMap m_;
};

#endif
