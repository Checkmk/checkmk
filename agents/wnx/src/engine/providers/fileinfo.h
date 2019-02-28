
// provides basic api to start and stop service

#pragma once
#ifndef fileinfo_h__
#define fileinfo_h__

#include <filesystem>
#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class FileInfo : public Asynchronous {
public:
    FileInfo() : Asynchronous(cma::section::kFileInfoName, '|') {}

    FileInfo(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

private:
    virtual std::string makeBody() const override;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class FileInfoTest;
    FRIEND_TEST(FileInfoTest, Base);
#endif
};

}  // namespace provider

};  // namespace cma

#endif  // fileinfo_h__
