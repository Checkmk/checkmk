// Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "neb/NebComment.h"

#include "neb/Comment.h"

int32_t NebComment::id() const {
    // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
    return comment_._id;
}

std::string NebComment::author() const { return comment_._author; }

std::string NebComment::comment() const { return comment_._comment; }

CommentType NebComment::entry_type() const { return comment_._entry_type; }

std::chrono::system_clock::time_point NebComment::entry_time() const {
    return comment_._entry_time;
}

bool NebComment::isService() const { return comment_._is_service; }

bool NebComment::persistent() const { return comment_._persistent; }

CommentSource NebComment::source() const { return comment_._source; }

bool NebComment::expires() const { return comment_._expires; }

std::chrono::system_clock::time_point NebComment::expire_time() const {
    return comment_._expire_time;
}
