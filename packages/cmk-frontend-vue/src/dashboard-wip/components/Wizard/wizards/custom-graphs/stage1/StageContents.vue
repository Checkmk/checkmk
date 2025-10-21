<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import ContentSpacer from '../../../components/ContentSpacer.vue'
import CustomGraphWidget from './CustomGraphWidget.vue'
import { useCustomGraph } from './composables/useCustomGraph'

const { _t } = usei18n()

interface Stage1Props {
  dashboardName: string
  filters: ConfiguredFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<Stage1Props>()

const handler = await useCustomGraph(
  props.filters,
  props.dashboardConstants,
  props.editWidgetSpec || undefined
)

const emit = defineEmits<{
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
  updateWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const addWidget = () => {
  const isValid = handler.validate()
  if (isValid) {
    emit(
      'addWidget',
      toValue(handler.widgetProps.value!.content),
      toValue(handler.widgetProps.value!.general_settings),
      toValue(handler.widgetProps.value!.effective_filter_context)
    )
  }
}

const updateWidget = () => {
  const isValid = handler.validate()
  if (isValid) {
    emit(
      'updateWidget',
      toValue(handler.widgetProps.value!.content),
      toValue(handler.widgetProps.value!.general_settings),
      toValue(handler.widgetProps.value!.effective_filter_context)
    )
  }
}

const isUpdate = computed(() => !props.editWidgetSpec)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Custom graph') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      v-if="isUpdate"
      :label="_t('Add & place widget')"
      :action="addWidget"
      variant="primary"
    />
    <ActionButton v-else :label="_t('Save widget')" :action="updateWidget" variant="primary" />
  </ActionBar>

  <ContentSpacer />

  <CustomGraphWidget v-model:handler="handler" :dashboard-name="dashboardName" />
</template>
