<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import ContentSpacer from '../../../components/ContentSpacer.vue'
import VisibilityProperties from '../../../components/DashboardSettings/VisibilityProperties.vue'

const { _t } = usei18n()

const hideInMonitorMenu = defineModel<boolean>('hideInMonitorMenu', { required: true })
const monitorMenuTopic = defineModel<string>('monitorMenuTopic', { default: '' })
const sortIndex = defineModel<number>('sortIndex', { required: true })
const hideInDropdownsMenu = defineModel<boolean>('hideInDropdownsMenu', { required: true })
const showWhenShowMoreIsEnabled = defineModel<boolean>('showWhenShowMoreIsEnabled', {
  required: true
})

const showInDropdownsMenu = computed(() => !hideInDropdownsMenu.value)
const showInMonitorMenu = computed(() => !hideInMonitorMenu.value)
const onShowMoreLabel = _t('Only show when "Show more" is enabled')
</script>

<template>
  <VisibilityProperties
    v-model:monitor-menu-topic="monitorMenuTopic"
    v-model:sort-index="sortIndex"
    :show-in-monitor-menu="showInMonitorMenu"
    @update:show-in-monitor-menu="(val) => (hideInMonitorMenu = !val)"
  >
    <template #extra-visibility-settings>
      <CmkCheckbox
        :model-value="showInDropdownsMenu"
        :label="_t('Show in dropdown menus')"
        @update:model-value="(val) => (hideInDropdownsMenu = !val)"
      />

      <ContentSpacer />

      <CmkCheckbox v-model="showWhenShowMoreIsEnabled" :label="onShowMoreLabel" />
    </template>
  </VisibilityProperties>
</template>
