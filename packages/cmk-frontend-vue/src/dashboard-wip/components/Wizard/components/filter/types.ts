/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

export interface FilterEmits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
}

export interface SingleMultiFilterEmits extends FilterEmits {
  (e: 'reset-object-type-filters', objectType: ObjectType): void
}
