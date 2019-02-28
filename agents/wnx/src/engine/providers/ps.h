
// provides basic api to start and stop service

#pragma once
#ifndef ps_h__
#define ps_h__

#include <string>

#include "section_header.h"

#include "providers/internal.h"

namespace cma {

namespace provider {

class Ps : public Asynchronous {
public:
    Ps() : Asynchronous(cma::section::kPsName, '\t') {}

    Ps(const std::string& Name, char Separator)
        : Asynchronous(Name, Separator) {}

    virtual void loadConfig();

private:
    virtual std::string makeBody() const override;
    bool use_wmi_;
    bool full_path_;
};

}  // namespace provider

};  // namespace cma

#endif  // ps_h__
