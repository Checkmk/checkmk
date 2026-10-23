/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkElements } from 'cmk-ui-library/lib/initCmkUi'

import ProfilingFlamegraphApp from './ProfilingFlamegraphApp.vue'
import ProfilingProfilesListApp from './ProfilingProfilesListApp.vue'

const elements: CmkElements = {
  'cmk-profiling-flamegraph': ProfilingFlamegraphApp,
  'cmk-profiling-profiles-list': ProfilingProfilesListApp
}

export default elements
