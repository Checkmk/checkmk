<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import type {
  CopyExistingViewSelection,
  NewViewSelection
} from '@/dashboard-wip/components/Wizard/wizards/view/types'
import {
  DataConfigurationMode,
  ViewSelectionMode
} from '@/dashboard-wip/components/Wizard/wizards/view/types'
import type { EmbeddedViewContent } from '@/dashboard-wip/types/widget'

// These must be kept in sync with the Python side
interface ConfigurationErrorMessage {
  type: 'cmk:view:configuration-error'
  message: string
}

interface ValidationErrorMessage {
  type: 'cmk:view:validation-error'
}

interface SaveCompletedMessage {
  type: 'cmk:view:save-completed'
  datasource: string
  single_infos: string[]
}

type MessageEventData = ConfigurationErrorMessage | ValidationErrorMessage | SaveCompletedMessage

interface Stage2Props {
  dashboardName: string
  dashboardOwner: string
  embeddedId: string
  configurationMode: DataConfigurationMode
  viewSelection: NewViewSelection | CopyExistingViewSelection
}

const props = defineProps<Stage2Props>()
const emit = defineEmits<{
  goPrev: []
  goNext: [content: EmbeddedViewContent]
}>()

const { _t } = usei18n()

const iframeUrl = computed(() => {
  const baseUrl = 'widget_edit_view.py'
  const params = new URLSearchParams({
    dashboard: props.dashboardName,
    owner: props.dashboardOwner,
    embedded_id: props.embeddedId
  })
  if (props.configurationMode === DataConfigurationMode.EDIT) {
    params.append('mode', 'edit')
  } else if (props.viewSelection.type === ViewSelectionMode.COPY) {
    params.append('mode', 'copy')
    params.append('view_name', props.viewSelection.viewName)
  } else if (props.viewSelection.type === ViewSelectionMode.NEW) {
    params.append('mode', 'create')
    params.append('datasource', props.viewSelection.datasource)
    params.append('single_infos', props.viewSelection.restrictedToSingle.join(','))
  }
  return `${baseUrl}?${params.toString()}`
})
const isSaving = ref(false)
const configurationError = ref<string | undefined>()
const viewEditor = useTemplateRef<HTMLIFrameElement>('view-editor')

function saveAndContinue() {
  if (isSaving.value || configurationError.value || !viewEditor.value) {
    return
  }
  const iframeDocument = viewEditor.value.contentDocument
  if (!iframeDocument) {
    console.error('Could not access iframe document')
    return
  }
  const elements = iframeDocument.getElementsByName('_save')
  if (elements.length === 0) {
    console.error('Could not find save button in iframe')
    return
  }
  const saveButton = elements[0] as HTMLButtonElement
  isSaving.value = true
  saveButton.click()
}

function onMessageEvent(event: MessageEvent) {
  if (event.origin !== window.location.origin) {
    return // ignore messages from other domains
  }
  // there are 3 types of messages we expect, these must be in sync with widget_edit_view.py:
  // 1. Configuration error, missing permissions or otherwise invalid url parameters
  //    -> implementation error or the stored configured is invalid
  // 2. Validation error, the save failed due to validation errors -> user error
  // 3. Save completed, we can proceed to the next step
  // We might get other messages (from other components), we'll ignore those
  if (typeof event.data !== 'object' || event.data === null || !('type' in event.data)) {
    return
  }
  // type key could still be anything else, always check its value
  const eventData = event.data as MessageEventData

  if (eventData.type === 'cmk:view:configuration-error') {
    configurationError.value = event.data.message
    return
  }

  if (eventData.type === 'cmk:view:validation-error') {
    isSaving.value = false
    // the iframe will already show the validation error
    return
  }

  if (eventData.type === 'cmk:view:save-completed') {
    isSaving.value = false
    emit('goNext', {
      type: 'embedded_view',
      embedded_id: props.embeddedId,
      datasource: eventData.datasource,
      restricted_to_single: eventData.single_infos
    } as EmbeddedViewContent)
  }
}

onMounted(() => {
  window.addEventListener('message', onMessageEvent)
})
onUnmounted(() => {
  window.removeEventListener('message', onMessageEvent)
})
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Data configuration') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'back', side: 'left' }"
      :action="() => $emit('goPrev')"
      variant="secondary"
    />
    <ActionButton
      v-if="!configurationError"
      :label="_t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      :action="saveAndContinue"
      variant="secondary"
    />
  </ActionBar>

  <ContentSpacer />

  <CmkAlertBox v-if="configurationError" variant="error">
    {{ configurationError }}
  </CmkAlertBox>
  <iframe v-else ref="view-editor" class="db-stage-contents__view-editor" :src="iframeUrl" />
</template>

<style scoped>
.db-stage-contents__view-editor {
  border: none;
  width: 750px;

  /* should be more than 91px = height of heading + action bar + spacers
   we're adding a bit more because otherwise a simple scroll bar might pop up */
  height: calc(100% - 95px);
}
</style>
