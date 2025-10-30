<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'

import ColorSelector from '@/dashboard-wip/components/Wizard/components/ColorSelector/ColorSelector.vue'
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
      <ColorSelector
        v-model:color="metricColor"
        :static-options="[{ name: 'default', title: _t('Default color') }]"
      />
    </CmkIndent>

    <CmkLabel>{{ _t('Color of the average') }}</CmkLabel>
    <CmkIndent>
      <ColorSelector
        v-model:color="averageColor"
        :static-options="[{ name: 'default', title: _t('Default color') }]"
      />
    </CmkIndent>

    <CmkLabel>{{ _t('Color of the median') }}</CmkLabel>
    <CmkIndent>
      <ColorSelector
        v-model:color="medianColor"
        :static-options="[{ name: 'default', title: _t('Default color') }]"
      />
    </CmkIndent>
  </div>
</template>
