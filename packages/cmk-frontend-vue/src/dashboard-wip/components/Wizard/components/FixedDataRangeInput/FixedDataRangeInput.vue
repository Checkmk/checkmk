<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n.ts'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'
import { DATA_RANGE_SYMBOL_SUGGESTIONS } from './suggestions'

const { _t } = usei18n()
const dataRangeSymbol = defineModel<string>('dataRangeSymbol', { required: true })
const dataRangeMin = defineModel<number>('dataRangeMin', { required: true })
const dataRangeMax = defineModel<number>('dataRangeMax', { required: true })
</script>

<template>
  <div style="padding-top: 5px">
    <CmkDropdown
      :selected-option="dataRangeSymbol"
      :label="_t('Select option')"
      :options="{
        type: 'fixed',
        suggestions: DATA_RANGE_SYMBOL_SUGGESTIONS
      }"
      @update:selected-option="(value) => (dataRangeSymbol = value || dataRangeSymbol)"
    />
  </div>

  <TableForm style="padding-top: 5px">
    <TableFormRow>
      <FieldDescription>{{ _t('Minimum') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          :model-value="dataRangeMin"
          type="number"
          @update:model-value="(value) => (dataRangeMin = value || dataRangeMin)"
        />
      </FieldComponent>
    </TableFormRow>

    <TableFormRow>
      <FieldDescription>{{ _t('Maximum') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          :model-value="dataRangeMax"
          type="number"
          @update:model-value="(value) => (dataRangeMax = value || dataRangeMax)"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
