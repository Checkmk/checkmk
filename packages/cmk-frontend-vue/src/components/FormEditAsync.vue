<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T, D">
import type { FormSpec, ValidationMessage } from '@/form/components/vue_formspec_components'
import { ref, toRaw } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import CmkButton from '@/components/CmkButton.vue'
import AlertBox from '@/components/AlertBox.vue'
import { immediateWatch } from '@/form/components/utils/watch'

export type SetDataResult<T> =
  | { type: 'success'; objectId: T }
  | { type: 'error'; validationMessages: Array<ValidationMessage> }

export type API<T, D> = {
  getSchema: () => Promise<FormSpec>
  getData: (objectId: T | null) => Promise<D>
  setData: (objectId: T | null, data: D) => Promise<SetDataResult<T>>
}

export interface FormEditAsyncProps<T, D> {
  objectId: T | null
  api: API<T, D>
  i18n: {
    save_button: string
    cancel_button: string
    create_button: string
    loading: string
    fatal_error: string
  }
}

const props = defineProps<FormEditAsyncProps<T, D>>()
const schema = ref<FormSpec>()
const data = ref<D>()
const error = ref<string>()
const backendValidation = ref<Array<ValidationMessage>>([])

async function save() {
  if (data.value === undefined) {
    throw Error('can not save, data is undefined')
  }
  backendValidation.value = []

  error.value = ''
  let result
  try {
    result = await props.api.setData(props.objectId, toRaw(data.value))
  } catch (apiError: unknown) {
    error.value = (apiError as Error).toString()
    return
  }

  if (result.type === 'success') {
    emit('submitted', result.objectId)
  } else if (result.type === 'error') {
    backendValidation.value = result.validationMessages
  } else {
    throw Error(`broken result: did not expect type in ${result}`)
  }
}

function cancel() {
  emit('cancel')
}

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'submitted', objectId: T): void
}>()

async function reload(api: API<T, D>) {
  error.value = ''
  try {
    const [apiData, apiSchema] = await Promise.all([api.getData(props.objectId), api.getSchema()])
    data.value = apiData
    schema.value = apiSchema
  } catch (apiError: unknown) {
    error.value = (apiError as Error).toString()
  }
}

immediateWatch(
  () => props.api,
  async (api) => {
    reload(api)
  }
)
</script>

<template>
  <div v-if="!error" class="edit-object__buttons">
    <CmkButton variant="submit" @click="save">
      {{ objectId === undefined ? props.i18n.create_button : props.i18n.save_button }}</CmkButton
    >
    <CmkButton variant="cancel" @click="cancel">{{ props.i18n.cancel_button }}</CmkButton>
  </div>
  <AlertBox v-if="error" variant="error">
    {{ i18n.fatal_error }}
    {{ error }}
    <button @click="reload(api)">reload</button>
  </AlertBox>
  <div v-if="schema !== undefined && !error">
    <FormEdit v-model:data="data" :spec="schema" :backend-validation="backendValidation" />
  </div>
  <div v-if="schema === undefined && !error">{{ i18n.loading }}</div>
</template>

<style scoped>
.edit-object__buttons {
  margin-bottom: 1em;
}
</style>
