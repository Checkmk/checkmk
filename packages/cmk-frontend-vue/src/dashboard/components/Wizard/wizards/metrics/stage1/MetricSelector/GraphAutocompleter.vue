<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, watch } from 'vue'

import usei18n from '@/lib/i18n'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

import { useLabelValueAutocomplete } from '@/dashboard/components/Wizard/components/autocompleters/useLabelValueAutocomplete'
import type { LabelValueItem } from '@/dashboard/components/Wizard/types'
import { ElementSelection } from '@/dashboard/components/Wizard/types'

const { _t } = usei18n()

interface GraphAutocompleterProps {
  hostSelectionMode: ElementSelection
  serviceSelectionMode: ElementSelection
}

const props = defineProps<GraphAutocompleterProps>()
const metrics = defineModel<LabelValueItem | null>('combinedMetrics', { required: true })

const combinedMetricsAutocompleter = computed(() => {
  const autocompleterId =
    props.hostSelectionMode === ElementSelection.SPECIFIC &&
    props.serviceSelectionMode === ElementSelection.SPECIFIC
      ? 'available_graph_templates'
      : 'graph_template_for_combined_graph'

  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: autocompleterId,
      params: {
        show_independent_of_context: true,
        escape_regex: false,
        strict: true,
        context: {}
      }
    }
  }

  return autocompleter
})

const { internalValue } = useLabelValueAutocomplete(metrics, combinedMetricsAutocompleter)

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
  />
</template>
