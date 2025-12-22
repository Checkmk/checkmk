<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type ConditionChoices,
  type ConditionChoicesValue
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

defineProps<{ screenshotMode: boolean }>()

const spec: ConditionChoices = {
  type: 'condition_choices',
  title: 'some title',
  help: 'some help',
  validators: [],
  condition_groups: {
    group_a: {
      title: 'Group A',
      conditions: [
        { name: 'Condition A1', title: 'Condition A1 Title' },
        { name: 'Condition A2', title: 'Condition A2 Title' }
      ]
    },
    group_b: {
      title: 'Group B',
      conditions: [
        { name: 'Condition B1', title: 'Condition B1 Title' },
        { name: 'Condition B2', title: 'Condition B2 Title' }
      ]
    }
  },
  i18n: {
    choose_operator: 'Choose condition',
    choose_condition: 'Choose operator',
    add_condition_label: 'Add condition group',
    select_condition_group_to_add: 'Select condition group to add',
    no_more_condition_groups_to_add: 'No more condition groups to add',
    eq_operator: 'is',
    ne_operator: 'is not',
    or_operator: 'any of',
    nor_operator: 'none of'
  }
}

const data = ref<ConditionChoicesValue[]>([])

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
