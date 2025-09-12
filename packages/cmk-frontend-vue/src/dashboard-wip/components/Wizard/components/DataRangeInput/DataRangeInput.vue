<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'

import FixedDataRangeInput from '../FixedDataRangeInput/FixedDataRangeInput.vue'
import { type DataRangeType } from './useDataRangeInput'

const { _t } = usei18n()

const dataRangeType = defineModel<DataRangeType>('dataRangeType', { required: true })
const dataRangeSymbol = defineModel<string>('dataRangeSymbol', { required: true })
const dataRangeMin = defineModel<number>('dataRangeMin', { required: true })
const dataRangeMax = defineModel<number>('dataRangeMax', { required: true })
</script>

<template>
  <div>
    <CmkDropdown
      :selected-option="dataRangeType"
      :label="_t('Select option')"
      :options="{
        type: 'fixed',
        suggestions: [
          { name: 'automatic', title: _t('Automatically adjusted to available data') },
          { name: 'fixed', title: _t('Fixed range') }
        ]
      }"
      @update:selected-option="
        (value) => {
          dataRangeType = value === 'automatic' ? 'automatic' : 'fixed'
        }
      "
    />
    <CmkIndent v-if="dataRangeType === 'fixed'">
      <FixedDataRangeInput
        v-model:data-range-symbol="dataRangeSymbol"
        v-model:data-range-min="dataRangeMin"
        v-model:data-range-max="dataRangeMax"
      />
    </CmkIndent>
  </div>
</template>
