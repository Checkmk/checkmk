<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormSingleChoiceEditableEditAsync from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import type { SingleChoiceEditable } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { onMounted, ref, toRaw } from 'vue'
import { configEntityAPI, type Payload } from '@/form/components/utils/configuration_entity'
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import CmkDropdown from '@/components/CmkDropdown.vue'
import FormButton from './FormButton.vue'

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

const choices = ref<Array<{ title: string; name: string }>>(
  structuredClone(toRaw(props.spec.elements))
)

const slideInObjectId = ref<OptionId | null>(null)
const slideInOpen = ref<boolean>(false)

onMounted(async () => {
  const entities = await configEntityAPI.listEntities(
    props.spec.config_entity_type as ConfigEntityType,
    props.spec.config_entity_type_specifier
  )
  choices.value = entities.map((entity) => ({
    name: entity.ident,
    title: entity.description
  }))
})

const slideInAPI = {
  getSchema: async () => {
    return (
      await configEntityAPI.getSchema(
        props.spec.config_entity_type as ConfigEntityType,
        props.spec.config_entity_type_specifier
      )
    ).schema
  },
  getData: async (objectId: OptionId | null) => {
    if (objectId === null) {
      return (
        await configEntityAPI.getSchema(
          props.spec.config_entity_type as ConfigEntityType,
          props.spec.config_entity_type_specifier
        )
      ).defaultValues
    }
    const result = await configEntityAPI.getData(
      props.spec.config_entity_type as ConfigEntityType,
      objectId
    )
    return result
  },
  setData: async (objectId: OptionId | null, data: Payload) => {
    if (objectId === null) {
      return await configEntityAPI.createEntity(
        props.spec.config_entity_type as ConfigEntityType,
        props.spec.config_entity_type_specifier,
        data
      )
    }
    return await configEntityAPI.updateEntity(
      props.spec.config_entity_type as ConfigEntityType,
      props.spec.config_entity_type_specifier,
      objectId,
      data
    )
  }
}

function slideInSubmitted(event: { ident: string; description: string }) {
  data.value = event.ident
  if (choices.value.find((object) => object.name === event.ident) === undefined) {
    choices.value.push({ title: event.description, name: event.ident })
  } else {
    choices.value = choices.value.map((choice) =>
      // Update description of existing object
      choice.name === event.ident ? { title: event.description, name: event.ident } : choice
    )
  }
  closeSlideIn()
}

function closeSlideIn() {
  slideInOpen.value = false
}

function openSlideIn(objectId: null | OptionId) {
  slideInObjectId.value = objectId
  slideInOpen.value = true
  error.value = null
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { ErrorBoundary, error } = useErrorBoundary()
</script>

<template>
  <div>
    <CmkDropdown
      v-model:selected-option="selectedObjectId"
      :options="{
        type: props.spec.elements.length > 5 ? 'filtered' : 'fixed',
        suggestions: choices
      }"
      :input-hint="spec.i18n.no_selection"
      :no-elements-text="spec.i18n.no_objects"
      :label="spec.title"
      class="fsce__dropdown"
      required
    />
    <template v-if="spec.allow_editing_existing_elements">
      <FormButton
        v-show="selectedObjectId !== null"
        icon="edit"
        @click="openSlideIn(selectedObjectId)"
      >
        {{ spec.i18n.edit }}
      </FormButton>
      <CmkSpace v-show="selectedObjectId !== null" />
    </template>
    <FormButton @click="openSlideIn(null)">
      {{ spec.i18n.create }}
    </FormButton>

    <CmkSlideInDialog
      :open="slideInOpen"
      :header="{
        title:
          slideInObjectId === null ? spec.i18n.slidein_new_title : spec.i18n.slidein_edit_title,
        closeButton: true
      }"
      @close="closeSlideIn"
    >
      <ErrorBoundary>
        <FormSingleChoiceEditableEditAsync
          :object-id="slideInObjectId"
          :api="slideInAPI"
          :i18n="{
            save_button: spec.i18n.slidein_save_button,
            cancel_button: spec.i18n.slidein_cancel_button,
            create_button: spec.i18n.slidein_create_button,
            loading: spec.i18n.loading,
            validation_error: spec.i18n.validation_error,
            fatal_error: spec.i18n.fatal_error,
            permanent_choice_warning: spec.i18n.permanent_change_warning,
            permanent_choice_warning_dismissal: spec.i18n.permanent_change_warning_dismiss
          }"
          @cancel="closeSlideIn"
          @submitted="slideInSubmitted"
        />
      </ErrorBoundary>
    </CmkSlideInDialog>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.fsce__dropdown {
  margin-right: 1em;
}
</style>
