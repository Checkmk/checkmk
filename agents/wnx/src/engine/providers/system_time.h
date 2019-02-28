
//

#pragma once
#ifndef system_time_h__
#define system_time_h__

#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class SystemTime : public Synchronous {
public:
    SystemTime() : Synchronous(cma::section::kSystemTime) {}
    SystemTime(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    virtual std::string makeBody() const override;
};

}  // namespace provider

};  // namespace cma

#endif  // system_time_h__
