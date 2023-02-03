// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContact_h
#define NebContact_h

#include <algorithm>

#include "CustomAttributeMap.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebContact : public IContact {
public:
    explicit NebContact(const contact &contact) : contact_{contact} {}

    [[nodiscard]] const void *handle() const override { return &contact_; };

    bool all_of_labels(const std::function<bool(const std::string &name,
                                                const std::string &value)>
                           &pred) const override {
        // TODO(sp) Avoid construction of temporary map
        auto labels = CustomAttributeMap{AttributeKind::labels}(contact_);
        return std::all_of(
            labels.cbegin(), labels.cend(),
            [&pred](const std::pair<std::string, std::string> &label) {
                return pred(label.first, label.second);
            });
    }

private:
    const contact &contact_;
};

#endif  // NebContact_h
