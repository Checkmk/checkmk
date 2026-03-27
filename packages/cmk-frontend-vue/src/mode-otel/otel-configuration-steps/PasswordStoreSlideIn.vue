<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import type { SetDataResult, ValidationMessages } from '@/lib/configuration_entity_types.ts'
import usei18n from '@/lib/i18n'
import client, { unwrap } from '@/lib/rest-api-client/client'

import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import type { API, Payload } from '@/form/FormEditAsync.vue'
import FormEditAsync from '@/form/FormEditAsync.vue'

import type { PasswordConfig } from './password_store_password.types.ts'

function isPasswordConfig(data: unknown): data is PasswordConfig {
  if (typeof data !== 'object' || data === null) {
    return false
  }
  const d = data as Record<string, unknown>
  const generalProps = d['general_props']
  const passwordProps = d['password_props']
  return (
    typeof generalProps === 'object' &&
    generalProps !== null &&
    typeof (generalProps as Record<string, unknown>)['id'] === 'string' &&
    typeof (generalProps as Record<string, unknown>)['title'] === 'string' &&
    typeof passwordProps === 'object' &&
    passwordProps !== null
  )
}

defineProps<{ open: boolean }>()

const emit = defineEmits<{
  close: []
  created: [data: PasswordConfig]
}>()

const { _t } = usei18n()

async function fetchFormSpec(): Promise<{ schema: FormSpec; defaultValues: Payload }> {
  const data = unwrap(
    await client.GET('/domain-types/form_spec/collections/{entity_type}', {
      params: {
        path: { entity_type: 'passwordstore_password' },
        query: { entity_type_specifier: 'passwordstore_password' }
      }
    })
  )
  return {
    schema: data.extensions!.schema as FormSpec,
    defaultValues: data.extensions!.default_values as Payload
  }
}

const slideInObjectId = ref<string | null>(null)

const api: API<string, PasswordConfig> = {
  getSchema: async () => {
    return (await fetchFormSpec()).schema
  },
  getData: async (_objectId: string | null) => {
    return (await fetchFormSpec()).defaultValues
  },
  setData: async (
    _objectId: string | null,
    data: Record<string, unknown>
  ): Promise<SetDataResult<PasswordConfig>> => {
    if (isPasswordConfig(data)) {
      return { type: 'success', entity: data }
    }
    const validationMessages: ValidationMessages = [
      { location: [], message: _t('Unexpected form data shape.'), replacement_value: data }
    ]
    return { type: 'error', validationMessages }
  }
}
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    :header="{ title: _t('New password'), closeButton: true }"
    @close="emit('close')"
  >
    <FormEditAsync
      :object-id="slideInObjectId"
      :api="api"
      :i18n="{
        save_button: _t('Save'),
        cancel_button: _t('Cancel'),
        create_button: _t('Create'),
        loading: _t('Loading...'),
        validation_error: _t('Could not validate form, errors are shown in the form'),
        fatal_error: _t('A fatal error occurred:'),
        permanent_choice_warning: _t(
          'Changes submitted through this form will be immediately applied to your configuration. However, you may still need to activate them for them to take effect.'
        ),
        permanent_choice_warning_dismissal: _t('Do not show again')
      }"
      @cancel="emit('close')"
      @submitted="(result) => emit('created', result)"
    />
  </CmkSlideInDialog>
</template>
