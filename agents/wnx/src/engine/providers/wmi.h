// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef wmi_h__
#define wmi_h__

#include <chrono>
#include <string>
#include <string_view>

#include "common/wtools.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

namespace wmi {
constexpr char kSepChar = cma::section::kPipeSeparator;
constexpr std::wstring_view kSepString = cma::section::kPipeSeparatorString;
}  // namespace wmi
namespace ohm {
constexpr char kSepChar = ',';
}
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

// separate class - too weak on functionality
// no need to be included in Wmi hierarchy
class SubSection {
public:
    enum class Type {
        sub,  // [name]
        full  //<<<name>>>
    };

    enum class Mode {
        standard,     // in production
        debug_forced  // for testing we could generate only headers
    };
    SubSection(std::string_view name, Type type)
        : uniq_name_(name), type_(type) {
        setupByName();
    }
    virtual ~SubSection() {}

    std::string getUniqName() const noexcept { return uniq_name_; }

    std::string generateContent(Mode mode);

protected:
    // *internal* function which correctly sets
    // all parameters
    void setupByName();
    std::string makeBody();

private:
    std::wstring name_space_;      // WMI namespace "root\\Cimv2" for example
    std::wstring object_;          // WMI Object name
    const std::string uniq_name_;  // unique id of SUB section provider
    std::string cache_;            // used to store WMI data to later reuse
    Type type_;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class WmiProviderTest;
    FRIEND_TEST(WmiProviderTest, SimulationIntegration);
#endif
};

// configuration
SubSection::Type GetSubSectionType(std::string_view name) noexcept;
bool IsHeaderless(std::string_view name) noexcept;

class Wmi : public Asynchronous {
public:
    Wmi(const std::string &name, char separator)
        : Asynchronous(name, separator) {
        setupByName();
    }

    // accessors, mostly for a testing
    const auto object() const { return object_; }
    const auto nameSpace() const { return name_space_; }
    const auto &columns() const { return columns_; }

    virtual bool isAllowedByCurrentConfig() const;

protected:
    // *internal* function which correctly sets
    // all parameters
    void setupByName();
    std::string makeBody() override;

private:
    std::wstring name_space_;  // WMI namespace "root\\Cimv2" for example
    std::wstring object_;      // WMI Object name
    std::string cache_;        // cached data to reuse

    std::vector<std::wstring> columns_;

    std::vector<SubSection>
        sub_objects_;  // Windows WMI Object name for the case when we have

    SubSection::Mode subsection_mode_ = SubSection::Mode::standard;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class WmiProviderTest;
    FRIEND_TEST(WmiProviderTest, SimulationIntegration);
    FRIEND_TEST(WmiProviderTest, SubSectionSimulateExchange_Integration);
#endif
};

// this is proposed API
std::pair<std::string, wtools::WmiStatus> GenerateWmiTable(
    const std::wstring &NameSpace, const std::wstring &Object,
    const std::vector<std::wstring> &Columns, std::wstring_view separator);

std::string WmiCachedDataHelper(std::string &cache_data,
                                const std::string &wmi_data, char separator);
}  // namespace provider

};  // namespace cma

#endif  // wmi_h__
