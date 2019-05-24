
// provides basic api to start and stop service

#pragma once
#ifndef mem_h__
#define mem_h__

#include <string>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class Mem : public Synchronous {
public:
    Mem() : Synchronous(cma::section::kMemName) {}
    Mem(const std::string& Name, char Separator)
        : Synchronous(Name, Separator) {}

private:
    std::string makeBody() override;
};

}  // namespace provider

};  // namespace cma

#endif  // mem_h__
