<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import SourceFormField from '../SourceFormField.vue'

const {
  modelValue,
  context,
  placeholder,
  required = false,
  showIndependentOfContext = false,
  errors
} = defineProps<{
  modelValue: string | null
  context: ConfiguredFilters
  placeholder?: TranslatedString
  required?: boolean
  /** Resolve metric suggestions from the filter context even without an exact host+service. */
  showIndependentOfContext?: boolean
  errors: TranslatedString[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { _t } = usei18n()

const label = _t('Service metric')

const metricAutocompleter = computed<Autocompleter>(() => ({
  fetch_method: 'rest_autocomplete',
  data: {
    ident: 'monitored_metrics',
    params: { show_independent_of_context: showIndependentOfContext, strict: true, context }
  }
}))
</script>

<template>
  <SourceFormField
    v-slot="{ controlId, describedBy, invalid }"
    :label="label"
    label-variant="name"
    :required="required"
    :errors="errors"
  >
    <FormAutocompleter
      :id="controlId"
      :label="label"
      :model-value="modelValue"
      :autocompleter="metricAutocompleter"
      :size="0"
      :placeholder="placeholder ?? _t('Select metric')"
      width="wide"
      floating
      :has-error="invalid"
      :described-by="describedBy"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </SourceFormField>
</template>
