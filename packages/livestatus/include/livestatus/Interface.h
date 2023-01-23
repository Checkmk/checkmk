// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Interface_h
#define Interface_h

#include <chrono>
#include <functional>
#include <memory>
#include <string>

class IContact {
public:
    virtual ~IContact() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
};

class IHost {
public:
    virtual ~IHost() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;
};

class IService {
public:
    virtual ~IService() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual bool hasHostContact(const IContact &) const = 0;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual std::string notificationPeriodName() const = 0;
    [[nodiscard]] virtual std::string servicePeriodName() const = 0;
};

class IHostGroup {
public:
    virtual ~IHostGroup() = default;
    virtual bool all(const std::function<bool(const IHost &)> &pred) const = 0;
};

class IServiceGroup {
public:
    virtual ~IServiceGroup() = default;
    virtual bool all(
        const std::function<bool(const IService &)> &pred) const = 0;
};

class IContactGroup {
public:
    virtual ~IContactGroup() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
    [[nodiscard]] virtual bool isMember(const IContact &) const = 0;
};

enum class CommentType : int32_t {
    user = 1,
    downtime = 2,
    flapping = 3,
    acknowledgement = 4
};

enum class CommentSource : int32_t { internal = 0, external = 1 };

class IComment {
public:
    virtual ~IComment() = default;
    [[nodiscard]] virtual int32_t id() const = 0;
    [[nodiscard]] virtual std::string author() const = 0;
    [[nodiscard]] virtual std::string comment() const = 0;
    [[nodiscard]] virtual CommentType entry_type() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point entry_time()
        const = 0;

    [[nodiscard]] virtual bool isService() const = 0;
    bool isHost() const { return !isService(); };
    [[nodiscard]] virtual bool persistent() const = 0;
    [[nodiscard]] virtual CommentSource source() const = 0;
    [[nodiscard]] virtual std::chrono::system_clock::time_point expire_time()
        const = 0;
    [[nodiscard]] virtual bool expires() const = 0;

    [[nodiscard]] virtual const IHost &host() const = 0;
    [[nodiscard]] virtual const IService *service() const = 0;
};

#endif  // Interface_h
