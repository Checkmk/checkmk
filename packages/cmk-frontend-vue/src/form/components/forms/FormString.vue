<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import { useId } from '@/form/utils'
import { inputSizes } from '../utils/sizes'
import CmkSpace from '@/components/CmkSpace.vue'
import FormRequired from '@/form/private/FormRequired.vue'
import FormLabel from '@/form/private/FormLabel.vue'

defineOptions({
  inheritAttrs: false
})

const props = defineProps<{
  spec: FormSpec.String
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })
const [validation, value] = useValidation<string>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const componentId = useId()
</script>

<template>
  <template v-if="props.spec.label">
    <FormLabel :for="componentId">{{ props.spec.label }}<CmkSpace size="small" /> </FormLabel>
    <FormRequired
      :spec="props.spec"
      :i18n-required="props.spec.i18n_base.required"
      :space="'after'"
    />
  </template>
  <input
    v-if="!spec.autocompleter"
    :id="componentId"
    v-model="value"
    :placeholder="spec.input_hint || ''"
    type="text"
    :size="inputSizes[props.spec.field_size].width"
  />
  <FormAutocompleter
    v-if="spec.autocompleter"
    :id="componentId"
    v-model="value"
    :size="inputSizes[props.spec.field_size].width"
    :resest-input-on-add="false"
    :autocompleter="spec.autocompleter"
    :placeholder="spec.input_hint ?? ''"
    :filter-on="[]"
    :show-icon="true"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
