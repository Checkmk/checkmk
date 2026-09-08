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
import GlobalSettingsModificationFilter, {
  type ModificationFilter
} from './components/GlobalSettingsModificationFilter.vue'
import GlobalSettingsSearchInput from './components/GlobalSettingsSearchInput.vue'
import GlobalSettingsTopic from './components/GlobalSettingsTopic.vue'
import { type VariableFilter, buildSearchIndex, matchTopics } from './lib/search'
import { applyReceived, describeError, useGlobalSettingsEditor } from './useGlobalSettingsEditor'

const { _t } = usei18n()

const props = defineProps<GlobalSettingsApp>()

const service = inject(GLOBAL_SETTINGS_SERVICE, globalSettingsService)

const SEARCH_URL_PARAM = 'search'
const FILTER_URL_PARAM = 'filter'

function urlParam(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name)
}

function parseModificationFilter(value: string | null): ModificationFilter {
  switch (value) {
    case 'default':
    case 'modified':
      return value
    default:
      return 'all'
  }
}

function setOrDelete(params: URLSearchParams, name: string, value: string | null): void {
  if (value === null) {
    params.delete(name)
  } else {
    params.set(name, value)
  }
}

const editableTopics = ref(structuredClone(toRaw(props.topics)))
const { session, openEditor, closeEditor } = useGlobalSettingsEditor(service, props.scope)
const resetConfirmTopic = ref<GlobalSettingsTopicData | null>(null)
const resettingTopic = ref<string | null>(null)
const resetError = ref<TranslatedString | null>(null)

const query = ref(urlParam(SEARCH_URL_PARAM) ?? '')
const debouncedQuery = useDebounceRef(query, 100)
const searchActive = computed(() => debouncedQuery.value.trim() !== '')

const modification = ref<ModificationFilter>(parseModificationFilter(urlParam(FILTER_URL_PARAM)))
const variableFilter = computed<VariableFilter | null>(() => {
  switch (modification.value) {
    case 'default':
      return (variable) => !variable.modified
    case 'modified':
      return (variable) => variable.modified
    default:
      return null
  }
})

const searchIndex = computed(() => buildSearchIndex(editableTopics.value))
const matches = computed(() =>
  matchTopics(editableTopics.value, searchIndex.value, debouncedQuery.value, variableFilter.value)
)

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

// Only the search touches the open sections; the filter leaves them as they are.
const openedItems = ref<string[]>(openedItemsForQuery())

watch(debouncedQuery, () => {
  openedItems.value = openedItemsForQuery()
})

watch([debouncedQuery, modification], ([value, filter]) => {
  // replaceState, not pushState: typing must not fill the back stack.
  const url = new URL(window.location.href)
  setOrDelete(url.searchParams, SEARCH_URL_PARAM, value.trim() === '' ? null : value)
  setOrDelete(url.searchParams, FILTER_URL_PARAM, filter === 'all' ? null : filter)
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

function resetSearchAndFilters(): void {
  query.value = ''
  modification.value = 'all'
}

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
      <div class="global-settings-app__toolbar-right">
        <GlobalSettingsModificationFilter v-model="modification" />
        <ExpandCollapseButtons
          @expand-all="openedItems = shownTopics.map((topic) => topic.headline)"
          @collapse-all="openedItems = []"
        />
      </div>
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
    <GlobalSettingsEmptyState v-if="shownTopics.length === 0" @reset="resetSearchAndFilters" />
    <CmkAccordion v-else v-model="openedItems" :min-open="0" :max-open="0">
      <GlobalSettingsTopic
        v-for="topic in shownTopics"
        :key="topic.headline"
        :topic="topic"
        :value="topic.headline"
        :match="shownVariablesOf(topic.headline)"
        :query="debouncedQuery"
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
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-6);
}

.global-settings-app__search {
  flex: 1 1 320px;
  max-width: 400px;
}

/* Wraps below the search field when the toolbar runs out of width, and the two
button groups stack once even that is too narrow. */
.global-settings-app__toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}
</style>
