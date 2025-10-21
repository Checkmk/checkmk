<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type DualListChoice } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type Ref } from 'vue'
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDualList from '@/components/CmkDualList'
import type { DualListElement } from '@/components/CmkDualList'
import CmkIcon from '@/components/CmkIcon'

import { fetchData } from '../utils/autocompleters/ajax'
import { type ValidationMessages } from '../utils/validation'

const props = defineProps<{
  spec: DualListChoice
  backendValidation: ValidationMessages
}>()

const { _t } = usei18n()

const data = defineModel<DualListElement[]>('data', { required: true })
const localElements = ref<DualListElement[]>(props.spec.elements)
const loading: Ref<boolean> = ref(false) // Loading flag

onMounted(async () => {
  if (!props.spec.autocompleter) {
    return
  }
  loading.value = true
  await fetchData('', props.spec.autocompleter.data).then((result) => {
    localElements.value = result['choices']
      .filter(([id, _]) => id !== null)
      .map(([id, title]) => ({
        name: id,
        title: title.length > 60 ? `${title.substring(0, 57)}...` : title
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
      v-model:data="data"
      :elements="localElements"
      :title="props.spec.title"
      :validators="props.spec.validators"
      :backend-validation="props.backendValidation"
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
