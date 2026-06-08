<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'
import { CmkRadioButton, CmkRadioGroup } from '@/components/user-input/CmkRadioButton'

defineProps<{ screenshotMode: boolean }>()

const value1 = ref<string>('custom')
const value2 = ref<string>('')
const value3 = ref<string>('week')

const externalErrors = ref<string[]>([])
</script>

<template>
  <p>
    <CmkButton
      @click="
        externalErrors.length > 0
          ? (externalErrors = [])
          : (externalErrors = ['This is an external error'])
      "
      >Toggle external validation error</CmkButton
    >
  </p>

  <hr />
  <ul>
    <li>
      Time range (preselected, with external validation):
      <CmkRadioGroup v-model="value1" label="Time range" :external-errors="externalErrors">
        <CmkRadioButton value="today" label="Today" />
        <CmkRadioButton value="yesterday" label="Yesterday" />
        <CmkRadioButton value="week" label="This week" />
        <CmkRadioButton value="month" label="This month" />
        <CmkRadioButton value="year" label="This year" />
        <CmkRadioButton value="custom" label="Custom" />
      </CmkRadioGroup>
    </li>
    <li>
      Nothing preselected, radios without label:
      <CmkRadioGroup v-model="value2">
        <CmkRadioButton value="a" />
        <CmkRadioButton value="b" />
        <CmkRadioButton value="c" />
      </CmkRadioGroup>
    </li>
    <li>
      With help text and a disabled entry:
      <CmkRadioGroup v-model="value3" label="Time range with help">
        <CmkRadioButton value="week" label="This week" help="The current calendar week." />
        <CmkRadioButton value="month" label="This month" disabled />
      </CmkRadioGroup>
    </li>
    <li>
      Entire group disabled:
      <CmkRadioGroup v-model="value3" label="Disabled time range" disabled>
        <CmkRadioButton value="week" label="This week" />
        <CmkRadioButton value="month" label="This month" />
      </CmkRadioGroup>
    </li>
  </ul>
</template>
