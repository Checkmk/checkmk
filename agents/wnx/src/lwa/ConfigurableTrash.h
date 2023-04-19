// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// SPECIAL INCLUDE FOR Configurable.h
#ifndef ConfigurableTrash_h__
#define ConfigurableTrash_h__

    virtual void output(const std::string &key,
                        std::ostream &out) const override {
        for (const auto & [var, value] : this->values()) {
            out << key << " " << var << " = " << value << "\n";
        }
    }
#endif  // ConfigurableTrash_h__
