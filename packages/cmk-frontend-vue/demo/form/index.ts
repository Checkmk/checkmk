/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import DemoEmpty from '@demo/_demo/DemoEmpty.vue'
import { Folder, Page } from '@demo/_demo/page'

import DemoFormAll from './DemoFormAll.vue'
import { pages as componentPages } from './components'

export const pages: Array<Folder | Page> = [
  new Folder('components', DemoEmpty, componentPages),
  new Page('all', DemoFormAll)
]
