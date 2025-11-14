<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { List, String } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const spec = ref<List>({
  type: 'list',
  title: 'some title',
  help: 'some help',
  validators: [],
  element_default_value: '',
  editable_order: true,
  add_element_label: 'some add element label',
  remove_element_label: 'some remove label',
  no_element_label: 'some no element label',
  element_template: {
    type: 'string',
    title: 'some title',
    help: 'some help',
    label: null,
    validators: [],
    input_hint: null,
    field_size: 'SMALL',
    autocompleter: null
  } as String
})
const data = ref<Array<string>>([])
const showValidation = ref<boolean>(false)
const validation = computed((): ValidationMessages => {
  if (showValidation.value) {
    return [
      {
        location: [],
        message: 'General Inline Error Message',
        replacement_value: ''
      }
    ]
  } else {
    return []
  }
})
</script>

<template>
  <div>
    <CmkCheckbox v-model="showValidation" label="show validation" />
  </div>
  <FormEdit v-model:data="data" :spec="spec" :backend-validation="validation" />
</template>
