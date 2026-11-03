/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

import type { CustomGraphPublishPermissions } from '@/dashboard/types/page'

export interface CustomGraphPermissions {
  edit: boolean
  publish: CustomGraphPublishPermissions
}

const NO_PERMISSIONS: CustomGraphPermissions = {
  edit: false,
  publish: { allUsers: false, contactGroups: false, sites: false }
}

const customGraphPermissionsKey: InjectionKey<CustomGraphPermissions> =
  Symbol('customGraphPermissions')

export function useProvideCustomGraphPermissions(permissions: CustomGraphPermissions): void {
  provide(customGraphPermissionsKey, permissions)
}

/** Without a provider nothing is permitted, so catalog actions stay hidden. */
export function useInjectCustomGraphPermissions(): CustomGraphPermissions {
  return inject(customGraphPermissionsKey, NO_PERMISSIONS)
}
