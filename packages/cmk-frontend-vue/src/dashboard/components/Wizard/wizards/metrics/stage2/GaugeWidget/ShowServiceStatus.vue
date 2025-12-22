<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { ForStates } from '@/dashboard/components/Wizard/types'

import type { ShowServiceStatusType } from './composables/useGauge'

const { _t } = usei18n()

const showServiceStatus = defineModel<ShowServiceStatusType>('showServiceStatus', {
  required: true
})
const showServiceStatusSelection = defineModel<ForStates | null>('showServiceStatusSelection', {
  required: true
})

const isShowLabel = computed({
  get: () => showServiceStatus.value !== 'disabled',
  set: (value: boolean) => {
    showServiceStatus.value = value ? 'text' : 'disabled'
    showServiceStatusSelection.value = value ? 'all' : null
  }
})

const isShowBackground = computed({
  get: () => showServiceStatus.value === 'background',
  set: (value: boolean) => {
    showServiceStatus.value = value ? 'background' : 'text'
  }
})
</script>

<template>
  <CmkCheckbox v-model="isShowLabel" :label="_t('Show colored status label')" />
  <CmkIndent v-if="isShowLabel">
    <div class="db-show-service-status__item">
      <CmkLabel>{{ _t('Show label for') }}</CmkLabel> <CmkSpace />
      <CmkDropdown
        v-model:selected-option="showServiceStatusSelection as string"
        :label="_t('Show label for')"
        :options="{
          type: 'fixed',
          suggestions: [
            { name: 'all', title: _t('all states') },
            { name: 'not_ok', title: _t('not OK states') }
          ]
        }"
      />
    </div>
    <div class="db-show-service-status__item">
      <CmkCheckbox v-model="isShowBackground" :label="_t('Show colored metric background')" />
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-show-service-status__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
