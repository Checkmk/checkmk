<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  GraphLineQueryAttribute,
  GraphLineQueryAttributes
} from 'cmk-shared-typing/typescript/graph_designer'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkList from '@/components/CmkList'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormMetricBackendCustomQueryAttribute, {
  type Attribute
} from './FormMetricBackendAttribute.vue'
import type { AutoCompleteContext } from './FormMetricBackendAttributes.vue'

const props = withDefaults(
  defineProps<{
    label: string
    keyIdent: string
    valueIdent: string
    disableValuesOnEmptyKey?: boolean
    indent?: boolean
    orientation?: 'horizontal' | 'vertical'
    strict?: boolean
    getAutoCompleterContext: (
      key: string | null,
      ignoreExisting: { index: number } | null
    ) => AutoCompleteContext
  }>(),
  {
    disableValuesOnEmptyKey: false,
    indent: false,
    orientation: 'horizontal',
    strict: false
  }
)

const validation = defineModel<string[]>('validation', { default: [] })

const attributes = defineModel<GraphLineQueryAttributes>({ default: [] })

const valueCellComponent = computed(() => (props.indent ? CmkIndent : 'div'))
const labelCellComponent = computed(() => (props.indent ? 'div' : 'td'))
const valueCellWrapperComponent = computed(() => (props.indent ? 'div' : 'td'))

const currentAttribute = ref<Attribute>({
  key: null,
  value: null
})

function clearAttributeSelection() {
  currentAttribute.value = { key: null, value: null }
}

defineExpose({ clearAttributeSelection })

const attributeAutoCompleter = (
  key: string | null,
  isForKey: boolean,
  ignoreExistingIndex: number | null = null
): Autocompleter => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: isForKey ? props.keyIdent : props.valueIdent,
    params: {
      strict: props.strict,
      context: props.getAutoCompleterContext(
        isForKey ? null : key,
        ignoreExistingIndex !== null ? { index: ignoreExistingIndex } : null
      )
    }
  }
})

function addAttribute() {
  if (
    currentAttribute.value.key !== '' &&
    currentAttribute.value.key !== null &&
    currentAttribute.value.value !== '' &&
    currentAttribute.value.value !== null
  ) {
    attributes.value.push(currentAttribute.value as GraphLineQueryAttribute)
    currentAttribute.value = { key: null, value: null }
    validation.value = []
  }
}

function deleteAttribute(index: number) {
  attributes.value.splice(index, 1)
  currentAttribute.value = { key: null, value: null }
  validation.value = []
  return true
}
</script>

<template>
  <tr>
    <component
      :is="labelCellComponent"
      class="metric-backend-form-metric-backend-attribute-section__label-cell"
    >
      {{ label }}
    </component>
    <component :is="valueCellWrapperComponent">
      <component :is="valueCellComponent">
        <FormValidation :validation="validation" />
        <CmkList
          :items-props="{ itemData: attributes }"
          :orientation="orientation"
          :try-delete="deleteAttribute"
        >
          <template #item-props="{ index, itemData }">
            <FormMetricBackendCustomQueryAttribute
              :model-value="itemData"
              :autocompleter-getter="
                (key: string | null, isForKey: boolean) =>
                  attributeAutoCompleter(key, isForKey, index)
              "
              :disable-values-on-empty-key="disableValuesOnEmptyKey"
              @update:model-value="addAttribute"
            />
          </template>
        </CmkList>
        <FormMetricBackendCustomQueryAttribute
          v-model="currentAttribute"
          :autocompleter-getter="attributeAutoCompleter"
          :disable-values-on-empty-key="disableValuesOnEmptyKey"
          @update:model-value="addAttribute"
        />
      </component>
    </component>
  </tr>
</template>

<style scoped>
.metric-backend-form-metric-backend-attribute-section__label-cell {
  vertical-align: top;
}
</style>
