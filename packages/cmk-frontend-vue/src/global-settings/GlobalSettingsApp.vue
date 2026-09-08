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
import CmkBreadcrumb from 'cmk-ui-library/components/CmkBreadcrumb'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { computed, inject, provide, ref, toRaw, watch } from 'vue'

import { GLOBAL_SETTINGS_SERVICE, GLOBAL_SETTINGS_TOGGLE, globalSettingsService } from './api'
import ExpandCollapseButtons from './components/ExpandCollapseButtons.vue'
import GlobalSettingsEditSlideIn from './components/GlobalSettingsEditSlideIn.vue'
import GlobalSettingsEmptyState from './components/GlobalSettingsEmptyState.vue'
import GlobalSettingsSearchInput from './components/GlobalSettingsSearchInput.vue'
import GlobalSettingsTopic from './components/GlobalSettingsTopic.vue'
import { buildSearchIndex, matchTopics } from './lib/search'
import { applyReceived, describeError, useGlobalSettingsEditor } from './useGlobalSettingsEditor'

const { _t } = usei18n()

const props = defineProps<GlobalSettingsApp>()

const service = inject(GLOBAL_SETTINGS_SERVICE, globalSettingsService)

const SEARCH_URL_PARAM = 'search'

const editableTopics = ref(structuredClone(toRaw(props.topics)))
const { session, openEditor, closeEditor } = useGlobalSettingsEditor(service, props.scope)
const resetConfirmTopic = ref<GlobalSettingsTopicData | null>(null)
const resettingTopic = ref<string | null>(null)
const resetError = ref<TranslatedString | null>(null)

const query = ref(new URLSearchParams(window.location.search).get(SEARCH_URL_PARAM) ?? '')
const debouncedQuery = useDebounceRef(query, 100)
const searchActive = computed(() => debouncedQuery.value.trim() !== '')

const searchIndex = computed(() => buildSearchIndex(editableTopics.value))
const matches = computed(() => matchTopics(searchIndex.value, debouncedQuery.value))

const shownTopics = computed(() => {
  const currentMatches = matches.value
  return currentMatches === null
    ? editableTopics.value
    : editableTopics.value.filter((topic) => currentMatches.has(topic.headline))
})

function shownVariablesOf(headline: string): ReadonlySet<string> | null {
  return matches.value?.get(headline) ?? null
}

function openedItemsForQuery(): string[] {
  return searchActive.value ? shownTopics.value.map((topic) => topic.headline) : []
}

const openedItems = ref<string[]>(openedItemsForQuery())

watch(debouncedQuery, (value) => {
  openedItems.value = openedItemsForQuery()

  const url = new URL(window.location.href)
  if (value.trim() === '') {
    url.searchParams.delete(SEARCH_URL_PARAM)
  } else {
    url.searchParams.set(SEARCH_URL_PARAM, value)
  }
  window.history.replaceState({}, '', url)
})

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
    <CmkBreadcrumb :items="breadcrumb" />
    <div class="global-settings-app__toolbar">
      <GlobalSettingsSearchInput
        v-model="query"
        class="global-settings-app__search"
        :placeholder="_t('Search settings…')"
      />
      <ExpandCollapseButtons
        @expand-all="openedItems = shownTopics.map((topic) => topic.headline)"
        @collapse-all="openedItems = []"
      />
    </div>
    <CmkAlertBox variant="warning">
      {{ _t('This page is work in progress. It shows a subset of the global settings.') }}
    </CmkAlertBox>
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
    <GlobalSettingsEmptyState v-if="shownTopics.length === 0" @reset="query = ''" />
    <CmkAccordion v-else v-model="openedItems" :min-open="0" :max-open="0">
      <GlobalSettingsTopic
        v-for="topic in shownTopics"
        :key="topic.headline"
        :topic="topic"
        :value="topic.headline"
        :match="shownVariablesOf(topic.headline)"
        :resetting="resettingTopic === topic.headline"
        @edit="openEditor"
        @reset="requestTopicReset(topic)"
      />
    </CmkAccordion>
    <GlobalSettingsEditSlideIn v-if="session !== null" :session="session" @close="closeEditor" />
  </div>
</template>

<style scoped>
.global-settings-app {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  padding: var(--dimension-4) var(--dimension-4) 0;
}

.global-settings-app__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-6);
}

.global-settings-app__search {
  flex: 0 1 400px;
}
</style>
