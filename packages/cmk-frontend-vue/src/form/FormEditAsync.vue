<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="ObjectIdent, Result">
import type {
  FormSpec,
  ValidationMessage
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, toRaw } from 'vue'

import usei18n from '@/lib/i18n'
import { untranslated } from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'
import CmkIcon from '@/components/CmkIcon'
import CmkSpace from '@/components/CmkSpace.vue'

import { useFormEditDispatcher } from '@/form/private/FormEditDispatcher/useFormEditDispatcher'

export type Payload = Record<string, unknown>

export type SetDataResult<Result> =
  | { type: 'success'; entity: Result }
  | { type: 'error'; validationMessages: Array<ValidationMessage> }

export type API<ObjectIdent, Result> = {
  getSchema: () => Promise<FormSpec>
  getData: (objectId: ObjectIdent | null) => Promise<Payload>
  setData: (objectId: ObjectIdent | null, data: Payload) => Promise<SetDataResult<Result>>
}

export interface FormSingleChoiceEditableEditAsyncProps<ObjectIdent, Result> {
  objectId: ObjectIdent | null
  api: API<ObjectIdent, Result>
  i18n: {
    save_button: string
    cancel_button: string
    create_button: string
    loading: string
    fatal_error: string
    validation_error: string
    permanent_choice_warning: string
    permanent_choice_warning_dismissal: string
  }
}

const DISMISSAL_KEY = 'immediate_slideout_change'
const { _t } = usei18n()

const props = defineProps<FormSingleChoiceEditableEditAsyncProps<ObjectIdent, Result>>()

const schema = ref<FormSpec>()
const data = ref<Payload>()
const saving = ref<boolean>(false)

const backendValidation = ref<Array<ValidationMessage>>([])

async function save() {
  if (data.value === undefined) {
    throw Error('can not save, data is undefined')
  }
  backendValidation.value = []

  saving.value = true
  const result: SetDataResult<Result> = await props.api.setData(props.objectId, toRaw(data.value))
  saving.value = false

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
  const [apiData, apiSchema] = await Promise.all([api.getData(objectId), api.getSchema()])
  data.value = apiData
  schema.value = apiSchema
}

immediateWatch(() => ({ api: props.api, objectId: props.objectId }), reloadAll)

// eslint-disable-next-line @typescript-eslint/naming-convention
const { FormEditDispatcher } = useFormEditDispatcher()
// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <div class="form-edit-async__wrapper">
    <CmkErrorBoundary>
      <CmkDialog
        class="form-edit-async__dialog"
        :message="untranslated(props.i18n.permanent_choice_warning)"
        :dismissal_button="{
          title: untranslated(props.i18n.permanent_choice_warning_dismissal),
          key: DISMISSAL_KEY
        }"
      />
      <div class="form-edit-async__buttons">
        <CmkButtonSubmit @click="save">
          {{
            objectId === undefined ? props.i18n.create_button : props.i18n.save_button
          }}</CmkButtonSubmit
        >
        <CmkSpace />
        <CmkButtonCancel @click="cancel">{{ props.i18n.cancel_button }}</CmkButtonCancel>
        <!-- the validation error could be scrolled out of the viewport, so we have to show an error bar at the top -->
        <CmkAlertBox v-if="backendValidation.length !== 0" variant="error">
          {{ i18n.validation_error }}
        </CmkAlertBox>
        <div v-if="saving" class="form-edit-async__saving">
          <CmkIcon name="load-graph" size="large" /> {{ _t('Saving') }}
        </div>
      </div>
      <div v-if="schema !== undefined && data !== undefined">
        <FormEditDispatcher
          v-model:data="data"
          :spec="schema"
          :backend-validation="backendValidation"
        />
      </div>
      <div v-if="schema === undefined">
        <CmkIcon name="load-graph" size="xxlarge" /> {{ i18n.loading }}
      </div>
    </CmkErrorBoundary>
  </div>
</template>

<style scoped>
.form-edit-async__wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-edit-async__dialog {
  margin: 8px 0 24px;
}

.form-edit-async__buttons {
  margin-bottom: 1em;
}

.form-edit-async__saving {
  display: flex;
  align-items: center;
  margin-top: 1em;
  gap: 0.5em;
}
</style>
