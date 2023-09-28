// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef WMI_H
#define WMI_H

#include <string>
#include <string_view>

#include "common/wtools.h"
#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

namespace wmi {
constexpr char kSepChar = cma::section::kPipeSeparator;
constexpr std::wstring_view kSepString = cma::section::kPipeSeparatorString;
}  // namespace wmi
/*
    # wmi_cpuload
    ## system_perf
    ## computer_system
    # ms_exch
    ## msexch_activesync
    ## msexch_availability
    ## msexch_owa
    ## msexch_autodiscovery
    ## msexch_isclienttype
    ## msexch_isstore
    ## msexch_rpcclientaccess
    */

class SubSection {
public:
    enum class Type {
        sub,  // [name]
        full  // <<<name>>>
    };

    enum class Mode {
        standard,  // production
        forced     // testing or feature: headers are in output
    };
    SubSection(std::string_view name, Type type)
        : uniq_name_(name), type_(type) {
        setupByName();
    }

    [[nodiscard]] std::string getUniqName() const noexcept {
        return uniq_name_;
    }

    std::string generateContent(Mode mode);
    [[nodiscard]] auto object() const noexcept { return object_; }
    [[nodiscard]] auto nameSpace() const noexcept { return name_space_; }

protected:
    // internal function which correctly sets all parameters
    void setupByName();
    std::string makeBody();

private:
    std::wstring name_space_;      // WMI namespace "root\\Cimv2" for example
    std::wstring object_;          // WMI Object name
    const std::string uniq_name_;  // unique id of SUB section provider
    std::string cache_;            // used to store WMI data to later reuse
    Type type_;
};

SubSection::Type GetSubSectionType(std::string_view name) noexcept;
bool IsHeaderless(std::string_view name) noexcept;

class WmiBase : public Asynchronous {
public:
    WmiBase(std::string_view name, char separator)
        : WmiBase(name, separator, SubSection::Mode::standard) {}

    WmiBase(std::string_view name, char separator, SubSection::Mode mode)
        : Asynchronous(name, separator), subsection_mode_{mode} {
        setupByName();
    }

    // accessors, mostly for a testing
    auto object() const noexcept { return object_; }
    auto nameSpace() const noexcept { return name_space_; }
    const auto &columns() const noexcept { return columns_; }

    bool isAllowedByCurrentConfig() const override;

    auto subsectionMode() const noexcept { return subsection_mode_; }
    auto delayOnFail() const noexcept { return delay_on_fail_; }

    const auto &subObjects() const noexcept { return sub_objects_; }

protected:
    void setupByName();
    std::string getData();

private:
    std::wstring name_space_;  // WMI namespace "root\\Cimv2" for example
    std::wstring object_;      // WMI Object name
    std::vector<std::wstring> services_;  // required services
    std::string cache_;                   // cached data to reuse

    std::vector<std::wstring> columns_;

    std::vector<SubSection>
        sub_objects_;  // Windows WMI Object name for the case when we have

    SubSection::Mode subsection_mode_{SubSection::Mode::standard};
};

class Wmi final : public WmiBase {
public:
    Wmi(std::string_view name, char separator)
        : WmiBase(name, separator, SubSection::Mode::standard) {}

    Wmi(std::string_view name, char separator, SubSection::Mode mode)
        : WmiBase(name, separator, mode) {}

protected:
    std::string makeBody() override;
};

// this is proposed API
std::pair<std::string, wtools::WmiStatus> GenerateWmiTable(
    std::wstring_view wmi_namespace, const std::wstring &wmi_object,
    const std::vector<std::wstring> &columns_table,
    std::wstring_view separator);

std::string WmiCachedDataHelper(std::string &cache_data,
                                const std::string &wmi_data, char separator);
}  // namespace cma::provider

#endif  // WMI_H
