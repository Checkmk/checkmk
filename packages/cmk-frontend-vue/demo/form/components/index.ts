/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import DemoEmpty from '@demo/_demo/DemoEmpty.vue'

import type { Page } from '@demo/_demo/page'
import { Folder } from '@demo/_demo/page'

import { pages as formsPages } from './forms'

export const pages: Array<Folder | Page> = [new Folder('forms', DemoEmpty, formsPages)]
