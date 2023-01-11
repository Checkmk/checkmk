// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContactGroup_h
#define NebContactGroup_h

#include <memory>
#include <string>
#include <vector>

#include "livestatus/Interface.h"

class NebContactGroup : public IContactGroup {
public:
    explicit NebContactGroup(const std::string &name) : name_{name} {}
    bool isMember(const IContact &) const override;

private:
    const std::string name_;
};

std::vector<std::unique_ptr<const IContactGroup>> ToIContactGroups(
    const std::string &group_sequence);

#endif  // NebContactGroup_h
