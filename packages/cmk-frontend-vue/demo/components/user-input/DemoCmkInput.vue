<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ComponentInstance, ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

defineProps<{ screenshotMode: boolean }>()
const data = ref('')

type PropTypes = ComponentInstance<typeof CmkInput>['$props']

const fieldSize = ref<NonNullable<PropTypes['fieldSize']>>('LARGE')
const fieldSizeOptions: { name: NonNullable<PropTypes['fieldSize']>; title: string }[] = [
  { name: 'SMALL', title: 'Small' },
  { name: 'MEDIUM', title: 'Medium' },
  { name: 'LARGE', title: 'Large' }
]

const type = ref<NonNullable<PropTypes['type']>>('text')
const typeOptions: { name: NonNullable<PropTypes['type']>; title: string }[] = [
  { name: 'text', title: 'Text' },
  { name: 'number', title: 'Number' },
  { name: 'date', title: 'Date' },
  { name: 'time', title: 'Time' }
]

const externalErrors = ref<string[]>([])
</script>

<template>
  <p>
    <label>
      Type:
      <CmkDropdown
        v-model:selected-option="type"
        :options="{ type: 'fixed', suggestions: typeOptions }"
        label="Type"
      />
    </label>
  </p>
  <p>
    <label>
      Field size (only affects text fields):
      <CmkDropdown
        v-model:selected-option="fieldSize"
        :options="{ type: 'fixed', suggestions: fieldSizeOptions }"
        label="Field Size"
      />
    </label>
  </p>
  <p>
    <CmkButton @click="externalErrors = ['This is an external error']"
      >Show external validation error</CmkButton
    >
  </p>

  <hr />
  <CmkHeading type="h3">Input field:</CmkHeading>
  <br />
  <CmkInput
    v-model="data"
    :placeholder="'Enter a negative number to trigger local validation'"
    :field-size="fieldSize"
    :type="type"
    :aria-label="'foo'"
    :external-errors="externalErrors"
    :validators="[(v: unknown) => ((v as number) < 0 ? ['Value must be positive'] : [])]"
  />
</template>
