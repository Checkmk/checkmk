<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import { ref } from 'vue'
// eslint-disable-next-line @typescript-eslint/naming-convention
import type * as vue_formspec_components from '@/form/components/vue_formspec_components'
import FormCascadingSingleChoice from '@/form/components/forms/FormCascadingSingleChoice.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<vue_formspec_components.CascadingSingleChoice>({
  type: 'cascading_single_choice',
  title: 'some title',
  help: 'some help',
  validators: [],
  label: 'some label',
  layout: 'horizontal',
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
        validators: [],
        input_hint: 'nestedStringInputHint',
        field_size: 'SMALL',
        autocompleter: null
      } as vue_formspec_components.String
    }
  ]
})
const data = ref<[string, unknown]>(['stringChoice', 'some string'])
</script>

<template>
  <FormCascadingSingleChoice v-model:data="data" :spec="spec" :backend-validation="[]" />
</template>
