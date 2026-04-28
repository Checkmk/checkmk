<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import { computed, onMounted, onUnmounted, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'
import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import FormEditAsync from '@/form/FormEditAsync.vue'

import { type Payload, configEntityAPI } from './configuration_entity'

const { _t } = usei18n()

const props = defineProps<{
  configEntityType: ConfigEntityType
  configEntityTypeSpecifier: string
  initialElements?: Array<{ name: string; title: string }>
  allowEditingExistingElements?: boolean
  label: string
  inputHint?: string
  validation?: Array<string>
}>()

type OptionId = string

const selectedObjectId = defineModel<OptionId | null>({ required: true })

const choices = ref<Array<{ title: TranslatedString; name: string }>>(
  (props.initialElements ?? []).map((element: { name: string; title: string }) => ({
    title: untranslated(element.title),
    name: element.name
  }))
)
const hideButtonChoices = ref<Array<{ name: string; hide_edit: boolean }>>([])

const slideInObjectId = ref<OptionId | null>(null)
const slideInOpen = ref<boolean>(false)

const abortController = new AbortController()
onUnmounted(() => {
  abortController.abort()
})

onMounted(async () => {
  try {
    const entities = await configEntityAPI.listEntities(
      props.configEntityType,
      props.configEntityTypeSpecifier,
      abortController.signal
    )
    hideButtonChoices.value = entities.map((entity) => ({
      name: entity.ident,
      hide_edit: entity.hide_edit
    }))
    choices.value = entities.map((entity) => ({
      name: entity.ident,
      title: untranslated(entity.description)
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
    return (
      await configEntityAPI.getSchema(
        props.configEntityType,
        props.configEntityTypeSpecifier,
        signal
      )
    ).schema
  },
  getData: async (objectId: OptionId | null, signal?: AbortSignal) => {
    if (objectId === null) {
      return (
        await configEntityAPI.getSchema(
          props.configEntityType,
          props.configEntityTypeSpecifier,
          signal
        )
      ).defaultValues
    }
    return await configEntityAPI.getData(props.configEntityType, objectId, signal)
  },
  setData: async (objectId: OptionId | null, data: Payload) => {
    if (objectId === null) {
      return await configEntityAPI.createEntity(
        props.configEntityType,
        props.configEntityTypeSpecifier,
        data
      )
    }
    return await configEntityAPI.updateEntity(
      props.configEntityType,
      props.configEntityTypeSpecifier,
      objectId,
      data
    )
  }
}

function readableEntityName(): string {
  switch (props.configEntityType) {
    case 'passwordstore_password':
      return _t('password')
    case 'folder':
      return _t('folder')
    case 'oauth2_connection':
      return _t('OAuth2 connection')
    case 'notification_parameter':
      return _t('%{specifier} parameter', { specifier: props.configEntityTypeSpecifier })
    case 'rule_form_spec':
      return _t('rule %{specifier}', { specifier: props.configEntityTypeSpecifier })
  }
}

const resolvedI18n = computed(() => ({
  noSelection: props.inputHint ?? _t('Please select an element'),
  noObjects: _t('No options available'),
  edit: _t('Edit'),
  create: _t('Create new'),
  slideInNewTitle: _t('New %{entity}', { entity: readableEntityName() }),
  slideInEditTitle: _t('Edit %{entity}', { entity: readableEntityName() })
}))

function slideInSubmitted(event: { ident: string; description: string }) {
  selectedObjectId.value = event.ident
  if (choices.value.find((object) => object.name === event.ident) === undefined) {
    choices.value.push({ title: untranslated(event.description), name: event.ident })
    hideButtonChoices.value.push({ name: event.ident, hide_edit: false })
  } else {
    choices.value = choices.value.map((choice) =>
      // Update description of existing object
      choice.name === event.ident
        ? { title: untranslated(event.description), name: event.ident }
        : choice
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
const { CmkErrorBoundary, error } = useCmkErrorBoundary()
</script>

<template>
  <CmkDropdown
    v-model:selected-option="selectedObjectId"
    :options="{
      type: choices.length > 5 ? 'filtered' : 'fixed',
      suggestions: choices
    }"
    :input-hint="untranslated(resolvedI18n.noSelection)"
    :no-elements-text="untranslated(resolvedI18n.noObjects)"
    :label="untranslated(label)"
    class="cmk-configuration-entity-dropdown__dropdown"
    required
  />
  <template
    v-if="
      allowEditingExistingElements &&
      !hideButtonChoices.find((choice) => choice.name === selectedObjectId)?.hide_edit
    "
  >
    <CmkInlineButton
      v-show="selectedObjectId !== null"
      icon="edit"
      @click="openSlideIn(selectedObjectId)"
    >
      {{ resolvedI18n.edit }}
    </CmkInlineButton>
    <CmkSpace v-show="selectedObjectId !== null" />
  </template>
  <CmkInlineButton @click="openSlideIn(null)">
    {{ resolvedI18n.create }}
  </CmkInlineButton>

  <CmkSlideInDialog
    :open="slideInOpen"
    :header="{
      title:
        slideInObjectId === null ? resolvedI18n.slideInNewTitle : resolvedI18n.slideInEditTitle,
      closeButton: true
    }"
    @close="closeSlideIn"
  >
    <CmkErrorBoundary>
      <FormEditAsync
        :object-id="slideInObjectId"
        :api="slideInAPI"
        @cancel="closeSlideIn"
        @submitted="slideInSubmitted"
      />
    </CmkErrorBoundary>
  </CmkSlideInDialog>

  <CmkInlineValidation :validation="props.validation" />
</template>

<style scoped>
.cmk-configuration-entity-dropdown__dropdown {
  margin-right: 1em;
}
</style>
