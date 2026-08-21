/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { type SaveResult, saveCustomServiceDefinition } from './api'
import { aggregationProblem, buildCustomServiceDefinition } from './definition'
import type { ServiceModel } from './types'

const { _t } = usei18n()

export type { SaveResult }

export async function createCustomService(model: ServiceModel): Promise<SaveResult> {
  if (model.metricName === null) {
    return { ok: false, error: _t('No metric selected.') }
  }
  if (model.hostName === null || model.hostName.trim() === '') {
    return { ok: false, error: _t('Please assign the custom service to a host.') }
  }
  switch (aggregationProblem(model.consolidation)) {
    case 'thresholds_missing':
      return { ok: false, error: _t('Please enter the thresholds of the selected consolidation.') }
    case 'thresholds_out_of_order':
      return { ok: false, error: _t('The lower threshold must be below the upper threshold.') }
  }

  return await saveCustomServiceDefinition(
    buildCustomServiceDefinition({
      ...model,
      metricName: model.metricName,
      hostName: model.hostName
    })
  )
}
