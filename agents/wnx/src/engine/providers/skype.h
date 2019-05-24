
// provides basic api to start and stop service

#pragma once
#ifndef skype_h__
#define skype_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

// mrpe:
class SkypeProvider : public Asynchronous {
public:
    SkypeProvider() : Asynchronous(cma::section::kSkype, ',') {
        delay_on_fail_ = cma::cfg::G_DefaultDelayOnFail;
    }

    SkypeProvider(const std::string_view& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

protected:
    static std::string makeFirstLine();
    static std::wstring makeSubSection(const std::wstring& RegName);
    std::string makeBody() override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class SkypeTest;
    FRIEND_TEST(SkypeTest, Base);
#endif
};

// special API used for testing
namespace internal {
std::vector<std::wstring>* GetSkypeCountersVector();
}  // namespace internal

}  // namespace cma::provider

#endif  // skype_h__
