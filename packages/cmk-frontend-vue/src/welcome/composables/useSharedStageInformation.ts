/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'
import { type Ref, ref } from 'vue'

let sharedStageInformation: Ref<StageInformation> | null = null

export function useSharedStageInformation(current: StageInformation): Ref<StageInformation> {
  if (sharedStageInformation === null) {
    sharedStageInformation = ref(current)
  } else {
    sharedStageInformation.value = current
  }
  return sharedStageInformation
}

export function resetSharedStageInformation(): void {
  sharedStageInformation = null
}
