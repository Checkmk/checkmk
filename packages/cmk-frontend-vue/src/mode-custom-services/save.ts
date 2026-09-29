/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

import { type SaveResult, saveCustomServiceDefinition, updateCustomServiceDefinition } from './api'
import {
  aggregationProblem,
  buildCustomServiceDefinition,
  buildCustomServiceUpdate
} from './definition'
import type { ServiceModel } from './types'

const { _t } = usei18n()

export type { SaveResult }

type CompleteModel = ServiceModel & { metricName: string; hostName: string }

type Validated = { ok: true; model: CompleteModel } | { ok: false; error: string }

/** What the endpoint would reject, refused here so the reason names the field. */
function validate(model: ServiceModel): Validated {
  const { metricName, hostName } = model
  if (metricName === null) {
    return { ok: false, error: _t('No metric selected.') }
  }
  if (hostName === null || hostName.trim() === '') {
    return { ok: false, error: _t('Please assign the custom service to a host.') }
  }
  switch (aggregationProblem(model.consolidation)) {
    case 'thresholds_missing':
      return { ok: false, error: _t('Please enter the thresholds of the selected consolidation.') }
    case 'thresholds_out_of_order':
      return { ok: false, error: _t('The lower threshold must be below the upper threshold.') }
  }
  return { ok: true, model: { ...model, metricName, hostName } }
}

export async function createCustomService(model: ServiceModel): Promise<SaveResult> {
  const validated = validate(model)
  if (!validated.ok) {
    return validated
  }
  return await saveCustomServiceDefinition(buildCustomServiceDefinition(validated.model))
}

export async function updateCustomService(
  configurationName: string,
  model: ServiceModel,
  etag: string
): Promise<SaveResult> {
  const validated = validate(model)
  if (!validated.ok) {
    return validated
  }
  return await updateCustomServiceDefinition(
    configurationName,
    buildCustomServiceUpdate(validated.model),
    etag
  )
}
