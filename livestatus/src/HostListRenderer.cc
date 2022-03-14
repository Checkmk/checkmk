// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostListRenderer.h"

#include "Renderer.h"

void HostListRenderer::output(ListRenderer &l,
                              const column::host_list::Entry &entry) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(entry.host_name);
            break;
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(entry.host_name);
            s.output(static_cast<int>(entry.current_state));
            s.output(static_cast<int>(entry.has_been_checked));
            break;
        }
    }
}
