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

export interface AttributeAutoCompleter {
  attribute: Attribute
  autocompleterGetter: (key: string | null, isForKey: boolean) => Autocompleter
}

const attribute = defineModel<Attribute>({
  required: true
})
const props = defineProps<{
  autocompleterGetter: (key: string | null, isForKey: boolean) => Autocompleter
}>()

function updateValue(newValue: string | null) {
  attribute.value = { key: attribute.value.key, value: newValue }
}
</script>

<template>
  <div>
    <div>
      <FormAutocompleter
        v-model="attribute.key"
        :autocompleter="props.autocompleterGetter(attribute.key, true)"
        :placeholder="_t('Attribute key')"
      />
    </div>
    <div>
      <FormAutocompleter
        :model-value="attribute.value"
        :autocompleter="props.autocompleterGetter(attribute.key, false)"
        :placeholder="_t('Attribute value')"
        @update:model-value="updateValue"
      />
    </div>
  </div>
</template>

<style scoped>
div {
  display: inline-block;
  margin-right: 1px;
}
</style>
