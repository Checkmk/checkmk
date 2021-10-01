// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceListRenderer.h"

#include "Renderer.h"

void ServiceListRenderer::output(
    ListRenderer &l, const column::service_list::Entry &entry) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(std::string(entry.description));
            break;
        case verbosity::low: {
            SublistRenderer s(l);
            s.output(entry.description);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<int>(entry.has_been_checked));
            break;
        }
        case verbosity::medium: {
            SublistRenderer s(l);
            s.output(entry.description);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<int>(entry.has_been_checked));
            s.output(entry.plugin_output);
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(entry.description);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<int>(entry.has_been_checked));
            s.output(entry.plugin_output);
            s.output(static_cast<int>(entry.last_hard_state));
            s.output(entry.current_attempt);
            s.output(entry.max_check_attempts);
            s.output(entry.scheduled_downtime_depth);
            s.output(static_cast<int>(entry.acknowledged));
            s.output(static_cast<int>(entry.service_period_active));
            break;
        }
    }
}
