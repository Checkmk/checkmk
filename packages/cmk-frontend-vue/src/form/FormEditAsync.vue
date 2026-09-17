<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="ObjectIdent, Result">
import type {
  Components,
  FormSpec,
  ValidationMessage
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import { type SetDataResult } from 'cmk-ui-library/lib/configuration_entity_types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { onUnmounted, ref, toRaw } from 'vue'

import FormEditDispatcher from '@/form/private/FormEditDispatcher/FormEditDispatcher.vue'

export type Payload = Record<string, unknown>

export type { SetDataResult }

export type API<ObjectIdent, Result> = {
  getSchema: (signal?: AbortSignal) => Promise<FormSpec>
  getData: (objectId: ObjectIdent | null, signal?: AbortSignal) => Promise<Payload>
  setData: (objectId: ObjectIdent | null, data: Payload) => Promise<SetDataResult<Result>>
}

export interface FormSingleChoiceEditableEditAsyncProps<ObjectIdent, Result> {
  objectId: ObjectIdent | null
  api: API<ObjectIdent, Result>
  saveButtonLabel?: TranslatedString
  cancelButtonLabel?: TranslatedString
  createButtonLabel?: TranslatedString
  permanentChoiceWarning?: TranslatedString
}

const DISMISSAL_KEY = 'immediate_slideout_change'
const { _t } = usei18n()

const { isShown: alertShown, dismiss: dismissAlert } = useDismissDialog(DISMISSAL_KEY)

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

const abortController = new AbortController()
onUnmounted(() => {
  abortController.abort()
})

async function reloadAll({
  api,
  objectId
}: {
  api: API<ObjectIdent, Result>
  objectId: ObjectIdent | null
}) {
  try {
    const [apiData, apiSchema] = await Promise.all([
      api.getData(objectId, abortController.signal),
      api.getSchema(abortController.signal)
    ])
    data.value = apiData
    schema.value = apiSchema
  } catch (e) {
    if (abortController.signal.aborted) {
      return
    }
    throw e
  }
}

immediateWatch(() => ({ api: props.api, objectId: props.objectId }), reloadAll)

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <div class="form-edit-async__wrapper">
    <CmkErrorBoundary>
      <CmkAlert
        v-if="alertShown"
        class="form-edit-async__dialog"
        :optional-button="{
          title: _t('Do not show again'),
          icon: 'cancel',
          onclick: dismissAlert
        }"
        :text="
          props.permanentChoiceWarning ??
          _t(
            'Changes submitted through this form will be immediately applied to your configuration. However, you may still need to activate them for them to take effect.'
          )
        "
      />
      <div class="form-edit-async__buttons">
        <CmkButton variant="secondary" @click="save">
          <CmkIcon variant="inline" name="save" />
          {{
            objectId === undefined
              ? (props.createButtonLabel ?? _t('Create'))
              : (props.saveButtonLabel ?? _t('Save'))
          }}</CmkButton
        >
        <CmkSpace />
        <CmkButton @click="cancel">
          <CmkIcon variant="inline" name="cancel" />{{
            props.cancelButtonLabel ?? _t('Cancel')
          }}</CmkButton
        >
        <!-- the validation error could be scrolled out of the viewport, so we have to show an error bar at the top -->
        <CmkAlert
          v-if="backendValidation.length !== 0"
          variant="error"
          :text="_t('Could not validate form, errors are shown in the form')"
        />
        <div v-if="saving" class="form-edit-async__saving">
          <CmkIcon name="load-graph" size="large" /> {{ _t('Saving') }}
        </div>
      </div>
      <div v-if="schema !== undefined && data !== undefined">
        <FormEditDispatcher
          v-model:data="data"
          :spec="schema as Components"
          :backend-validation="backendValidation"
        />
      </div>
      <div v-if="schema === undefined">
        <CmkIcon name="load-graph" size="xxlarge" /> {{ _t('Loading ...') }}
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
