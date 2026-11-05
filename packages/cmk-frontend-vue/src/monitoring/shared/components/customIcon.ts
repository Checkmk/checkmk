/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'

import type { CustomIcon } from '@/monitoring/shared/api/types'

import type { ActionIcon } from './cell/ActionIcon.vue'

/** What CmkDynamicIcon renders for a custom icon: an uploaded image or a built-in icon. */
export const customIconSpec = (icon: CustomIcon): DynamicIcon =>
  icon.icon_path === undefined
    ? { type: 'default_icon', id: icon.icon_name }
    : { type: 'user_icon', id: icon.icon_name, path: icon.icon_path }

/** The icon of an action menu entry: an uploaded one by its path, a built-in one by its name. */
export const menuEntryIcon = (entry: {
  icon_name: string
  icon_path?: string | undefined
}): ActionIcon =>
  entry.icon_path === undefined
    ? (entry.icon_name as SimpleIcons)
    : { type: 'user_icon', id: entry.icon_name, path: entry.icon_path }
