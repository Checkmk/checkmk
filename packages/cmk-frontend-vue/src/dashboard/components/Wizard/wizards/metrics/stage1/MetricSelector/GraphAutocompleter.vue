<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import { useLabelValueAutocomplete } from '@/dashboard/components/Wizard/components/autocompleters/useLabelValueAutocomplete'
import type { LabelValueItem } from '@/dashboard/components/Wizard/types'
import { ElementSelection } from '@/dashboard/components/Wizard/types'

const { _t } = usei18n()

interface GraphAutocompleterProps {
  hostSelectionMode: ElementSelection
  serviceSelectionMode: ElementSelection
  context: ConfiguredFilters
}

const props = defineProps<GraphAutocompleterProps>()
const metrics = defineModel<LabelValueItem | null>('combinedMetrics', { required: true })

const combinedMetricsAutocompleter = computed<Autocompleter>(() => {
  // A single, specific host/service resolves to exactly one object, so its own graph templates are
  // offered. Any broader selection is a combined graph: match the templates against the objects the
  // configured filters select (an empty context falls back to all templates on the server side).
  if (
    props.hostSelectionMode === ElementSelection.SPECIFIC &&
    props.serviceSelectionMode === ElementSelection.SPECIFIC
  ) {
    return {
      fetch_method: 'rest_autocomplete',
      data: {
        ident: 'available_graph_templates',
        params: {
          show_independent_of_context: true,
          escape_regex: false,
          strict: true,
          context: {}
        }
      }
    }
  }

  return {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: 'combined_graphs',
      params: {
        strict: true,
        datasource: 'services',
        context: props.context
      }
    }
  }
})

const { internalValue, pending } = useLabelValueAutocomplete(metrics, combinedMetricsAutocompleter)

watch(
  () => [props.hostSelectionMode, props.serviceSelectionMode],
  () => {
    metrics.value = null
  },
  { deep: true }
)
</script>

<template>
  <FormAutocompleter
    v-model="internalValue"
    :autocompleter="combinedMetricsAutocompleter"
    :size="0"
    :placeholder="_t('Select graph')"
    :busy="pending"
  />
</template>
