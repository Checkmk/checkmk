
//

#pragma once
#ifndef services_h__
#define services_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class Services : public Asynchronous {
public:
    Services() : Asynchronous(cma::section::kServices) {}
    Services(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

private:
    std::string makeBody() override;
};

}  // namespace provider

};  // namespace cma

#endif  // services_h__
