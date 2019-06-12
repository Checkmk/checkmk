
// provides basic api to start and stop service

#pragma once
#ifndef wmi_h__
#define wmi_h__

#include <chrono>
#include <string>
#include <string_view>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

namespace wmi {
constexpr char kSepChar = '\t';
constexpr std::wstring_view kSepString = L"\t";
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
// #TODO think about noch mal, probably should be integrated with WMI
class SubSection {
public:
    SubSection(const std::string& Name) : uniq_name_(Name) { setupByName(); }
    virtual ~SubSection() {}

    std::string getUniqName() const { return uniq_name_; }

    std::string generateContent();

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

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ProviderTest;
    FRIEND_TEST(ProviderTest, WmiAll);
#endif
};

class Wmi : public Asynchronous {
public:
    Wmi(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {
        setupByName();
    }

    // accessors, mostly for a testing
    const auto object() const { return object_; }
    const auto nameSpace() const { return name_space_; }
    const auto& columns() const { return columns_; }

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

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ProviderTest;
    FRIEND_TEST(ProviderTest, WmiAll);
    FRIEND_TEST(ProviderTest, WmiOhm);
#endif
};

// this is proposed API
enum class WmiStatus { ok, timeout, fail_open, fail_connect, bad_param };
std::pair<WmiStatus, std::string> GenerateWmiTable(
    const std::wstring& NameSpace, const std::wstring& Object,
    const std::vector<std::wstring> Columns, std::wstring_view separator);

}  // namespace provider

};  // namespace cma

#endif  // wmi_h__
