// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// based on idea from fuchsia
// I am not sure still

#pragma once

#include <mutex>

namespace cma {
namespace util {

// ProtectedFields is a useful abstraction for having an object that is
// protected by a mutex.
//
// Example usage:
//
// struct SafeField {
//   int protected_int;
// };
// ProtectedFields<SafeField> protected_fields;
// protected_fields.lock()->protected_int = 100;
// LOG(INFO) << "Current protected_int: " <<
// protected_fields.const_lock()->protected_int;
//
template <class RawData>
class ProtectedFields {
public:
    // ConstLockedFieldsPtr holds a pointer to Fields, as well a
    // unique_lock<mutex>.
    //
    // The semantics of this object is similar to a pointer.
    class LockedRawData {
    public:
        RawData* operator->() { return fields_; }
        RawData& operator*() { return *fields_; }

    private:
        friend class ProtectedFields;
        LockedRawData(std::mutex* mutex, RawData* fields)
            : lock_(*mutex), fields_(fields) {}

        std::unique_lock<std::mutex> lock_;
        RawData* fields_;

    public:
        // Disable copy/assign. Only allow move.
        LockedRawData(LockedRawData&&);
        LockedRawData& operator=(LockedRawData&&);
        LockedRawData& operator=(const LockedRawData&) = delete;
        LockedRawData(const LockedRawData&) = delete;
    };

    // ConstLockedFieldsPtr holds a const pointer to Fields, as well a
    // unique_lock<mutex>.
    //
    // The semantics of this object is similar to a const pointer.
    class ConstLockedRawData {
    public:
        const RawData* operator->() { return fields_; }
        const RawData& operator*() { return *fields_; }

    private:
        friend class ProtectedFields;
        ConstLockedRawData(std::mutex* mutex, const RawData* fields)
            : lock_(*mutex), fields_(fields) {}

        std::unique_lock<std::mutex> lock_;
        const RawData* fields_;

    public:
        // Disable copy/assign. Only allow move.
        ConstLockedRawData(ConstLockedRawData&&);
        ConstLockedRawData& operator=(ConstLockedRawData&&);
        ConstLockedRawData& operator=(const ConstLockedRawData&) = delete;
        ConstLockedRawData(const ConstLockedRawData&) = delete;
    };

    LockedRawData lock() { return LockedRawData(&mutex_, &fields_); }
    ConstLockedRawData const_lock() const {
        return ConstLockedRawData(&mutex_, &fields_);
    }

private:
    mutable std::mutex mutex_;
    RawData fields_;

public:
    ProtectedFields& operator=(const ProtectedFields&) = delete;
    ProtectedFields(const ProtectedFields&) = delete;
    ProtectedFields() {}
};

}  // namespace util
}  // namespace cma
