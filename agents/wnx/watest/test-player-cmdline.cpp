// test-plugin-cmdline.cpp

//
#include "pch.h"

#include "carrier.h"
#include "common/cfg_info.h"
#include "common/cmdline_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "player.h"
#include "player_api.h"
#include "read_file.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::player {  // to be friendly for wtools classes
TEST(PlayerMainTest, wMain) {
    using namespace cma::player;
    using namespace cma::exe::cmdline;
    wchar_t const *help[] = {kHelpParam};
}

}  // namespace cma::player
