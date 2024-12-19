/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import DemoCmkInput from './DemoCmkInput.vue'
import DemoCmkCheckbox from './DemoCmkCheckbox.vue'

import { type Folder, Page } from '@demo/_demo/page'

export const pages: Array<Folder | Page> = [
  new Page('CmkInput', DemoCmkInput),
  new Page('CmkCheckbox', DemoCmkCheckbox)
]
