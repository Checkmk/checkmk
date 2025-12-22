/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import { computed, ref } from 'vue'

import { type IconCategory, type IconsWithCategory, type UseIconHandler } from '../types'
import { getIconId } from '../utils'
import { getCategories, getEmblems, getIcons } from './api'

type IconType = 'icon' | 'emblem'

export const useIcons = async (
  iconType: IconType,
  selectedIcon?: string | null
): Promise<UseIconHandler> => {
  const icons = ref<IconsWithCategory[]>([])
  const categories = ref<IconCategory[]>([])

  const icon = ref<DynamicIcon | null>(null)
  const category = ref<string | null>(null)

  const iconsInCategory = computed(() => {
    if (!category.value) {
      return []
    }

    return icons.value.filter((iwc) => iwc.category === category.value).flatMap((iwc) => iwc.icons)
  })

  const promGetIcons = iconType === 'icon' ? getIcons() : getEmblems()
  const promGetCategories = getCategories()
  const [respGetIcons, respGetCategories] = await Promise.allSettled([
    promGetIcons,
    promGetCategories
  ])

  icons.value = respGetIcons.status === 'fulfilled' ? respGetIcons.value : []
  categories.value = (respGetCategories.status === 'fulfilled' ? respGetCategories.value : [])
    .filter((category) => icons.value.some((iwc) => iwc.category === category.id))
    .sort((a, b) => a.alias.localeCompare(b.alias))

  const _selectIcon = (iconId: string | null | undefined) => {
    for (const iwc of icons.value) {
      const foundIcon = iwc.icons.find((ic) => getIconId(ic) === iconId)
      if (foundIcon) {
        icon.value = foundIcon
        category.value = iwc.category
        break
      }
    }
  }

  if (selectedIcon) {
    _selectIcon(selectedIcon)
  } else {
    category.value = categories.value.length > 0 ? categories.value[0]!.id : null
  }

  return {
    allIcons: icons,
    categories,
    icons: iconsInCategory,

    category,
    icon
  }
}
