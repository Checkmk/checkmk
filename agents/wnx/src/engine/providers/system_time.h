
//

#pragma once
#ifndef system_time_h__
#define system_time_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class SystemTime : public Synchronous {
public:
    SystemTime() : Synchronous(cma::section::kSystemTime) {}
    SystemTime(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    std::string makeBody() override;
};

}  // namespace provider

};  // namespace cma

#endif  // system_time_h__
