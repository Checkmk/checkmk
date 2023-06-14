// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/DowntimeRenderer.h"

#include <chrono>

#include "livestatus/ChronoUtils.h"
#include "livestatus/Renderer.h"

void DowntimeRenderer::output(
    ListRenderer &l, const std::unique_ptr<const IDowntime> &downtime) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(downtime->id());
            break;
        case verbosity::medium: {
            SublistRenderer s(l);
            s.output(downtime->id());
            s.output(downtime->author());
            s.output(downtime->comment());
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(downtime->id());
            s.output(downtime->author());
            s.output(downtime->comment());
            s.output(downtime->origin_is_rule());
            s.output(downtime->entry_time());
            s.output(downtime->start_time());
            s.output(downtime->end_time());
            s.output(downtime->fixed());
            s.output(mk::ticks<std::chrono::seconds>(downtime->duration()));
            s.output(downtime->recurring());
            s.output(downtime->pending());
            break;
        }
    }
}
