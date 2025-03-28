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
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{ screenshotMode: boolean }>()

const layout = ref<vue_formspec_components.CascadingSingleChoice['layout']>('horizontal')
const nestedLayout = ref<vue_formspec_components.CascadingSingleChoice['layout']>('horizontal')

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
    no_elements_text: '',
    elements: [
      {
        name: 'integerChoice',
        title: 'integerChoiceTitle',
        default_value: 5,
        parameter_form: {
          type: 'integer',
          title: 'integerTitle',
          label: 'integerLabel',
          i18n_base: { required: 'required' },
          help: 'integerHelp',
          validators: [],
          input_hint: null,
          unit: null
        } as vue_formspec_components.Integer
      },
      {
        name: 'stringChoice',
        title: 'stringChoiceTitle',
        default_value: 'bar',
        parameter_form: {
          type: 'string',
          title: 'stringTitle',
          help: 'stringHelp',
          label: null,
          i18n_base: { required: 'required' },
          validators: [],
          input_hint: 'stringInputHint',
          field_size: 'SMALL',
          autocompleter: null
        } as vue_formspec_components.String
      },
      {
        name: 'nestedChoice',
        title: 'nestedChoiceTitle',
        default_value: ['stringChoice', 'bar'],
        parameter_form: {
          type: 'cascading_single_choice',
          title: 'nestedChoiceTitle',
          help: 'nestedChoiceHelp',
          label: null,
          i18n_base: { required: 'required' },
          validators: [],
          input_hint: 'nestedChoiceInputHint',
          field_size: 'SMALL',
          layout: nestedLayout.value,
          no_elements_text: '',
          elements: [
            {
              name: 'integerChoice',
              title: 'integerChoiceTitle',
              default_value: 5,
              parameter_form: {
                type: 'integer',
                title: 'integerTitle',
                label: 'integerLabel',
                i18n_base: { required: 'required' },
                help: 'integerHelp',
                validators: [],
                input_hint: null,
                unit: null
              } as vue_formspec_components.Integer
            },
            {
              name: 'stringChoice',
              title: 'stringChoiceTitle',
              default_value: 'bar',
              parameter_form: {
                type: 'string',
                title: 'stringTitle',
                help: 'stringHelp',
                label: 'stringLabel',
                i18n_base: { required: 'required' },
                validators: [],
                input_hint: 'stringInputHint',
                field_size: 'SMALL',
                autocompleter: null
              } as vue_formspec_components.String
            }
          ]
        } as vue_formspec_components.CascadingSingleChoice
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
      <option value="button_group">button group</option>
    </select>
  </label>
  <CmkSpace size="medium" />
  <label
    >nested layout
    <select v-model="nestedLayout">
      <option value="horizontal">horizontal</option>
      <option value="vertical">vertical</option>
      <option value="button_group">button group</option>
    </select>
  </label>
  <hr />
  <h2>Edit</h2>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="[]" />
  <hr />
  <h2>Readonly</h2>
  <FormReadonly :data="data" :spec="spec" :backend-validation="[]" />
</template>
