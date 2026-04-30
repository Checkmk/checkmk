/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Page } from '@ucl/_ucl/types/page'
import type { Folder } from '@ucl/_ucl/types/page'

import UclI18n from './UclI18n.vue'

export const pages: Array<Folder | Page> = [new Page('I18n', UclI18n)]
