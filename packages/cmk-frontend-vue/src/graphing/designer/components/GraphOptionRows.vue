<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'

import type { DataFieldErrors, UseCustomGraphOptions } from '../composables/useCustomGraphOptions'
import UnitSettings from './UnitSettings.vue'
import VerticalRangeSettings from './VerticalRangeSettings.vue'

const { _t } = usei18n()

/** The custom graph's own options as table form rows, for any table form that hosts them. */
const { validationErrors } = defineProps<{ validationErrors: DataFieldErrors }>()
const graphOptions = defineModel<UseCustomGraphOptions>('graphOptions', { required: true })
</script>

<template>
  <TableFormRow>
    <FieldDescription>{{ _t('Unit') }}</FieldDescription>
    <FieldComponent>
      <UnitSettings
        v-model:unit-type="graphOptions.unitType.value"
        v-model:notation="graphOptions.notation.value"
        v-model:symbol="graphOptions.symbol.value"
        v-model:rounding-mode="graphOptions.roundingMode.value"
        v-model:rounding-digits="graphOptions.roundingDigits.value"
        :digit-error="validationErrors.precision_digits ?? null"
      />
    </FieldComponent>
  </TableFormRow>
  <TableFormRow>
    <FieldDescription>{{ _t('Explicit range') }}</FieldDescription>
    <FieldComponent>
      <VerticalRangeSettings
        v-model:vertical-range-type="graphOptions.verticalRangeType.value"
        v-model:lower-bound="graphOptions.lowerVerticalRange.value"
        v-model:upper-bound="graphOptions.upperVerticalRange.value"
        :lower-bound-error="validationErrors.lower_range ?? null"
        :upper-bound-error="validationErrors.upper_range ?? null"
      />
    </FieldComponent>
  </TableFormRow>
  <TableFormRow>
    <FieldDescription>{{ _t('Metric visibility') }}</FieldDescription>
    <FieldComponent>
      <CmkCheckbox v-model="graphOptions.showZeroValues.value" :label="_t('Show zero values')" />
    </FieldComponent>
  </TableFormRow>
</template>
