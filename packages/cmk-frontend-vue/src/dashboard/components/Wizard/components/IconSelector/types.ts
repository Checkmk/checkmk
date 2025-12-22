/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import type { Ref } from 'vue'

type IconCategoryId = string

export interface UseIconHandler {
  allIcons: Ref<IconsWithCategory[] | null>
  icons: Ref<DynamicIcon[]>
  categories: Ref<IconCategory[]>

  category: Ref<string | null>
  icon: Ref<DynamicIcon | null>
}

export interface IconCategory {
  id: IconCategoryId
  alias: string
}

export interface IconsWithCategory {
  category: IconCategoryId
  icons: DynamicIcon[]
}
