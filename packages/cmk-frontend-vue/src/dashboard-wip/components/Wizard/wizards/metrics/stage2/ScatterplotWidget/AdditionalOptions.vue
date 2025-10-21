<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'

import type { DefaultOrColor } from '@/dashboard-wip/components/Wizard/types'

const { _t } = usei18n()

const metricColor = defineModel<DefaultOrColor>('metricColor', { required: true })
const averageColor = defineModel<DefaultOrColor>('averageColor', { required: true })
const medianColor = defineModel<DefaultOrColor>('medianColor', { required: true })
</script>

<template>
  <div>
    <CmkLabel>{{ _t('Color of the scattered dots') }}</CmkLabel>
    <CmkIndent>
      <CmkDropdown
        :selected-option="metricColor"
        :label="_t('Select option')"
        :options="{
          type: 'fixed',
          suggestions: [{ name: 'default', title: _t('Default color') }]
        }"
        @update:selected-option="(value) => (metricColor = value || metricColor)"
      />
    </CmkIndent>

    <CmkLabel>{{ _t('Color of the average') }}</CmkLabel>
    <CmkIndent>
      <CmkDropdown
        :selected-option="averageColor"
        :label="_t('Select option')"
        :options="{
          type: 'fixed',
          suggestions: [{ name: 'default', title: _t('Default color') }]
        }"
        @update:selected-option="(value) => (averageColor = value || averageColor)"
      />
    </CmkIndent>

    <CmkLabel>{{ _t('Color of the median') }}</CmkLabel>
    <CmkIndent>
      <CmkDropdown
        :selected-option="medianColor"
        :label="_t('Select option')"
        :options="{
          type: 'fixed',
          suggestions: [{ name: 'default', title: _t('Default color') }]
        }"
        @update:selected-option="(value) => (medianColor = value || medianColor)"
      />
    </CmkIndent>
  </div>
</template>
