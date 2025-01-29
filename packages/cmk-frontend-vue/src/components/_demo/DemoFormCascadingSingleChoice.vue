<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref, computed } from 'vue'
// eslint-disable-next-line @typescript-eslint/naming-convention
import type * as vue_formspec_components from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormReadonly from '@/form/components/FormReadonly.vue'
import FormEdit from '@/form/components/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const layout = ref<vue_formspec_components.CascadingSingleChoice['layout']>('horizontal')

const spec = computed(() => {
  return {
    type: 'cascading_single_choice',
    title: 'some title',
    help: 'some help',
    i18n_base: { required: 'required' },
    validators: [],
    label: 'some label',
    layout: layout.value,
    input_hint: '',
    elements: [
      {
        name: 'integerChoice',
        title: 'integerChoiceTitle',
        default_value: 'bar',
        parameter_form: {
          type: 'integer',
          title: 'nestedIntegerTitle',
          label: 'nestedIntegerLabel',
          i18n_base: { required: 'required' },
          help: 'nestedIntegerHelp',
          validators: [],
          input_hint: null,
          unit: null
        } as vue_formspec_components.Integer
      },
      {
        name: 'stringChoice',
        title: 'stringChoiceTitle',
        default_value: 5,
        parameter_form: {
          type: 'string',
          title: 'nestedStringTitle',
          help: 'nestedStringHelp',
          label: null,
          i18n_base: { required: 'required' },
          validators: [],
          input_hint: 'nestedStringInputHint',
          field_size: 'SMALL',
          autocompleter: null
        } as vue_formspec_components.String
      }
    ]
  } as vue_formspec_components.CascadingSingleChoice
})
const data = ref<[string, unknown]>(['stringChoice', 'some string'])
</script>

<template>
  <label
    >layout
    <select v-model="layout">
      <option value="horizontal">horizontal</option>
      <option value="vertical">vertical</option>
    </select>
  </label>
  <hr />
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  <hr />
  <FormReadonly :data="data" :spec="spec" :backend-validation="[]" />
</template>
