// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CommentRenderer.h"

#include "Renderer.h"

void CommentRenderer::output(ListRenderer &l,
                             const CommentData &comment) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(comment._id);
            break;
        case verbosity::medium: {
            SublistRenderer s(l);
            s.output(comment._id);
            s.output(comment._author);
            s.output(comment._comment);
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(comment._id);
            s.output(comment._author);
            s.output(comment._comment);
            s.output(comment._entry_type);
            s.output(comment._entry_time);
            break;
        }
    }
}
