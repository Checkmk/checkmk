<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toRaw, provide } from 'vue'
import type {
  API,
  SetDataResult
} from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'
import FormSingleChoiceEditableEditAsync from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'
import FormEditDispatcher from '@/form/components/FormEditDispatcher.vue'
import type {
  Dictionary,
  FormSpec,
  String,
  ValidationMessage
} from 'cmk-shared-typing/typescript/vue_formspec_components'

defineProps<{ screenshotMode: boolean }>()
import { dispatcherKey } from '@/form/private'

// demo stuff

const reloadCount = ref<number>(0)
const apiDelay = ref<number>(0)
const objectId = ref<ObjectId | null>(null)
const apiError = ref<boolean>(false)
const backendValidation = ref<Array<ValidationMessage>>([])

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
// demo stuff end

type ObjectId = string
type ObjectData = Record<string, unknown>

const api: API<ObjectId, ObjectId> = {
  getData: async (objectId: ObjectId | null): Promise<ObjectData> => {
    console.log('getData', objectId)
    await sleep(apiDelay.value)
    if (apiError.value) {
      throw Error('some error for getData')
    }
    return {}
  },
  setData: async (
    objectId: ObjectId | null,
    data: ObjectData
  ): Promise<SetDataResult<ObjectId>> => {
    console.log('setData', objectId, data)
    await sleep(apiDelay.value)
    if (apiError.value) {
      throw Error('error for setData')
    }
    if (backendValidation.value.length) {
      return { type: 'error', validationMessages: toRaw(backendValidation.value) }
    } else {
      return { type: 'success', entity: 'smth' }
    }
  },
  getSchema: async (): Promise<FormSpec> => {
    await sleep(apiDelay.value)
    if (apiError.value) {
      throw Error('another error for getSchema')
    }
    const dict: Dictionary = {
      type: 'dictionary',
      title: 'dict title',
      validators: [],
      help: 'dict help',
      i18n_base: { required: 'required' },
      no_elements_text: 'no_text',
      additional_static_elements: null,
      elements: [
        {
          name: 'element_name',
          render_only: false,
          group: null,
          required: false,
          default_value: '',
          parameter_form: {
            type: 'string',
            title: 'string title',
            help: 'some string help',
            label: null,
            i18n_base: { required: 'required' },
            validators: [],
            input_hint: null,
            autocompleter: null,
            field_size: 'SMALL'
          } as String
        }
      ],
      groups: []
    }
    return dict as FormSpec
  }
}
// this is a hack to use FormSingleChoiceEditableEditAsync outside a FormEdit context:
// if you need this in production code, we should think about a better solution
provide(dispatcherKey, FormEditDispatcher)
</script>

<template>
  <div class="demo-control">
    <button @click="reloadCount += 1">reload</button>
    <label>
      delay
      <select v-model="apiDelay">
        <option :value="0">No API delay</option>
        <option :value="1000">1 second api delay</option>
      </select>
    </label>
    <label>
      objectId
      <select v-model="objectId">
        <option :value="null">null</option>
        <option :value="'123'">defined</option>
      </select>
    </label>
    <label>
      api errors
      <select v-model="apiError">
        <option :value="false">no error</option>
        <option :value="'true'">always error</option>
      </select>
    </label>
    <label>
      validation errors
      <select v-model="backendValidation">
        <option :value="[]">No error</option>
        <option
          :value="[
            { location: ['element_name'], message: 'error message!', replacement_value: 'dafuck' }
          ]"
        >
          One error
        </option>
      </select>
    </label>
  </div>
  <FormSingleChoiceEditableEditAsync
    :key="reloadCount"
    :object-id="objectId"
    :api="api"
    :i18n="{
      save_button: 'save',
      cancel_button: 'cancel',
      create_button: 'create',
      loading: 'loading data i18n',
      fatal_error: 'unrecoverable error:',
      validation_error: 'i18n validation_error',
      permanent_choice_warning: 'permanent_choice_warning_i18n',
      permanent_choice_warning_dismissal: 'permanent_choice_warning_dismissal_i18n'
    }"
    @cancel="console.log('cancel')"
    @submitted="(event: unknown) => console.log(event)"
  />
</template>

<style scoped>
.demo-control {
  margin-bottom: 1em;
  padding: 1em;
  display: flex;
  flex-direction: column;
}

.demo-control > * {
  display: flex;
  flex: 1 100%;
  margin-bottom: 0.5em;
}
</style>
