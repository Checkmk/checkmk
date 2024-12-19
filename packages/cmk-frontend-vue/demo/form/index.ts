/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import DemoPassThrough from '@demo/_demo/DemoPassThrough.vue'

import DemoFormAll from './DemoFormAll.vue'

import { pages as componentPages } from './components'
import { Page, Folder } from '@demo/_demo/page'

export const pages: Array<Folder | Page> = [
  new Folder('components', DemoPassThrough, componentPages),
  new Page('all', DemoFormAll)
]
