// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef agent_plugins_h__
#define agent_plugins_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class AgentPlugins : public Asynchronous {
public:
    static constexpr char kSepChar = '\0';
    AgentPlugins(std::string_view name, char separator)
        : Asynchronous(name, separator) {
        setHeaderless();
    }

private:
    std::string makeBody() override;
};

namespace agent_plugins {}  // namespace agent_plugins

}  // namespace provider

};  // namespace cma

#endif  // agent_plugins_h__
