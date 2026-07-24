<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { Catalog } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import { type Payload, configEntityAPI } from '@/form'
import FormEditAsync from '@/form/FormEditAsync.vue'

import { metricBackendRuleQuery } from '../metricBackend'
import type { MetricBackendItem } from '../types'

const { open, item, defaultTitle } = defineProps<{
  open: boolean
  item: MetricBackendItem
  defaultTitle: string
}>()

const emit = defineEmits<{
  close: []
}>()

const { _t } = usei18n()
// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const configEntityType: ConfigEntityType = 'rule_form_spec'
const configEntityTypeSpecifier = 'special_agents:custom_query_metric_backend'

function setLockedValue(catalog: Catalog): void {
  for (const element of catalog.elements) {
    if (element.name === 'value') {
      element.locked = {
        message: _t(
          'At this point, rule values cannot be changed. ' +
            'Either go back and change the custom graph as needed or ' +
            'save the rule and edit later via ' +
            'Setup > Agents > Other integrations > Metric backend (custom query).'
        )
      }
    }
  }
}

const ruleFormApi = {
  getSchema: async (signal?: AbortSignal) => {
    const { schema } = await configEntityAPI.getSchema(
      configEntityType,
      configEntityTypeSpecifier,
      signal
    )
    if ('type' in schema && schema.type === 'catalog') {
      setLockedValue(schema as Catalog)
    }
    return schema
  },
  getData: async (_id: null, signal?: AbortSignal) => {
    const { defaultValues } = await configEntityAPI.getSchema(
      configEntityType,
      configEntityTypeSpecifier,
      signal
    )
    // The rule payload nests the rule value under its own `value` topic.
    defaultValues.value = {
      value: { metric_backend_custom_query: [metricBackendRuleQuery(item, defaultTitle)] }
    }
    return defaultValues
  },
  setData: async (_id: null, data: Payload) =>
    await configEntityAPI.createEntity(configEntityType, configEntityTypeSpecifier, data)
}
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    :header="{ title: _t('Add rule: Metric backend (Custom query)'), closeButton: true }"
    @close="emit('close')"
  >
    <CmkErrorBoundary>
      <FormEditAsync
        :object-id="null"
        :api="ruleFormApi"
        :permanent-choice-warning="
          _t(
            'This creates a special agent rule based on the selected custom graph. ' +
              'Note that later changes to the custom graph will not be applied to the special agent rule.'
          )
        "
        @cancel="emit('close')"
        @submitted="emit('close')"
      />
    </CmkErrorBoundary>
  </CmkSlideInDialog>
</template>
