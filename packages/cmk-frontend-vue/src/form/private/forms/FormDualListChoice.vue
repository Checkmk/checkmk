<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type DualListChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkDualList from 'cmk-ui-library/components/CmkDualList'
import type { DualListElement } from 'cmk-ui-library/components/CmkDualList'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { fetchData } from 'cmk-ui-library/components/FormAutocompleter/autocompleters/rest'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref } from 'vue'
import { onMounted, ref } from 'vue'

import { type ValidationMessages, useValidation } from '../validation'

const props = defineProps<{
  spec: DualListChoice
  backendValidation: ValidationMessages
}>()

const { _t } = usei18n()

const data = defineModel<DualListElement[]>('data', { required: true })
const [validation, value] = useValidation<DualListElement[]>(
  data,
  props.spec.validators,
  () => props.backendValidation
)
const localElements = ref<DualListElement[]>(props.spec.elements)
const loading: Ref<boolean> = ref(false) // Loading flag

onMounted(async () => {
  if (!props.spec.autocompleter) {
    return
  }
  loading.value = true
  await fetchData('', props.spec.autocompleter.data).then((result) => {
    localElements.value = result.choices.map(({ id, value }) => ({
      name: id,
      title: value.length > 60 ? `${value.substring(0, 57)}...` : value
    })) as DualListElement[]
    loading.value = false
  })
})
</script>

<template>
  <div class="form-dual-list-choice__container">
    <div v-if="loading" class="form-dual-list-choice__loading">
      <CmkIcon name="load-graph" variant="inline" size="xlarge" />
      <span>{{ _t('Loading') }}</span>
    </div>
    <CmkDualList
      v-model="value"
      :elements="localElements"
      :title="props.spec.title"
      :external-errors="validation"
    />
  </div>
</template>

<style scoped>
.form-dual-list-choice__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
</style>
