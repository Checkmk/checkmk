// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/CommentRenderer.h"

#include "livestatus/Renderer.h"

void CommentRenderer::output(
    ListRenderer &l, const std::unique_ptr<const IComment> &comment) const {
    switch (verbosity_) {
        case verbosity::none:
            l.output(comment->id());
            break;
        case verbosity::medium: {
            SublistRenderer s(l);
            s.output(comment->id());
            s.output(comment->author());
            s.output(comment->comment());
            break;
        }
        case verbosity::full: {
            SublistRenderer s(l);
            s.output(comment->id());
            s.output(comment->author());
            s.output(comment->comment());
            s.output(comment->entry_type());
            s.output(comment->entry_time());
            break;
        }
    }
}
