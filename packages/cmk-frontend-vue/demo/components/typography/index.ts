/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Folder, Page } from '@demo/_demo/page'

import DemoI18n from './DemoI18n.vue'
import DemoTypography from './DemoTypography.vue'

export const pages: Array<Folder | Page> = [
  new Page('typography', DemoTypography),
  new Page('i18n', DemoI18n)
]
