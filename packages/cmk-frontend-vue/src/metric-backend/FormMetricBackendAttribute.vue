<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

const { _t } = usei18n()

export type Attribute = { key: string | null; value: string | null }

const props = defineProps<{
  autocompleterGetter: (key: string | null, isForKey: boolean) => Autocompleter
  disableValuesOnEmptyKey?: boolean
}>()

const attribute = defineModel<Attribute>({
  required: true
})

let previousValue: string | null = attribute.value.value

function onValueUpdate(newValue: string | null) {
  if (attribute.value.value === null) {
    attribute.value.value = previousValue
    return
  }
  previousValue = attribute.value.value
  attribute.value = { key: attribute.value.key, value: newValue }
}
</script>

<template>
  <div>
    <FormAutocompleter
      v-model="attribute.key"
      :autocompleter="props.autocompleterGetter(attribute.key, true)"
      :placeholder="_t('Attribute key')"
      @update:model-value="attribute.value = null"
    />
  </div>
  <div>
    <FormAutocompleter
      v-model="attribute.value"
      :autocompleter="props.autocompleterGetter(attribute.key, false)"
      :placeholder="_t('Attribute value')"
      :disabled="props.disableValuesOnEmptyKey && (attribute.key === null || attribute.key === '')"
      @update:model-value="onValueUpdate"
    />
  </div>
</template>

<style scoped>
div {
  display: inline-block;
  margin-right: 1px;
}
</style>
