// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebContact.h"

#include "nagios.h"

std::unique_ptr<const IContact> ToIContact(const contact *c) {
    return c != nullptr ? std::make_unique<NebContact>(*c) : nullptr;
}
