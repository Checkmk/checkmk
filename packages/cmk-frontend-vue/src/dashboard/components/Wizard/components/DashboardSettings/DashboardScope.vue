<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import SelectorSingleInfo from '@/dashboard/components/selectors/SelectorSingleInfo.vue'

import ContentSpacer from '../../components/ContentSpacer.vue'

const { _t } = usei18n()

interface DashboardScopeProps {
  selectionErrors?: string[]
}

const props = defineProps<DashboardScopeProps>()

const selectedIds = defineModel<string[]>('selectedIds', { required: true })

const displayError = computed(() => (props?.selectionErrors?.length ?? 0) > 0)
</script>

<template>
  <div>
    <CmkLabel>{{ _t('Choose which objects this dashboard applies to') }}</CmkLabel>
    <CmkLabelRequired space="before" />
    <ContentSpacer :dimension="3" />
    <CmkInlineValidation v-if="displayError" :validation="selectionErrors || []" />
    <SelectorSingleInfo v-model:selected-ids="selectedIds" :has-errors="displayError" />
  </div>
</template>
