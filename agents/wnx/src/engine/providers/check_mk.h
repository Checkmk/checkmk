
//

#pragma once
#ifndef check_mk_h__
#define check_mk_h__

#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class CheckMk : public Synchronous {
public:
    CheckMk() : Synchronous(cma::section::kCheckMk) {}
    CheckMk(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    virtual std::string makeBody() const override;
};

}  // namespace provider

};  // namespace cma

#endif  // check_mk_h__
