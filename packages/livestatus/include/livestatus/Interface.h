// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Interface_h
#define Interface_h

#include <memory>
#include <vector>

class IContact {
public:
    virtual ~IContact() = default;
    [[nodiscard]] virtual const void *handle() const = 0;
};

class IHost {
public:
    virtual ~IHost() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
};

class IService {
public:
    virtual ~IService() = default;
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    [[nodiscard]] virtual const IHost &host() const = 0;
};

class IHostGroup {
public:
    virtual ~IHostGroup() = default;
    [[nodiscard]] virtual const std::vector<std::unique_ptr<const IHost>>
        &hosts() const = 0;
};

class IServiceGroup {
public:
    virtual ~IServiceGroup() = default;
    [[nodiscard]] virtual const std::vector<std::unique_ptr<const IService>>
        &services() const = 0;
};

class IContactGroup {
public:
    virtual ~IContactGroup() = default;
    [[nodiscard]] virtual bool isMember(const IContact &) const = 0;
};

#endif  // Interface_h
