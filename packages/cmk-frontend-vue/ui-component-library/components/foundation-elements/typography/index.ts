/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Folder, Page } from '@ucl/_ucl/types/page'

import UclCmkHeading from './UclCmkHeading.vue'
import UclCmkParagraph from './UclCmkParagraph.vue'

export const pages: Array<Folder | Page> = [
  new Page('CmkHeading', UclCmkHeading),
  new Page('CmkParagraph', UclCmkParagraph)
]
