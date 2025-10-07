/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import axios from 'axios'
import type { StageInformation } from 'cmk-shared-typing/typescript/welcome'

export type StepId = StageInformation['finished'][number]

export async function markStepAsComplete(
  markStepCompletedUrl: string,
  stepId: StepId
): Promise<void> {
  return axios.post(markStepCompletedUrl, null, {
    params: {
      _completed_step: stepId
    }
  })
}

export async function getWelcomeStageInformation(
  getStageInformationUrl: string
): Promise<StageInformation | null> {
  return await axios
    .get(getStageInformationUrl)
    .then((response) => {
      return response.data.result as StageInformation
    })
    .catch(() => {
      return null
    })
}
