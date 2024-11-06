<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="ObjectIdent, Result">
// TODO: this is a strange hyprid: on the one hand its a building block, on the other hand its dependent on FormEdit, but not part of the form namespace.
// maybe we should move this into src/form/components ? or we rename it to AsyncEditForm and keep it were it is? but the Form prefix is a bit confusing.
// don't forget to adapt the demo!
import type { FormSpec, ValidationMessage } from '@/form/components/vue_formspec_components'
import { ref, toRaw } from 'vue'
import FormEdit from '@/form/components/FormEdit.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
import AlertBox from '@/components/AlertBox.vue'
import { immediateWatch } from '@/lib/watch'

export type Payload = Record<string, unknown>

export type SetDataResult<Result> =
  | { type: 'success'; entity: Result }
  | { type: 'error'; validationMessages: Array<ValidationMessage> }

export type API<ObjectIdent, Result> = {
  getSchema: () => Promise<FormSpec>
  getData: (objectId: ObjectIdent | null) => Promise<Payload>
  setData: (objectId: ObjectIdent | null, data: Payload) => Promise<SetDataResult<Result>>
}

export interface FormEditAsyncProps<ObjectIdent, Result> {
  objectId: ObjectIdent | null
  api: API<ObjectIdent, Result>
  i18n: {
    save_button: string
    cancel_button: string
    create_button: string
    loading: string
    fatal_error: string
    validation_error: string
  }
}

const props = defineProps<FormEditAsyncProps<ObjectIdent, Result>>()

const schema = ref<FormSpec>()
const data = ref<Payload>()

const error = ref<string>()
const backendValidation = ref<Array<ValidationMessage>>([])

async function save() {
  if (data.value === undefined) {
    throw Error('can not save, data is undefined')
  }
  backendValidation.value = []

  error.value = ''
  let result: SetDataResult<Result>
  try {
    result = await props.api.setData(props.objectId, toRaw(data.value))
  } catch (apiError: unknown) {
    error.value = (apiError as Error).toString()
    return
  }

  if (result.type === 'success') {
    emit('submitted', result.entity)
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
  (e: 'submitted', result: Result): void
}>()

async function reloadAll({
  api,
  objectId
}: {
  api: API<ObjectIdent, Result>
  objectId: ObjectIdent | null
}) {
  error.value = ''
  try {
    const [apiData, apiSchema] = await Promise.all([api.getData(objectId), api.getSchema()])
    data.value = apiData
    schema.value = apiSchema
  } catch (apiError: unknown) {
    error.value = (apiError as Error).toString()
  }
}

immediateWatch(() => ({ api: props.api, objectId: props.objectId }), reloadAll)
</script>

<template>
  <div class="edit-object__wrapper">
    <div v-if="!error" class="edit-object__buttons">
      <CmkButtonSubmit @click="save">
        {{
          objectId === undefined ? props.i18n.create_button : props.i18n.save_button
        }}</CmkButtonSubmit
      >
      <CmkSpace />
      <CmkButtonCancel @click="cancel">{{ props.i18n.cancel_button }}</CmkButtonCancel>
      <!-- the validation error could be scrolled out of the viewport, so we have to show an error bar at the top -->
      <AlertBox v-if="backendValidation.length !== 0" variant="error">
        {{ i18n.validation_error }}
      </AlertBox>
    </div>
    <AlertBox v-if="error" variant="error">
      {{ i18n.fatal_error }}
      {{ error }}
      <button @click="() => reloadAll({ api: props.api, objectId: props.objectId })">reload</button>
    </AlertBox>
    <div class="edit-object__content">
      <div v-if="schema !== undefined && !error && data !== undefined">
        <FormEdit v-model:data="data" :spec="schema" :backend-validation="backendValidation" />
      </div>
      <div v-if="schema === undefined && !error">
        <CmkIcon name="load-graph" size="xxlarge" /> {{ i18n.loading }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.edit-object__wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.edit-object__buttons {
  margin-bottom: 1em;
}
.edit-object__content {
  overflow: auto;
  height: 100%;
}
</style>
