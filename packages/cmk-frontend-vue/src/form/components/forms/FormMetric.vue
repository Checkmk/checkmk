<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'
import FormString from './FormString.vue'
import { computed, ref } from 'vue'

const props = defineProps<{
  spec: FormSpec.Metric
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })

const stringSpec = computed<FormSpec.String>(() => ({
  ...props.spec,
  type: 'string'
}))

const filterHostContext = ref<string>('')

const filterHostSpec: FormSpec.String = {
  ...props.spec,
  type: 'string',
  title: '',
  help: '',
  label: props.spec.i18n.host_filter,
  validators: [],
  input_hint: props.spec.i18n.host_input_hint,
  autocompleter: props.spec.host_filter_autocompleter
}

const filterServiceContext = ref<string>('')

const filterServiceSpec: FormSpec.String = {
  ...props.spec,
  type: 'string',
  title: '',
  help: '',
  label: props.spec.i18n.service_filter,
  validators: [],
  input_hint: props.spec.i18n.service_input_hint,
  autocompleter: props.spec.service_filter_autocompleter
}
</script>
<template>
  <FormString v-model:data="data" :backend-validation="backendValidation" :spec="stringSpec" />
  <div class="dictelement indent">
    <FormString v-model:data="filterHostContext" :backend-validation="[]" :spec="filterHostSpec" />
    <FormString
      v-model:data="filterServiceContext"
      :backend-validation="[]"
      :spec="filterServiceSpec"
    />
  </div>
</template>
