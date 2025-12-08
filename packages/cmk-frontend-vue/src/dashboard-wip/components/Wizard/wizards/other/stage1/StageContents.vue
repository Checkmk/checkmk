<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ShallowRef, computed, ref, toValue, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import SelectableWidgets from '@/dashboard-wip/components/Wizard/components/WidgetSelection/SelectableWidgets.vue'
import type { WidgetItemList } from '@/dashboard-wip/components/Wizard/components/WidgetSelection/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

import SectionBlock from '../../../components/SectionBlock.vue'
import { type GetValidWidgetProps, OtherWidgetType } from '../types'
import EmbeddedURL from './EmbeddedURL/EmbeddedURL.vue'
import SidebarWidget from './SidebarWidget/SidebarWidget.vue'
import StaticText from './StaticText/StaticText.vue'
import UserMessages from './UserMessages/UserMessages.vue'

const { _t } = usei18n()

interface Stage1Props {
  dashboardName: string
  dashboardConstants: DashboardConstants
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<{
  goPrev: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const availableWidgets: WidgetItemList = [
  { id: OtherWidgetType.USER_MESSAGES, label: _t('User messages'), icon: 'folder' },
  { id: OtherWidgetType.SIDEBAR_WIDGET, label: _t('Sidebar widget'), icon: 'folder' },
  { id: OtherWidgetType.EMBEDDED_URL, label: _t('Embed URL'), icon: 'folder' },
  { id: OtherWidgetType.STATIC_TEXT, label: _t('Static text'), icon: 'folder' }
]
const enabledWidgets = computed(() => {
  return availableWidgets.map((item) => item.id)
})

function getSelectedWidget(): OtherWidgetType {
  switch (props.editWidgetSpec?.content?.type) {
    case 'user_messages':
      return OtherWidgetType.USER_MESSAGES
    case 'sidebar_element':
      return OtherWidgetType.SIDEBAR_WIDGET
    case 'url':
      return OtherWidgetType.EMBEDDED_URL
    case 'static_text':
      return OtherWidgetType.STATIC_TEXT
  }
  return OtherWidgetType.USER_MESSAGES
}
const selectedWidget = ref<OtherWidgetType>(getSelectedWidget())

const userMessagesRef = useTemplateRef<InstanceType<typeof UserMessages>>('userMessagesRef')
const sidebarWidgetRef = useTemplateRef<InstanceType<typeof SidebarWidget>>('sidebarWidgetRef')
const embeddedURLRef = useTemplateRef<InstanceType<typeof EmbeddedURL>>('embeddedURLRef')
const staticTextRef = useTemplateRef<InstanceType<typeof StaticText>>('staticTextRef')
const widgetRefs: Record<OtherWidgetType, Readonly<ShallowRef<GetValidWidgetProps | null>>> = {
  [OtherWidgetType.USER_MESSAGES]: userMessagesRef,
  [OtherWidgetType.SIDEBAR_WIDGET]: sidebarWidgetRef,
  [OtherWidgetType.EMBEDDED_URL]: embeddedURLRef,
  [OtherWidgetType.STATIC_TEXT]: staticTextRef
}

function gotoNextStage() {
  const selected = widgetRefs[selectedWidget.value].value
  if (!selected) {
    return
  }

  const widgetProps = selected.getValidWidgetProps()
  if (widgetProps) {
    emit(
      'addWidget',
      toValue(widgetProps.content),
      toValue(widgetProps.general_settings),
      toValue({
        filters: {},
        uses_infos: widgetProps.effective_filter_context.uses_infos
      } as WidgetFilterContext)
    )
  }
}
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Add other element') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton :label="_t('Add & place widget')" :action="gotoNextStage" variant="primary" />
  </ActionBar>

  <ContentSpacer :dimension="8" />

  <SectionBlock :title="_t('Choose how to display your data')">
    <SelectableWidgets
      v-model:selected-widget="selectedWidget as OtherWidgetType"
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
    />
  </SectionBlock>

  <UserMessages
    v-show="selectedWidget === OtherWidgetType.USER_MESSAGES"
    ref="userMessagesRef"
    :dashboard-name="dashboardName"
    :dashboard-constants="dashboardConstants"
    :edit-widget-spec="editWidgetSpec"
  />

  <SidebarWidget
    v-show="selectedWidget === OtherWidgetType.SIDEBAR_WIDGET"
    ref="sidebarWidgetRef"
    :dashboard-name="dashboardName"
    :dashboard-constants="dashboardConstants"
    :edit-widget-spec="editWidgetSpec"
  />

  <EmbeddedURL
    v-show="selectedWidget === OtherWidgetType.EMBEDDED_URL"
    ref="embeddedURLRef"
    :dashboard-name="dashboardName"
    :dashboard-constants="dashboardConstants"
    :edit-widget-spec="editWidgetSpec"
  />

  <StaticText
    v-show="selectedWidget === OtherWidgetType.STATIC_TEXT"
    ref="staticTextRef"
    :dashboard-name="dashboardName"
    :dashboard-constants="dashboardConstants"
    :edit-widget-spec="editWidgetSpec"
  />
</template>
