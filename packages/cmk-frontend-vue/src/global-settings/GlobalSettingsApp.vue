<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  GlobalSettingsApp,
  GlobalSettingsTopic as GlobalSettingsTopicData,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject, provide, ref, toRaw } from 'vue'

import { GLOBAL_SETTINGS_SERVICE, GLOBAL_SETTINGS_TOGGLE, globalSettingsService } from './api'
import ExpandCollapseToggle from './components/ExpandCollapseToggle.vue'
import GlobalSettingsEditSlideIn from './components/GlobalSettingsEditSlideIn.vue'
import GlobalSettingsTopic from './components/GlobalSettingsTopic.vue'
import { applyReceived, describeError, useGlobalSettingsEditor } from './useGlobalSettingsEditor'

const { _t } = usei18n()

const props = defineProps<GlobalSettingsApp>()

const service = inject(GLOBAL_SETTINGS_SERVICE, globalSettingsService)

const allTopicIds = computed(() => props.topics.map((topic) => topic.headline))
const openedItems = ref<string[]>([])

const editableTopics = ref(structuredClone(toRaw(props.topics)))
const { session, openEditor, closeEditor } = useGlobalSettingsEditor(service, props.scope)
const resetConfirmTopic = ref<GlobalSettingsTopicData | null>(null)
const resettingTopic = ref<string | null>(null)
const resetError = ref<TranslatedString | null>(null)

const resetConfirmation = computed<{
  heading: TranslatedString
  body: TranslatedString
  confirm: TranslatedString
} | null>(() => {
  if (resetConfirmTopic.value === null) {
    return null
  }
  const topic = resetConfirmTopic.value.headline
  return {
    heading: _t('Remove all modifications in "%{topic}"?', { topic }),
    body: _t(
      'The configured values will be discarded and the default values will be used instead.'
    ),
    confirm: _t('Remove')
  }
})

async function toggleSetting(
  variable: GlobalSettingsVariable,
  value: boolean
): Promise<TranslatedString | null> {
  try {
    applyReceived(variable, await service.save(props.scope, variable.name, value, '*'))
    return null
  } catch (cause: unknown) {
    return describeError(cause, _t('Could not reach the server.'))
  }
}

provide(GLOBAL_SETTINGS_TOGGLE, toggleSetting)

function requestTopicReset(topic: GlobalSettingsTopicData): void {
  resetError.value = null
  resetConfirmTopic.value = topic
}

async function resetTopic(): Promise<void> {
  const topic = resetConfirmTopic.value
  if (topic === null || session.value?.busy === true || resettingTopic.value !== null) {
    return
  }
  resetConfirmTopic.value = null
  resettingTopic.value = topic.headline
  try {
    for (const variable of topic.variables.filter((entry) => entry.modified)) {
      const received = await service.load(props.scope, variable.name)
      await service.reset(props.scope, variable.name, received.etag)
      applyReceived(variable, await service.load(props.scope, variable.name))
    }
  } catch (cause: unknown) {
    resetError.value = describeError(cause, _t('Could not reach the server.'))
  } finally {
    resettingTopic.value = null
  }
}
</script>

<template>
  <div class="global-settings-app">
    <div class="global-settings-app__toolbar">
      <ExpandCollapseToggle
        :opened-count="openedItems.length"
        :total-count="allTopicIds.length"
        @expand-all="openedItems = [...allTopicIds]"
        @collapse-all="openedItems = []"
      />
    </div>
    <CmkAlertBox v-if="resetError !== null" variant="error" :heading="_t('Resetting failed')">
      {{ resetError }}
    </CmkAlertBox>
    <CmkAlertBox
      v-if="resetConfirmation !== null"
      variant="warning"
      :heading="resetConfirmation.heading"
      :main-button="{ title: resetConfirmation.confirm, onclick: resetTopic }"
      :optional-button="{
        title: _t('Cancel'),
        icon: 'cancel',
        onclick: () => (resetConfirmTopic = null)
      }"
    >
      {{ resetConfirmation.body }}
    </CmkAlertBox>
    <CmkAccordion v-model="openedItems" :min-open="0" :max-open="0">
      <GlobalSettingsTopic
        v-for="topic in editableTopics"
        :key="topic.headline"
        :topic="topic"
        :value="topic.headline"
        :resetting="resettingTopic === topic.headline"
        @edit="openEditor"
        @reset="requestTopicReset(topic)"
      />
    </CmkAccordion>
    <GlobalSettingsEditSlideIn
      v-if="session !== null"
      :session="session"
      :title="title"
      @close="closeEditor"
    />
  </div>
</template>

<style scoped>
.global-settings-app {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.global-settings-app__toolbar {
  display: flex;
  justify-content: flex-end;
}
</style>
