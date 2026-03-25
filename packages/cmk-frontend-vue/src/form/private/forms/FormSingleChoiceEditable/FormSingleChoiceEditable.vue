<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConfigEntityType } from 'cmk-shared-typing/typescript/configuration_entity'
import type { SingleChoiceEditable } from 'cmk-shared-typing/typescript/vue_formspec_components'

import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown'

import { type ValidationMessages, useValidation } from '@/form/private/validation'

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
</script>

<template>
  <div>
    <CmkConfigurationEntityDropdown
      v-model="selectedObjectId"
      :config-entity-type="spec.config_entity_type as ConfigEntityType"
      :config-entity-type-specifier="spec.config_entity_type_specifier"
      :initial-elements="spec.elements.map((e) => ({ name: e.name, title: e.title }))"
      :allow-editing-existing-elements="spec.allow_editing_existing_elements"
      :label="spec.title"
      :validation="validation"
    />
  </div>
</template>
