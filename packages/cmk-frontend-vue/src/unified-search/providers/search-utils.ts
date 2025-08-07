/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import { inject, provide, type InjectionKey, ref } from 'vue'
import type { UnifiedSearch } from '@/lib/unified-search/unified-search'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import type { UnifiedSearchProviderIdentifier } from '@/lib/unified-search/providers/unified'
import type { SearchHistoryService } from '@/lib/unified-search/searchHistory'
import type { CmkIconProps } from '@/components/CmkIcon.vue'
import { topicIconMapping } from './topic-icon-mapping'
import type {
  FilterOption,
  ProviderOption,
  QueryProvider,
  SearchProviderKeys,
  UnifiedSearchQueryLike
} from './search-utils.types'

const queryInput = ref<string>('')
const queryProvider = ref<QueryProvider>('all')
const queryFilters = ref<FilterOption[]>([])
const sort = ref<string>('weighted_index')

const suggestionsActive = ref<boolean>(false)
const providerSelectActive = ref<boolean>(false)
const searchOperatorSelectActive = ref<boolean>(false)
const query = {
  input: queryInput,
  provider: queryProvider,
  filters: queryFilters,
  toQueryLike: (): UnifiedSearchQueryLike => {
    return {
      input: queryInput.value,
      provider: queryProvider.value,
      filters: queryFilters.value,
      sort: sort.value
    }
  },
  sort: sort
}
const shortcuts = new KeyShortcutService(window)
const shortCutEventIds = ref<string[]>([])
const callbacks: { [key: string]: { id: string; cb: (...args: any) => void }[] } = {}

function ensureKey(key: string) {
  if (!callbacks[key]) {
    callbacks[key] = []
  }
}

function pushCallBack(key: string, cb: (...args: any) => void) {
  ensureKey(key)
  const id = crypto.randomUUID()
  callbacks[key]?.push({ id, cb })
  return id
}

function dispatchCallback(key: string, ...args: any) {
  ensureKey(key)
  callbacks[key]?.forEach((c) => {
    c.cb(...args)
  })
}

function removeShortCuts(ids: string[]) {
  for (const key of Object.keys(callbacks)) {
    if (callbacks[key]) {
      callbacks[key] = callbacks[key]?.filter((c) => {
        return ids.indexOf(c.id) < 0
      })
    }
  }
}

function setQuery(query?: UnifiedSearchQueryLike) {
  dispatchCallback('setQuery', query)
}

function onSetQuery(cb: typeof setQuery): string {
  return pushCallBack('setQuery', cb)
}

function setInputValue(query?: string, noSet?: boolean) {
  dispatchCallback('setInputValue', query, noSet)
}

function onSetInputValue(cb: typeof setInputValue): string {
  return pushCallBack('setInputValue', cb)
}

function setProviderValue(query?: ProviderOption, noSet?: boolean) {
  dispatchCallback('setProviderValue', query, noSet)
}

function onSetProviderValue(cb: typeof setProviderValue): string {
  return pushCallBack('setProviderValue', cb)
}

function setFilterValue(query?: FilterOption[], noSet?: boolean) {
  dispatchCallback('setFilterValue', query, noSet)
}

function onSetFilterValue(cb: typeof setFilterValue): string {
  return pushCallBack('setFilterValue', cb)
}

function setFocus() {
  dispatchCallback('setFocus')
}

function onSetFocus(cb: typeof setFocus): string {
  return pushCallBack('setFocus', cb)
}

function setBlur() {
  dispatchCallback('setBlur')
}

function onSetBlur(cb: typeof setBlur): string {
  return pushCallBack('setBlur', cb)
}

function emptyBackspace() {
  dispatchCallback('setEmptyBackspace')
}

function onEmptyBackspace(cb: typeof emptyBackspace): string {
  return pushCallBack('setEmptyBackspace', cb)
}

function resetSearch() {
  dispatchCallback('resetSearch')
}

function onResetSearch(cb: typeof resetSearch): string {
  return pushCallBack('resetSearch', cb)
}

function closeSearch() {
  dispatchCallback('closeSearch')
}

function onCloseSearch(cb: typeof closeSearch): string {
  return pushCallBack('closeSearch', cb)
}

function arrowDown() {
  dispatchCallback('arrowDown')
}

function onArrowDown(cb: typeof arrowDown): string {
  return pushCallBack('arrowDown', cb)
}

function arrowUp() {
  dispatchCallback('arrowUp')
}

function onArrowUp(cb: typeof arrowUp): string {
  return pushCallBack('arrowUp', cb)
}

function arrowLeft() {
  dispatchCallback('arrowLeft')
}

function onArrowLeft(cb: typeof arrowLeft): string {
  return pushCallBack('arrowLeft', cb)
}

function arrowRight() {
  dispatchCallback('arrowRight')
}

function onArrowRight(cb: typeof arrowRight): string {
  return pushCallBack('arrowRight', cb)
}

function ctrlArrowLeft() {
  dispatchCallback('ctrlArrowLeft')
}

function onCtrlArrowLeft(cb: typeof ctrlArrowLeft): string {
  return pushCallBack('ctrlArrowLeft', cb)
}

function ctrlArrowRight() {
  dispatchCallback('ctrlArrowRight')
}

function onCtrlArrowRight(cb: typeof ctrlArrowRight): string {
  return pushCallBack('ctrlArrowRight', cb)
}

function ctrlK() {
  dispatchCallback('ctrlK')
}

function onCtrlK(cb: typeof ctrlK): string {
  return pushCallBack('ctrlK', cb)
}

function escape() {
  dispatchCallback('escape')
}

function onEscape(cb: typeof escape): string {
  return pushCallBack('escape', cb)
}

function ctrlEnter() {
  dispatchCallback('ctrlEnter')
}

function onCtrlEnter(cb: typeof ctrlEnter): string {
  return pushCallBack('ctrlEnter', cb)
}

function enableShortCuts() {
  shortCutEventIds.value.push(shortcuts.on({ key: ['k'], ctrl: true, preventDefault: true }, ctrlK))

  shortCutEventIds.value.push(shortcuts.on({ key: ['Escape'] }, escape))

  shortCutEventIds.value.push(shortcuts.on({ key: ['Enter'], ctrl: true }, ctrlEnter))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowDown'], preventDefault: true }, arrowDown))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowUp'], preventDefault: true }, arrowUp))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowLeft'], preventDefault: true }, arrowLeft))

  shortCutEventIds.value.push(
    shortcuts.on({ key: ['ArrowRight'], preventDefault: true }, arrowRight)
  )

  shortCutEventIds.value.push(
    shortcuts.on({ key: ['ArrowLeft'], ctrl: true, preventDefault: true }, ctrlArrowLeft)
  )

  shortCutEventIds.value.push(
    shortcuts.on({ key: ['ArrowRight'], ctrl: true, preventDefault: true }, ctrlArrowRight)
  )
}

function disableShortCuts() {
  shortcuts.remove(shortCutEventIds.value)
  shortCutEventIds.value = []
}

function highlightQuery(s: string): string {
  return s.replace(new RegExp(query.input.value, 'ig'), `<span class="highlight-query">$&</span>`)
}

function breadcrumb(provider: UnifiedSearchProviderIdentifier, topic: string): string[] {
  const breadcrumb: string[] = [provider]
  if (provider.toLowerCase() !== topic.toLowerCase()) {
    breadcrumb.push(topic)
  }
  return breadcrumb
}

function mapIcon(topic: string, provider: SearchProviderKeys): CmkIconProps {
  topic = topic
    .toLowerCase()
    .replace(/ /g, '_')
    .replace(/[^a-zA-Z0-9_]+/g, '')

  let name = topicIconMapping[provider][topic]
  if (!name) {
    if (name !== null) {
      console.error('topic', topic, 'not found for provider', provider) // keep in to easily find unmapped icons
    }
    name = `main-${provider}-active`
  } else {
    name = 'topic-'.concat(name)
  }

  return {
    name
  }
}

export interface SearchShortCuts {
  enable: typeof enableShortCuts
  disable: typeof disableShortCuts
  remove: typeof removeShortCuts
  onArrowDown: typeof onArrowDown
  onArrowUp: typeof onArrowUp
  onArrowLeft: typeof onArrowLeft
  onArrowRight: typeof onArrowRight
  onCtrlArrowLeft: typeof onCtrlArrowLeft
  onCtrlArrowRight: typeof onCtrlArrowRight
  onCtrlK: typeof onCtrlK
  onEscape: typeof onEscape
  onCtrlEnter: typeof onCtrlEnter
}

export interface SearchInputUtils {
  setQuery: typeof setQuery
  onSetQuery: typeof onSetQuery
  setInputValue: typeof setInputValue
  onSetInputValue: typeof onSetInputValue
  setProviderValue: typeof setProviderValue
  onSetProviderValue: typeof onSetProviderValue
  setFilterValue: typeof setFilterValue
  onSetFilterValue: typeof onSetFilterValue
  setFocus: typeof setFocus
  onSetFocus: typeof onSetFocus
  setBlur: typeof setBlur
  onSetBlur: typeof onSetBlur
  emptyBackspace: typeof emptyBackspace
  onEmptyBackspace: typeof onEmptyBackspace
  suggestionsActive: typeof suggestionsActive
  providerSelectActive: typeof providerSelectActive
  searchOperatorSelectActive: typeof searchOperatorSelectActive
}

export interface InitSearchUtils {
  resetSearch: typeof resetSearch
  onResetSearch: typeof onResetSearch
  closeSearch: typeof closeSearch
  onCloseSearch: typeof onCloseSearch
  shortCuts: SearchShortCuts
  query: typeof query
  input: SearchInputUtils
}

export interface SearchUtils extends InitSearchUtils {
  highlightQuery: typeof highlightQuery
  breadcrumb: typeof breadcrumb
  mapIcon: typeof mapIcon
  search?: UnifiedSearch
  history?: SearchHistoryService
}

export const searchUtilsProvider = Symbol() as InjectionKey<SearchUtils>

export function initSearchUtils(): SearchUtils {
  return {
    resetSearch,
    onResetSearch,
    closeSearch,
    onCloseSearch,
    shortCuts: {
      enable: enableShortCuts,
      disable: disableShortCuts,
      remove: removeShortCuts,
      onArrowDown,
      onArrowUp,
      onArrowLeft,
      onArrowRight,
      onCtrlArrowLeft,
      onCtrlArrowRight,
      onCtrlK,
      onEscape,
      onCtrlEnter
    },
    highlightQuery,
    breadcrumb,
    mapIcon,
    query: query,
    input: {
      setQuery,
      onSetQuery,
      setInputValue,
      onSetInputValue,
      setProviderValue,
      onSetProviderValue,
      setFilterValue,
      onSetFilterValue,
      setFocus,
      onSetFocus,
      setBlur,
      onSetBlur,
      emptyBackspace,
      onEmptyBackspace,
      suggestionsActive,
      providerSelectActive,
      searchOperatorSelectActive
    }
  }
}

export function provideSearchUtils(utils: SearchUtils): void {
  provide(searchUtilsProvider, utils)
}

export function getSearchUtils(): SearchUtils {
  const utils = inject(searchUtilsProvider)
  if (utils === undefined) {
    throw Error('can only be used inside unified search')
  }
  return utils
}
