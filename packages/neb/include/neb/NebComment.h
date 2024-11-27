// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebComment_h
#define NebComment_h

#include "livestatus/Interface.h"
#include "neb/Comment.h"
#include "neb/NebHost.h"
#include "neb/NebService.h"

class NebComment : public IComment {
public:
    NebComment(const Comment &comment, const IHost &host,
               const IService *service)
        : comment_{comment}, host_{host}, service_{service} {}

    [[nodiscard]] int32_t id() const override {
        // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
        return comment_._id;
    }

    [[nodiscard]] std::string author() const override {
        return comment_._author;
    }

    [[nodiscard]] std::string comment() const override {
        return comment_._comment;
    }

    [[nodiscard]] CommentType entry_type() const override {
        return comment_._entry_type;
    }

    [[nodiscard]] std::chrono::system_clock::time_point entry_time()
        const override {
        return comment_._entry_time;
    }

    [[nodiscard]] bool isService() const override {
        return comment_._is_service;
    }

    [[nodiscard]] bool persistent() const override {
        return comment_._persistent;
    }

    [[nodiscard]] CommentSource source() const override {
        return comment_._source;
    }

    [[nodiscard]] bool expires() const override { return comment_._expires; }

    [[nodiscard]] std::chrono::system_clock::time_point expire_time()
        const override {
        return comment_._expire_time;
    }

    [[nodiscard]] const IHost &host() const override { return host_; }

    [[nodiscard]] const IService *service() const override { return service_; }

private:
    const Comment &comment_;
    const IHost &host_;
    const IService *service_;
};

#endif  // NebComment_h
