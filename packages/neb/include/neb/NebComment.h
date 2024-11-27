// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebComment_h
#define NebComment_h

#include <chrono>
#include <cstdint>
#include <string>

#include "livestatus/Interface.h"

class Comment;

class NebComment : public IComment {
public:
    NebComment(const Comment &comment, const IHost &host,
               const IService *service)
        : comment_{comment}, host_{host}, service_{service} {}

    [[nodiscard]] int32_t id() const override;
    [[nodiscard]] std::string author() const override;
    [[nodiscard]] std::string comment() const override;
    [[nodiscard]] CommentType entry_type() const override;
    [[nodiscard]] std::chrono::system_clock::time_point entry_time()
        const override;
    [[nodiscard]] bool isService() const override;
    [[nodiscard]] bool persistent() const override;
    [[nodiscard]] CommentSource source() const override;
    [[nodiscard]] bool expires() const override;
    [[nodiscard]] std::chrono::system_clock::time_point expire_time()
        const override;
    [[nodiscard]] const IHost &host() const override { return host_; }
    [[nodiscard]] const IService *service() const override { return service_; }

private:
    const Comment &comment_;
    const IHost &host_;
    const IService *service_;
};

#endif  // NebComment_h
