<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type {
  GlobalSettingsApp,
  GlobalSettingsVariable
} from 'cmk-shared-typing/typescript/global_settings'
import CmkAccordion from 'cmk-ui-library/components/CmkAccordion/CmkAccordion.vue'
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkBreadcrumb from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDebounceRef } from 'cmk-ui-library/lib/useDebounce'
import { computed, inject, onMounted, provide, ref, toRaw, watch } from 'vue'

import { GLOBAL_SETTINGS_SERVICE, GLOBAL_SETTINGS_TOGGLE, globalSettingsService } from './api'
import ExpandCollapseButtons from './components/ExpandCollapseButtons.vue'
import GlobalSettingsEditor from './components/GlobalSettingsEditor.vue'
import GlobalSettingsEmptyState from './components/GlobalSettingsEmptyState.vue'
import GlobalSettingsModificationFilter from './components/GlobalSettingsModificationFilter.vue'
import GlobalSettingsTopic from './components/GlobalSettingsTopic.vue'
import { type ModificationFilter, isModified, isSiteOverride } from './lib/origin'
import { type VariableFilter, buildSearchIndex, matchTopics } from './lib/search'
import { applyReceived, describeError, useGlobalSettingsEditor } from './useGlobalSettingsEditor'

const { _t } = usei18n()

const props = defineProps<GlobalSettingsApp>()

const service = inject(GLOBAL_SETTINGS_SERVICE, globalSettingsService)

const SEARCH_URL_PARAM = 'search'
const FILTER_URL_PARAM = 'filter'
const VARNAME_URL_PARAM = 'varname'

function urlParam(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name)
}

const hasSiteOverrides =
  props.topics.some((topic) =>
    topic.variables.some((variable) => isSiteOverride(variable, props.scope))
  ) || props.scope.type === 'site'

function parseModificationFilter(value: string | null): ModificationFilter {
  switch (value) {
    case 'modified':
      return value
    case 'site':
      return hasSiteOverrides ? value : 'all'
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
const inSiteScope = computed(() => props.scope.type === 'site')
const query = ref(urlParam(SEARCH_URL_PARAM) ?? '')
const debouncedQuery = useDebounceRef(query, 100)
const searchActive = computed(() => debouncedQuery.value.trim() !== '')

const modification = ref<ModificationFilter>(parseModificationFilter(urlParam(FILTER_URL_PARAM)))
const variableFilter = computed<VariableFilter | null>(() => {
  switch (modification.value) {
    case 'modified':
      return isModified
    case 'site':
      return (variable) => isSiteOverride(variable, props.scope)
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

// Only the search and the topic tags touch the open sections, the filter leaves them as they are.
const openedItems = ref<string[]>(openedItemsForQuery())

watch(debouncedQuery, () => {
  openedItems.value = openedItemsForQuery()
})

watch([debouncedQuery, modification, session], ([value, filter, editing]) => {
  // replaceState, not pushState: typing must not fill the back stack.
  const url = new URL(window.location.href)
  setOrDelete(url.searchParams, SEARCH_URL_PARAM, value.trim() === '' ? null : value)
  setOrDelete(url.searchParams, FILTER_URL_PARAM, filter === 'all' ? null : filter)
  setOrDelete(url.searchParams, VARNAME_URL_PARAM, editing?.variable.name ?? null)
  window.history.replaceState({}, '', url)
})

function openVariableFromUrl(): void {
  const name = urlParam(VARNAME_URL_PARAM)
  for (const topic of editableTopics.value) {
    const variable = topic.variables.find((candidate) => candidate.name === name)
    if (variable !== undefined) {
      openedItems.value = [...new Set([...openedItems.value, topic.headline])]
      void openEditor(variable)
      return
    }
  }
}

onMounted(openVariableFromUrl)

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

function showOnly(headline: string, filter: ModificationFilter): void {
  modification.value = filter
  openedItems.value = [headline]
}

function resetSearchAndFilters(): void {
  query.value = ''
  modification.value = 'all'
}
</script>

<template>
  <div class="global-settings-app">
    <CmkBreadcrumb :items="breadcrumb" />
    <div class="global-settings-app__toolbar">
      <CmkSearchInput
        v-model="query"
        class="global-settings-app__search"
        :placeholder="_t('Search settings…')"
        :show-submit-button="false"
      />
      <div class="global-settings-app__toolbar-right">
        <GlobalSettingsModificationFilter
          v-model="modification"
          :scope="scope"
          :show-site-overrides="hasSiteOverrides"
        />
        <ExpandCollapseButtons
          @expand-all="openedItems = shownTopics.map((topic) => topic.headline)"
          @collapse-all="openedItems = []"
        />
      </div>
    </div>
    <CmkAlertBox variant="warning">
      {{ _t('This page is work in progress. It shows a subset of the global settings.') }}
    </CmkAlertBox>
    <GlobalSettingsEmptyState v-if="shownTopics.length === 0" @reset="resetSearchAndFilters" />
    <CmkAccordion v-else v-model="openedItems" :min-open="0" :max-open="0">
      <GlobalSettingsTopic
        v-for="topic in shownTopics"
        :key="topic.headline"
        :topic="topic"
        :scope="scope"
        :value="topic.headline"
        :match="shownVariablesOf(topic.headline)"
        :query="debouncedQuery"
        @edit="openEditor"
        @filter="showOnly(topic.headline, $event)"
      />
    </CmkAccordion>
    <CmkSlideInDialog
      :open="session !== null"
      size="small"
      :header="{
        title: inSiteScope ? _t('Edit site-specific setting') : _t('Edit global setting'),
        closeButton: true
      }"
      @close="closeEditor"
    >
      <GlobalSettingsEditor v-if="session !== null" :session="session" @close="closeEditor" />
    </CmkSlideInDialog>
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
