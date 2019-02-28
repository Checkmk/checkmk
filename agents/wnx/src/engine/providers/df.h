
// provides basic api to start and stop service

#pragma once
#ifndef df_h__
#define df_h__

#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class Df : public Asynchronous {
public:
    Df() : Asynchronous(cma::section::kDfName, '\t') {}

    Df(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

private:
    virtual std::string makeBody() const override;
};

}  // namespace provider

};  // namespace cma

#endif  // df_h__
