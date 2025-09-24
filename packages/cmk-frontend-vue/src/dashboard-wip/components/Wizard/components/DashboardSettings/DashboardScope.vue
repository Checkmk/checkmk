<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import SelectorSingleInfo from '@/dashboard-wip/components/selectors/SelectorSingleInfo.vue'

const { _t } = usei18n()

interface DashboardScopeProps {
  selectionErrors?: string[]
}

defineProps<DashboardScopeProps>()

const selectedIds = defineModel<string[]>('selectedIds', { required: true })
</script>

<template>
  <div>
    <CmkLabel>{{ _t('Choose which objects this dashboard applies to') }}</CmkLabel>
    <CmkInlineValidation v-if="selectionErrors" :validation="selectionErrors || []" />
    <SelectorSingleInfo v-model:selected-ids="selectedIds" />
  </div>
</template>
