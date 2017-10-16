#include "MockWinApi.h"

// See https://github.com/google/googletest/blob/master/googlemock/docs/CookBook.md#making-the-compilation-faster.
// Defining mock class constructor and destructor in source file should speed up compilation.
MockWinApi::MockWinApi() {}
MockWinApi::~MockWinApi() {}
