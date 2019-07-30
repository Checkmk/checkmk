
// provides basic api to start and stop service

#pragma once
#ifndef spool_h__
#define spool_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "cma_core.h"
#include "providers/internal.h"
#include "section_header.h"

namespace cma::provider {

// mrpe:
class SpoolProvider : public Asynchronous {
public:
    SpoolProvider() : Asynchronous(cma::section::kSpool) {}

    SpoolProvider(const std::string_view& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

    virtual void updateSectionStatus();

    // empty header
    virtual std::string makeHeader(const std::string_view) const { return {}; }

protected:
    std::string makeBody() override;

#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class MrpeTest;
    FRIEND_TEST(MrpeTest, Base);
#endif
};
bool IsSpoolFileValid(const std::filesystem::path& Path);
bool IsDirectoryValid(const std::filesystem::path& Dir);
}  // namespace cma::provider

#endif  // spool_h__
