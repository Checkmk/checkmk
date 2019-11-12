#ifndef TableQueryHelper_h
#define TableQueryHelper_h

#include <list>
#include <string>
class Table;

namespace mk {
namespace test {

std::string query(Table& table, const std::list<std::string>& q);

}  // namespace test
}  // namespace mk

#endif
