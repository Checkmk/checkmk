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
    [[nodiscard]] virtual const void *handle() const = 0;
    virtual ~IContact() = default;
};

class IHost {
public:
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    virtual ~IHost() = default;
};

class IService {
public:
    [[nodiscard]] virtual bool hasContact(const IContact &) const = 0;
    virtual ~IService() = default;
    virtual const IHost &host() const = 0;
};

class IHostGroup {
public:
    virtual ~IHostGroup() = default;
    virtual const std::vector<std::unique_ptr<const IHost>> &hosts() const = 0;
};

class IServiceGroup {
public:
    virtual ~IServiceGroup() = default;
    virtual const std::vector<std::unique_ptr<const IService>> &services()
        const = 0;
};

class IContactGroup {
public:
    virtual ~IContactGroup() = default;
    virtual bool isMember(const IContact &) const = 0;
};

#endif  // Interface_h
