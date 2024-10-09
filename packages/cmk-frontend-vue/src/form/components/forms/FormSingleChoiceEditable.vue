<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormEditAsync, { type API as SlideInAPI } from '@/components/FormEditAsync.vue'
import AlertBox from '@/components/AlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import SlideIn from '@/components/slidein/SlideIn.vue'
import FormValidation from '@/form/components/FormValidation.vue'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import { immediateWatch } from '@/form/components/utils/watch'
import type { SingleChoiceEditable } from '@/form/components/vue_formspec_components'
import { ref } from 'vue'
import { getConfigEntityAPI, type Payload } from '@/form/components/utils/configuration_entity'
import type { ConfigEntityType } from '@/form/components/configuration_entity'
import DropDown from '@/components/DropDown.vue'

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

const choices = ref<Array<{ name: string; ident: string }>>(
  props.spec.elements.map((element) => ({ name: element.title, ident: element.name }))
)

const error = ref<string | undefined>()

const slideInObjectId = ref<OptionId | null>(null)
const slideInOpen = ref<boolean>(false)

const slideInAPI = ref<SlideInAPI<OptionId, Payload>>()
immediateWatch(
  () => ({
    entityType: props.spec.config_entity_type,
    entityTypeSpecifier: props.spec.config_entity_type_specifier
  }),
  ({ entityType, entityTypeSpecifier }) => {
    const configEntityAPI = getConfigEntityAPI({
      entityType: entityType as ConfigEntityType,
      entityTypeSpecifier
    })
    slideInAPI.value = {
      getSchema: async () => {
        try {
          return (await configEntityAPI.getSchema()).schema
        } catch (e: unknown) {
          error.value = e as string
          throw e
        }
      },
      getData: async (objectId: OptionId | null) => {
        if (objectId === null) {
          return (await configEntityAPI.getSchema()).defaultValues
        }
        const result = await configEntityAPI.getData(objectId)
        return result
      },
      setData: async (objectId: OptionId | null, data: Payload) => {
        if (objectId === null) {
          return await configEntityAPI.createEntity(data)
        }
        return await configEntityAPI.updateEntity(objectId, data)
      }
    }
  }
)

function slideInSubmitted(event: { ident: string; description: string }) {
  data.value = event.ident
  if (choices.value.find((object) => object.ident === event.ident) === undefined) {
    choices.value.push({ name: event.description, ident: event.ident })
  } else {
    choices.value = choices.value.map((choice) =>
      // Update description of existing object
      choice.ident === event.ident ? { name: event.description, ident: event.ident } : choice
    )
  }
  closeSlideIn()
}

function closeSlideIn() {
  slideInOpen.value = false
  error.value = undefined
}

function openSlideIn(objectId: null | OptionId) {
  slideInObjectId.value = objectId
  slideInOpen.value = true
}
</script>

<template>
  <div>
    <!-- TODO the resulting data of the ternary operator for the input_hint switch not being watched  -->
    <DropDown
      v-model:selected-option="selectedObjectId"
      :options="choices"
      :input_hint="choices.length === 0 ? spec.i18n.no_objects : spec.i18n.no_selection"
      :disabled="choices.length === 0"
      class="fsce__dropdown"
    />
    <CmkButton
      v-if="selectedObjectId !== null"
      type="tertiary"
      @click="openSlideIn(selectedObjectId)"
    >
      {{ spec.i18n.edit }}
    </CmkButton>
    <CmkButton type="tertiary" @click="openSlideIn(null)">
      {{ spec.i18n.create }}
    </CmkButton>

    <!-- TODO the resulting data of the ternary operator for the title switch not being watched  -->
    <SlideIn
      :open="slideInOpen"
      :header="{
        title:
          slideInObjectId === null ? spec.i18n.slidein_new_title : spec.i18n.slidein_edit_title,
        closeButton: true
      }"
      @close="closeSlideIn"
    >
      <AlertBox v-if="error" variant="error">
        {{ spec.i18n.fatal_error }}
        {{ error }}
      </AlertBox>
      <FormEditAsync
        v-if="slideInAPI !== undefined"
        :object-id="slideInObjectId"
        :api="slideInAPI"
        :i18n="{
          save_button: spec.i18n.slidein_save_button,
          cancel_button: spec.i18n.slidein_cancel_button,
          create_button: spec.i18n.slidein_create_button,
          loading: spec.i18n.loading,
          validation_error: spec.i18n.validation_error,
          fatal_error: spec.i18n.fatal_error
        }"
        @cancel="closeSlideIn"
        @submitted="slideInSubmitted"
      />
    </SlideIn>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>

<style scoped>
.fsce__dropdown {
  margin-right: 1em;
}
</style>
