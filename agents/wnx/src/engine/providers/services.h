
//

#pragma once
#ifndef services_h__
#define services_h__

#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class Services : public Asynchronous {
public:
    Services() : Asynchronous(cma::section::kServices) {}
    Services(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

private:
    virtual std::string makeBody() const override;
};

}  // namespace provider

};  // namespace cma

#endif  // services_h__
