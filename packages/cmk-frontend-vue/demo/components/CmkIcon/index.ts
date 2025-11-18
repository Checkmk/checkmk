/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@demo/_demo/page'

import DemoCmkIcon from './DemoCmkIcon.vue'
import DemoCmkIconEmblem from './DemoCmkIconEmblem.vue'
import DemoCmkMultitoneIcon from './DemoCmkMultitoneIcon.vue'

export const pages = [
  new Page('CmkIcon', DemoCmkIcon),
  new Page('CmkIconEmblem', DemoCmkIconEmblem),
  new Page('CmkMultitoneIcon', DemoCmkMultitoneIcon)
]
