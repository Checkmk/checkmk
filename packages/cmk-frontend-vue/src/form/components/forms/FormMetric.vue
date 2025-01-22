<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { type ValidationMessages } from '@/form/components/utils/validation'
import FormString from './FormString.vue'
import { computed, ref } from 'vue'

const props = defineProps<{
  spec: FormSpec.Metric
  backendValidation: ValidationMessages
}>()

const data = defineModel<string>('data', { required: true })

const filterHostContext = ref<string>('')

const filterServiceContext = ref<string>('')

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

const hostContext = computed(() => {
  return filterHostContext.value === '' ? {} : { host: { host: filterHostContext.value } }
})

const serviceContext = computed(() => {
  return filterServiceContext.value === ''
    ? {}
    : { service: { service: filterServiceContext.value } }
})

function appendParamsToAutocompleter(
  autocompleter: FormSpec.Autocompleter,
  params: object
): FormSpec.Autocompleter {
  return {
    ...autocompleter,
    data: {
      ...autocompleter.data,
      params: {
        ...autocompleter.data.params,
        ...params
      }
    }
  }
}

const filterServiceSpec = computed<FormSpec.String>(() => ({
  ...props.spec,
  type: 'string',
  title: '',
  help: '',
  label: props.spec.i18n.service_filter,
  validators: [],
  input_hint: props.spec.i18n.service_input_hint,
  autocompleter: appendParamsToAutocompleter(
    props.spec.service_filter_autocompleter,
    filterHostContext.value === ''
      ? {}
      : {
          context: { ...hostContext.value }
        }
  )
}))

const metricSpec = computed<FormSpec.String>(() => ({
  ...props.spec,
  type: 'string',
  autocompleter: props.spec.autocompleter
    ? appendParamsToAutocompleter(
        props.spec.autocompleter,
        filterHostContext.value === '' && filterServiceContext.value === ''
          ? {}
          : {
              context: {
                ...hostContext.value,
                ...serviceContext.value
              }
            }
      )
    : null
}))
</script>

<template>
  <FormString v-model:data="data" :backend-validation="backendValidation" :spec="metricSpec" />
  <div class="dictelement indent">
    <FormString v-model:data="filterHostContext" :backend-validation="[]" :spec="filterHostSpec" />
    <FormString
      v-model:data="filterServiceContext"
      :backend-validation="[]"
      :spec="filterServiceSpec"
    />
  </div>
</template>
