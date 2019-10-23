#include "CrashReport.h"
#include <string>
#include <utility>

CrashReport::CrashReport(std::string id, std::string component)
    : _id(std::move(id)), _component(std::move(component)) {}

std::string CrashReport::id() const { return _id; }

std::string CrashReport::component() const { return _component; }
