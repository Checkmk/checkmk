
//

#pragma once
#ifndef check_mk_h__
#define check_mk_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

// Converts address entry from config file into
// expected by check_mk check(only_from) representation.
// Carefully tested to be maximally compatible with legacy
// integrations tests
// on error returns empty string
std::string AddressToCheckMkString(std::string_view entry) noexcept;

class CheckMk : public Synchronous {
public:
    CheckMk() : Synchronous(cma::section::kCheckMk) {}
    CheckMk(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    virtual std::string makeBody() override;
};

}  // namespace provider

};  // namespace cma

#endif  // check_mk_h__
