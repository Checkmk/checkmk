<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { LabelValueItem } from '@/dashboard/components/Wizard/types'

import { useLabelValueAutocomplete } from './useLabelValueAutocomplete'

const { _t } = usei18n()

interface CmkAutocompleteServiceProps {
  context: ConfiguredFilters
}

const props = defineProps<CmkAutocompleteServiceProps>()
const serviceMetrics = defineModel<LabelValueItem | null>('serviceMetrics', { required: true })

const metricNameAutocompleter = computed(() => {
  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: 'monitored_metrics',
      params: {
        show_independent_of_context: true,
        escape_regex: false,
        strict: true,
        context: props.context
      }
    }
  }
  return autocompleter
})

const { internalValue, pending } = useLabelValueAutocomplete(
  serviceMetrics,
  metricNameAutocompleter
)
</script>

<template>
  <FormAutocompleter
    v-model="internalValue"
    :autocompleter="metricNameAutocompleter"
    :size="0"
    :placeholder="_t('Select service metric')"
    :label="_t('Select service metric')"
    :busy="pending"
  />
</template>
