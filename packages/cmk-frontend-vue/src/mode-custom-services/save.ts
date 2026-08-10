/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Persistence for the OTel custom-service creation wizard.
//
// A custom service is a WATO rule in the `special_agents:custom_query_metric_backend`
// ruleset, created via the production config-entity path (the same one the graph
// designer's create-service slide-in uses): POST to
// /domain-types/configuration_entity/collections/all. The assigned host is carried
// as the rule's explicit-hosts condition; the service name lives in the value's
// service_name_template. `special_agents:*` is a host ruleset, so there is no
// service condition.
//
// We fetch the rule catalog's default frontend value (getSchema) to obtain a valid
// base (generated rule id + condition skeleton), then patch in the metric value and
// the host condition before creating.
import usei18n from 'cmk-ui-library/lib/i18n'

import { type Payload, configEntityAPI } from '@/form'

import type { ServiceModel } from './types'

const { _t } = usei18n()

const ENTITY_TYPE = 'rule_form_spec'
const ENTITY_TYPE_SPECIFIER = 'special_agents:custom_query_metric_backend'

// Percentile fallback for gauge/sum consolidations, which carry no percentile of
// their own (it only applies to histograms).
const DEFAULT_HISTOGRAM_PERCENTILE = 90

export interface SaveResult {
  ok: boolean
  error?: string
}

function asRecord(value: unknown): Record<string, unknown> {
  return value as Record<string, unknown>
}

export async function createCustomService(model: ServiceModel): Promise<SaveResult> {
  if (model.metricName === null) {
    return { ok: false, error: _t('No metric selected.') }
  }
  if (model.hostName === null || model.hostName.trim() === '') {
    return { ok: false, error: _t('Please assign the custom service to a host.') }
  }

  const { defaultValues } = await configEntityAPI.getSchema(ENTITY_TYPE, ENTITY_TYPE_SPECIFIER)

  // structuredClone keeps the fetched defaults (rule id, condition skeleton) intact.
  const data = structuredClone(defaultValues) as Payload

  asRecord(data.value).value = {
    metric_backend_custom_query: [
      {
        metric_name: model.metricName,
        attribute_filter: model.attributeFilter,
        aggregation_lookback: model.consolidation.lookback_seconds,
        aggregation_histogram_percentile:
          'percentile' in model.consolidation
            ? model.consolidation.percentile
            : DEFAULT_HISTOGRAM_PERCENTILE,
        service_name_template: model.serviceName
      }
    ]
  }

  // conditions.type is a cascading choice: ['explicit', { explicit_hosts, ... }].
  const conditionChoice = asRecord(data.conditions).type as [string, Record<string, unknown>]
  const explicit = conditionChoice[1]
  explicit.explicit_hosts = { value: [model.hostName], negate: false }

  const result = await configEntityAPI.createEntity(ENTITY_TYPE, ENTITY_TYPE_SPECIFIER, data)
  if (result.type === 'error') {
    const first = result.validationMessages[0]
    return { ok: false, error: first ? first.message : _t('Failed to create the custom service.') }
  }
  return { ok: true }
}
