// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CommentRenderer_h
#define CommentRenderer_h

#include <memory>
#include <string>

#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"

class CommentRenderer
    : public ListColumnRenderer<std::unique_ptr<const IComment>> {
public:
    enum class verbosity { none, medium, full };
    explicit CommentRenderer(verbosity v) : verbosity_{v} {}
    void output(ListRenderer &l,
                const std::unique_ptr<const IComment> &comment) const override;

private:
    verbosity verbosity_;
};

namespace column::detail {
template <>
inline std::string serialize(const std::unique_ptr<const IComment> &data) {
    return std::to_string(data->id());
}
}  // namespace column::detail

#endif
