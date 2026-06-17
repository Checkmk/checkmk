<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { SingleChoiceEditable } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, onMounted, onUnmounted, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkSlideInDropdown, {
  type CmkSlideInDropdownChoice
} from '@/components/user-input/CmkSlideInDropdown'

import FormEditAsync from '@/form/FormEditAsync.vue'
import { type EntityDescription, type Payload, configEntityAPI } from '@/form/configuration_entity'
import { type ValidationMessages, useValidation } from '@/form/private/validation'

const { _t } = usei18n()

const props = defineProps<{
  spec: SingleChoiceEditable
  backendValidation: ValidationMessages
}>()

type OptionId = string

const data = defineModel<OptionId | null>('data', { required: true })

const [validation, selectedObjectId] = useValidation<string | null>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const configEntityType = props.spec.config_entity_type as ConfigEntityType
const configEntityTypeSpecifier = props.spec.config_entity_type_specifier

const choices = ref<Array<CmkSlideInDropdownChoice>>(
  props.spec.elements.map((element) => ({
    title: untranslated(element.title),
    name: element.name
  }))
)

const abortController = new AbortController()
onUnmounted(() => {
  abortController.abort()
})

onMounted(async () => {
  try {
    const entities = await configEntityAPI.listEntities(
      configEntityType,
      configEntityTypeSpecifier,
      abortController.signal
    )
    choices.value = entities.map((entity) => ({
      name: entity.ident,
      title: untranslated(entity.description),
      hideEdit: entity.hide_edit
    }))
  } catch (e) {
    if (abortController.signal.aborted) {
      return
    }
    throw e
  }
})

const slideInAPI = {
  getSchema: async (signal?: AbortSignal) => {
    return (await configEntityAPI.getSchema(configEntityType, configEntityTypeSpecifier, signal))
      .schema
  },
  getData: async (objectId: OptionId | null, signal?: AbortSignal) => {
    if (objectId === null) {
      return (await configEntityAPI.getSchema(configEntityType, configEntityTypeSpecifier, signal))
        .defaultValues
    }
    return await configEntityAPI.getData(configEntityType, objectId, signal)
  },
  setData: async (objectId: OptionId | null, payload: Payload) => {
    if (objectId === null) {
      return await configEntityAPI.createEntity(
        configEntityType,
        configEntityTypeSpecifier,
        payload
      )
    }
    return await configEntityAPI.updateEntity(
      configEntityType,
      configEntityTypeSpecifier,
      objectId,
      payload
    )
  }
}

function readableEntityName(): string {
  switch (configEntityType) {
    case 'passwordstore_password':
      return _t('password')
    case 'folder':
      return _t('folder')
    case 'oauth2_connection':
      return _t('OAuth2 connection')
    case 'notification_parameter':
      return _t('%{specifier} parameter', { specifier: configEntityTypeSpecifier })
    case 'rule_form_spec':
      return _t('rule %{specifier}', { specifier: configEntityTypeSpecifier })
  }
}

const newTitle = computed(() => _t('New %{entity}', { entity: readableEntityName() }))
const editTitle = computed(() => _t('Edit %{entity}', { entity: readableEntityName() }))

function slideInSubmitted(event: EntityDescription, close: () => void) {
  selectedObjectId.value = event.ident
  if (choices.value.find((object) => object.name === event.ident) === undefined) {
    choices.value.push({
      title: untranslated(event.description),
      name: event.ident,
      hideEdit: false
    })
  } else {
    choices.value = choices.value.map((choice) =>
      // Update description of existing object, keeping its hideEdit state
      choice.name === event.ident ? { ...choice, title: untranslated(event.description) } : choice
    )
  }
  close()
}
</script>

<template>
  <CmkSlideInDropdown
    v-model="selectedObjectId"
    :choices="choices"
    :allow-editing-existing-elements="spec.allow_editing_existing_elements"
    :label="spec.title"
    :new-title="newTitle"
    :edit-title="editTitle"
    v-bind="spec.input_hint !== undefined ? { inputHint: spec.input_hint } : {}"
    :validation="validation"
  >
    <template #slide-in="{ objectId, close }">
      <FormEditAsync
        :object-id="objectId"
        :api="slideInAPI"
        @cancel="close"
        @submitted="(event: EntityDescription) => slideInSubmitted(event, close)"
      />
    </template>
  </CmkSlideInDropdown>
</template>
