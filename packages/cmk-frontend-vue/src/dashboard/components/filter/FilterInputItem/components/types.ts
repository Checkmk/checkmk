/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredValues } from '@/dashboard/components/filter/types.ts'

export interface FilterEmits {
  'update-filter-values': [filterId: string, values: ConfiguredValues]
}

export interface ComponentEmits {
  'update-component-values': [
    componentId: string,
    values: ConfiguredValues,
    mode?: 'merge' | 'overwrite'
  ]
}

export interface FilterComponentProps<T> {
  component: T
  configuredValues: ConfiguredValues | null
}
