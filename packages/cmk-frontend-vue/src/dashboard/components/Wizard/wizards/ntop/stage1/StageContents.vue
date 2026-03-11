<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import ActionBar from '@/dashboard/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard/components/Wizard/components/ContentSpacer.vue'
import SectionBlock from '@/dashboard/components/Wizard/components/SectionBlock.vue'
import StepsHeader from '@/dashboard/components/Wizard/components/StepsHeader.vue'
import type { WidgetItemList } from '@/dashboard/components/Wizard/components/WidgetSelection/types'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import WidgetTiles from '../../../components/WidgetSelection/WidgetTiles.vue'
import NtopPreview from './NtopPreview.vue'

const { _t } = usei18n()

interface Stage1Props {
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

enum NtopWidgetType {
  NTOP_ALERTS = 'ntop_alerts',
  NTOP_FLOWS = 'ntop_flows',
  NTOP_TOP_TALKERS = 'ntop_top_talkers'
}

const availableWidgets: WidgetItemList = [
  {
    id: NtopWidgetType.NTOP_ALERTS,
    label: _t('Ntop alerts'),
    icon: { name: 'ntop', emblem: 'warning' }
  },
  {
    id: NtopWidgetType.NTOP_FLOWS,
    label: _t('Ntop flows'),
    icon: { name: 'ntop', emblem: 'more' }
  },
  {
    id: NtopWidgetType.NTOP_TOP_TALKERS,
    label: _t('Ntop top talkers'),
    icon: { name: 'ntop', emblem: 'statistic' }
  }
]
const enabledWidgets = computed(() => {
  return availableWidgets.map((item) => item.id)
})

function getSelectedWidget(): NtopWidgetType {
  switch (props.editWidgetSpec?.content?.type) {
    case 'ntop_alerts':
      return NtopWidgetType.NTOP_ALERTS
    case 'ntop_flows':
      return NtopWidgetType.NTOP_FLOWS
    case 'ntop_top_talkers':
      return NtopWidgetType.NTOP_TOP_TALKERS
  }
  return NtopWidgetType.NTOP_ALERTS
}
const selectedWidget = ref<NtopWidgetType>(getSelectedWidget())

function gotoNextStage() {
  if (!selectedWidget.value) {
    return
  }

  emit(
    'addWidget',
    toValue({ type: selectedWidget.value }),
    toValue({
      title: { text: '', render_mode: 'hidden' },
      render_background: false
    }),
    toValue({
      filters: {},
      uses_infos: []
    } as WidgetFilterContext)
  )
}
</script>

<template>
  <StepsHeader
    :title="_t('Add ntop')"
    :subtitle="_t('Define widget')"
    @back="() => emit('goBack')"
  />

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="!!editWidgetSpec ? _t('Save widget') : _t('Add & place widget')"
      :action="gotoNextStage"
      variant="primary"
    />
  </ActionBar>

  <ContentSpacer :dimension="8" />

  <SectionBlock :title="_t('Choose what to display')">
    <WidgetTiles
      v-model:selected-widget="selectedWidget as NtopWidgetType"
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
    />
  </SectionBlock>

  <NtopPreview />
</template>
