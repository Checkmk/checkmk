/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types.ts'

export function showConditionalNotificationStageWidget(
  formData: { [key: number]: StageData } | undefined,
  conditionKey: string
) {
  if (!formData) {
    return false
  }
  for (const stageValue of Object.values(formData)) {
    for (const stageData of Object.values(stageValue) as [string, Record<string, unknown>][]) {
      const [stageType, stageDetails] = stageData
      switch (stageType) {
        case 'specific_events':
          return conditionKey in stageDetails
        case 'all_events':
          return true
        default:
          return false
      }
    }
  }
  return false
}
