<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, toValue } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import CustomGraphWidget from './CustomGraphWidget.vue'
import { useCustomGraph } from './composables/useCustomGraph'

const { _t } = usei18n()

interface Stage1Props {
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  filters: ConfiguredFilters
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<Stage1Props>()

const handler = await useCustomGraph(props.filters, props.editWidgetSpec || undefined)

const emit = defineEmits<{
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const addWidget = async () => {
  if (!handler.validate()) {
    return
  }
  const submitProps = await handler.getSubmitProps()
  emit(
    'addWidget',
    toValue(submitProps.content),
    toValue(submitProps.general_settings),
    toValue(submitProps.effective_filter_context)
  )
}

const isUpdate = computed(() => props.editWidgetSpec !== null)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Custom graph') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="isUpdate ? _t('Save widget') : _t('Add & place widget')"
      :action="addWidget"
      variant="primary"
    />
  </ActionBar>

  <ContentSpacer />

  <CustomGraphWidget
    v-model:handler="handler"
    :dashboard-key="dashboardKey"
    :tick="tick"
    :range="range"
  />
</template>
