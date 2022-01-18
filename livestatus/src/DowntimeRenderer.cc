// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DowntimeRenderer.h"

#include <chrono>

#include "ChronoUtils.h"
#include "Renderer.h"

void DowntimeRenderer::output(ListRenderer &l,
                              const DowntimeData &downtime) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(downtime._id);
            break;
        case verbosity::medium: {
            SublistRenderer s(l);
            s.output(downtime._id);
            s.output(downtime._author);
            s.output(downtime._comment);
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(downtime._id);
            s.output(downtime._author);
            s.output(downtime._comment);
            s.output(downtime._origin_is_rule);
            s.output(downtime._entry_time);
            s.output(downtime._start_time);
            s.output(downtime._end_time);
            s.output(downtime._fixed);
            s.output(mk::ticks<std::chrono::seconds>(downtime._duration));
            s.output(downtime._recurring);
            s.output(downtime._pending);
            break;
        }
    }
}
