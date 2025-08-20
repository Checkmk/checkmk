/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'

export type StepId = StageInformation['finished'][number]

export function markStepAsComplete(markStepCompletedUrl: string, stepId: StepId): void {
  window.open(markStepCompletedUrl.replace('PLACEHOLDER', stepId), 'main')
}
