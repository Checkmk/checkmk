<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

defineProps<{ screenshotMode: boolean }>()

const value1 = ref<boolean>(true)
const value2 = ref<boolean>(false)
const value3 = ref<boolean>(false)
const value4 = ref<boolean>(false)
const value5 = ref<boolean>(false)
const value6 = ref<boolean>(false)
const value7 = ref<boolean>(false)

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
      <CmkCheckbox v-model="value1" label="some checkbox" :external-errors="externalErrors" />
    </li>
    <li>
      <CmkCheckbox v-model="value2" label="some other checkbox" />
    </li>
    <li>checkbox without label: <CmkCheckbox v-model="value3" /></li>
    <li>
      <!-- testing vertical alignment -->
      two in one large line:<CmkCheckbox v-model="value4" /><span style="font-size: 30px"
        >vertical element<CmkCheckbox v-model="value5"
      /></span>
    </li>
    <li :style="{ width: '30em' }">
      <CmkCheckbox
        v-model="value6"
        label="Checkbox with help which wraps help icon with last word"
        :help="'foo bar'"
      />
    </li>
    <li>Checkboxes with vertical padding bottom/both/top next to one without:</li>
    <ul>
      <li>
        <CmkCheckbox v-model="value7" :padding="'bottom'" />&nbsp;<CmkCheckbox v-model="value7" />
      </li>
      <li>
        <CmkCheckbox v-model="value7" :padding="'both'" />&nbsp;<CmkCheckbox v-model="value7" />
      </li>
      <li>
        <CmkCheckbox v-model="value7" :padding="'top'" />&nbsp;<CmkCheckbox v-model="value7" />
      </li>
    </ul>
  </ul>
</template>
