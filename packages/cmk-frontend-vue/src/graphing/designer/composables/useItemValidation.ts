/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useFilterDefinitions } from 'cmk-ui-library/components/filter'
import { type ComputedRef, computed } from 'vue'

import type { DesignerItem } from '../drafts'
import type { GraphItem } from '../types'
import { isValid } from '../validation'

export interface ItemValidation {
  isValid: (item: DesignerItem) => item is GraphItem
  validItems: ComputedRef<GraphItem[]>
}

/** Which sources the designer rules accept, resolved against the provided filter definitions. */
export function useItemValidation(items: ComputedRef<readonly DesignerItem[]>): ItemValidation {
  const filterDefinitions = useFilterDefinitions()
  const isItemValid = (item: DesignerItem): item is GraphItem => isValid(item, filterDefinitions)
  return {
    isValid: isItemValid,
    validItems: computed(() => items.value.filter(isItemValid))
  }
}
