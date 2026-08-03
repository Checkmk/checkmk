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
import { computed } from 'vue'

const { _t } = usei18n()

interface VerticalRangeSettingsProps {
  lowerBoundError: TranslatedString | null
  upperBoundError: TranslatedString | null
}

defineProps<VerticalRangeSettingsProps>()

const verticalRangeType = defineModel<string>('verticalRangeType', { default: 'auto' })
const lowerBound = defineModel<number | null>('lowerBound')
const upperBound = defineModel<number | null>('upperBound')

// CmkInput's number model does not accept null, so bridge it to undefined here.
const lowerBoundInput = computed({
  get: () => lowerBound.value ?? undefined,
  set: (value) => (lowerBound.value = value ?? null)
})
const upperBoundInput = computed({
  get: () => upperBound.value ?? undefined,
  set: (value) => (upperBound.value = value ?? null)
})
</script>

<template>
  <CmkDropdown
    v-model="verticalRangeType"
    :label="_t('Explicit range')"
    :options="{
      type: 'fixed',
      suggestions: [
        { title: _t('Auto'), name: 'auto' },
        { title: _t('Explicit range'), name: 'fixed' }
      ]
    }"
  />
  <template v-if="verticalRangeType === 'fixed'">
    <CmkIndent>
      <div class="graphing-vertical-range-settings__row">
        <div>
          <CmkLabel>{{ _t('Lower') }}</CmkLabel>
        </div>
        <div>
          <CmkInput
            v-model="lowerBoundInput"
            :label="_t('Lower')"
            :aria-label="_t('Lower limit')"
            type="number"
            :external-errors="lowerBoundError ? [lowerBoundError] : []"
          />
        </div>
      </div>

      <div class="graphing-vertical-range-settings__row">
        <div>
          <CmkLabel>{{ _t('Upper') }}</CmkLabel>
        </div>
        <div>
          <CmkInput
            v-model="upperBoundInput"
            :label="_t('Upper')"
            :aria-label="_t('Upper limit')"
            type="number"
            :external-errors="upperBoundError ? [upperBoundError] : []"
          />
        </div>
      </div>
    </CmkIndent>
  </template>
</template>

<style scoped>
.graphing-vertical-range-settings__row {
  display: flex;
  flex-flow: row nowrap;
  place-content: stretch flex-start;
  align-items: flex-start;
  gap: var(--dimension-4);
  padding-bottom: var(--dimension-4);
}
</style>
