<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { CustomGraphUnitNotationTypes } from '../api'

const { _t } = usei18n()

interface UnitSettingsProps {
  digitError?: TranslatedString | null
}

defineProps<UnitSettingsProps>()

const unitType = defineModel<'first_entry_with_unit' | 'custom'>('unitType', {
  default: 'first_entry_with_unit'
})
const notation = defineModel<CustomGraphUnitNotationTypes | 'time' | null>('notation', {
  default: null
})
const symbol = defineModel<string>('symbol', {
  default: ''
})
const roundingMode = defineModel<'auto' | 'strict' | null>('roundingMode', {
  default: null
})
const roundingDigits = defineModel<number | undefined>('roundingDigits', {
  default: 2
})
</script>

<template>
  <CmkDropdown
    v-model="unitType"
    :label="_t('Unit')"
    :options="{
      type: 'fixed',
      suggestions: [
        { title: _t('Use unit of first entry'), name: 'first_entry_with_unit' },
        { title: _t('Custom'), name: 'custom' }
      ]
    }"
  />
  <template v-if="unitType === 'custom'">
    <CmkIndent>
      <div>
        <CmkLabel>{{ _t('Notation') }}</CmkLabel>
        <CmkIndent>
          <div class="graphing-unit-settings__row">
            <CmkLabel>{{ _t('Notation') }}</CmkLabel>
            <div>
              <CmkDropdown
                v-model="notation"
                :label="_t('Notation')"
                :options="{
                  type: 'fixed',
                  suggestions: [
                    { title: _t('Decimal'), name: 'decimal' },
                    { title: _t('Engineering scientific'), name: 'engineering_scientific' },
                    { title: _t('IEC'), name: 'iec' },
                    { title: _t('SI'), name: 'si' },
                    { title: _t('Standard scientific'), name: 'standard_scientific' },
                    { title: _t('Time'), name: 'time' }
                  ]
                }"
              />
            </div>
          </div>

          <template v-if="notation !== 'time'">
            <div class="graphing-unit-settings__row">
              <CmkLabel>{{ _t('Symbol') }}</CmkLabel>
              <CmkInput v-model="symbol" :aria-label="_t('Symbol')" />
            </div>
          </template>
        </CmkIndent>
      </div>

      <div>
        <CmkLabel>{{ _t('Precision') }}</CmkLabel>
        <CmkIndent>
          <div class="graphing-unit-settings__row">
            <CmkLabel>{{ _t('Rounding mode') }}</CmkLabel>
            <div>
              <CmkDropdown
                v-model="roundingMode"
                :label="_t('Rounding mode')"
                :options="{
                  type: 'fixed',
                  suggestions: [
                    { title: _t('Auto'), name: 'auto' },
                    { title: _t('Strict'), name: 'strict' }
                  ]
                }"
              />
            </div>
          </div>

          <div class="graphing-unit-settings__row">
            <CmkLabel>{{ _t('Digits') }}</CmkLabel>
            <CmkInput
              v-model="roundingDigits"
              :aria-label="_t('Rounding digits')"
              :external-errors="digitError ? [digitError] : []"
              type="number"
            />
          </div>
        </CmkIndent>
      </div>
    </CmkIndent>
  </template>
</template>

<style scoped>
.graphing-unit-settings__row {
  display: block;

  &:not(:last-child) {
    padding-bottom: var(--dimension-4);
  }
}
</style>
