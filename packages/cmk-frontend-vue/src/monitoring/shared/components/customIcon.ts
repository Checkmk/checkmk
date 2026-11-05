/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'

import type { CustomIcon } from '@/monitoring/shared/api/types'

/** What CmkDynamicIcon renders for a custom icon: an uploaded image or a built-in icon. */
export const customIconSpec = (icon: CustomIcon): DynamicIcon =>
  icon.icon_path === undefined
    ? { type: 'default_icon', id: icon.icon_name }
    : { type: 'user_icon', id: icon.icon_name, path: icon.icon_path }
