/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UserIcon } from 'cmk-shared-typing/typescript/icon'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import client, { unwrap } from '@/lib/rest-api-client/client'

import type { IconCategory, IconsWithCategory } from '../types'

type IconCategoryCollectionModel = components['schemas']['IconCategoryCollectionModel']
type IconCollectionModel = components['schemas']['IconCollectionModel']
type IconEmblemCollectionModel = components['schemas']['IconEmblemCollectionModel']

type CategoryIconsMap = {
  [key: string]: IconsWithCategory
}

const _transformIconData = (
  icons: IconCollectionModel | IconEmblemCollectionModel
): IconsWithCategory[] => {
  const result: CategoryIconsMap = {}

  icons.value.sort((a, b) => a.id!.localeCompare(b.id!))

  for (const icon of icons.value) {
    if (result[icon.extensions.category] === undefined) {
      result[icon.extensions.category] = {
        category: icon.extensions.category!,
        icons: []
      }
    }

    const dynamicIcon: UserIcon = {
      type: 'user_icon',
      id: icon.id!,
      path: icon.extensions.path!
    }

    result[icon.extensions.category]!.icons.push(dynamicIcon)
  }

  return Object.values(result)
}

export const getCategories = async (): Promise<IconCategory[]> => {
  const categories = unwrap<IconCategoryCollectionModel>(
    await client.GET('/domain-types/icon_category/collections/all')
  )
  return categories.value.map((cat) => ({ id: cat.id!, alias: cat.title! }))
}

export const getIcons = async (): Promise<IconsWithCategory[]> => {
  const icons = unwrap<IconCollectionModel>(await client.GET('/domain-types/icon/collections/all'))
  return _transformIconData(icons)
}

export const getEmblems = async (): Promise<IconsWithCategory[]> => {
  const icons = unwrap<IconEmblemCollectionModel>(
    await client.GET('/domain-types/icon_emblem/collections/all')
  )
  return _transformIconData(icons)
}
