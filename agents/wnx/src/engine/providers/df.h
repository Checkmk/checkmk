
// provides basic api to start and stop service

#pragma once
#ifndef df_h__
#define df_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class Df : public Asynchronous {
public:
    Df() : Asynchronous(cma::section::kDfName, '\t') {}

    Df(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

private:
    std::string makeBody() override;
};

}  // namespace provider

};  // namespace cma

#endif  // df_h__
