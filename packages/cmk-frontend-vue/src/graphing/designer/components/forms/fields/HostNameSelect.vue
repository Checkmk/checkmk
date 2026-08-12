<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import DesignerField from '../DesignerField.vue'

const {
  modelValue,
  required = false,
  errors
} = defineProps<{
  modelValue: string | null
  required?: boolean
  errors: TranslatedString[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { _t } = usei18n()

const hostAutocompleter: Autocompleter = {
  fetch_method: 'rest_autocomplete',
  data: { ident: 'monitored_hostname', params: { strict: true } }
}
</script>

<template>
  <DesignerField
    v-slot="{ controlId, describedBy, invalid }"
    :label="_t('Host name')"
    :required="required"
    :errors="errors"
  >
    <FormAutocompleter
      :id="controlId"
      :model-value="modelValue"
      :autocompleter="hostAutocompleter"
      :size="0"
      :placeholder="_t('Select host')"
      width="wide"
      floating
      :has-error="invalid"
      :described-by="describedBy"
      @update:model-value="emit('update:modelValue', $event)"
    />
  </DesignerField>
</template>
