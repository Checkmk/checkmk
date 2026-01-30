/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ProviderName } from 'cmk-shared-typing/typescript/unified_search'
import { type InjectionKey, type Ref, inject, provide, ref } from 'vue'

import { KeyShortcutService } from '@/lib/keyShortcuts'
import { randomId } from '@/lib/randomId'
import usePersistentRef from '@/lib/usePersistentRef'

import type { SearchHistoryService } from '@/unified-search/lib/searchHistory'
import type { UnifiedSearch } from '@/unified-search/lib/unified-search'

import type {
  FilterOption,
  ProviderOption,
  QueryProvider,
  UnifiedSearchQueryLike
} from './search-utils.types'

declare const cmk: any

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
const callbacks: {
  [key: string]: { id: string; cb: (...args: any) => void }[]
} = {}

function ensureKey(key: string) {
  if (!callbacks[key]) {
    callbacks[key] = []
  }
}

function pushCallBack(key: string, cb: (...args: any) => void) {
  ensureKey(key)
  const id = randomId()
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

function hideSuggestions() {
  dispatchCallback('hideSuggestions')
}

function onHideSuggestions(cb: typeof hideSuggestions): string {
  return pushCallBack('hideSuggestions', cb)
}

function setResultGrouping(grouping: boolean) {
  dispatchCallback('setResultGrouping', grouping)
}

function onSetResultGrouping(cb: typeof setResultGrouping): string {
  return pushCallBack('setResultGrouping', cb)
}

function openSearch() {
  cmk.popup_menu.close_popup()
  cmk.handle_main_menu('search')
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

function ctrlArrowUp() {
  dispatchCallback('ctrlArrowUp')
}

function onCtrlArrowUp(cb: typeof ctrlArrowUp): string {
  return pushCallBack('ctrlArrowUp', cb)
}

function ctrlArrowDown() {
  dispatchCallback('ctrlArrowDown')
}

function onCtrlArrowDown(cb: typeof ctrlArrowDown): string {
  return pushCallBack('ctrlArrowDown', cb)
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

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowDown'] }, arrowDown))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowUp'] }, arrowUp))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowLeft'] }, arrowLeft))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowRight'] }, arrowRight))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowLeft'], ctrl: true }, ctrlArrowLeft))

  shortCutEventIds.value.push(shortcuts.on({ key: ['ArrowRight'], ctrl: true }, ctrlArrowRight))

  shortCutEventIds.value.push(
    shortcuts.on({ key: ['ArrowUp'], ctrl: true, preventDefault: true }, ctrlArrowUp)
  )

  shortCutEventIds.value.push(
    shortcuts.on({ key: ['ArrowDown'], ctrl: true, preventDefault: true }, ctrlArrowDown)
  )
}

function disableShortCuts() {
  shortcuts.remove(shortCutEventIds.value)
  shortCutEventIds.value = []
}

function highlightQuery(s: string): string {
  if (!query.input.value) {
    return s
  }
  const sanitized = query.input.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').trimEnd()
  const regex = new RegExp(sanitized, 'ig')
  return s.replace(regex, `<span class="highlight-query">$&</span>`)
}

function breadcrumb(provider: ProviderName, topic: string): string[] {
  const breadcrumb: string[] = [provider]
  if (provider.toLowerCase() !== topic.toLowerCase()) {
    breadcrumb.push(topic)
  }
  return breadcrumb
}

function getGroupPersistentRef(searchId: string, groupId: string): Ref<boolean> {
  return usePersistentRef<boolean>(
    searchId.concat('-grouping-open-').concat(groupId),
    true,
    (v) => v as boolean,
    'local'
  )
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
  onCtrlArrowUp: typeof onCtrlArrowUp
  onCtrlArrowDown: typeof onCtrlArrowDown
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
  hideSuggestions: typeof hideSuggestions
  onHideSuggestions: typeof onHideSuggestions
  suggestionsActive: typeof suggestionsActive
  providerSelectActive: typeof providerSelectActive
  searchOperatorSelectActive: typeof searchOperatorSelectActive
}

export interface SearchResultOptions {
  getGroupPersistentRef: typeof getGroupPersistentRef
  setResultGrouping: typeof setResultGrouping
  onSetResultGrouping: typeof onSetResultGrouping
  grouping: Ref<boolean>
}
export interface InitSearchUtils {
  openSearch: typeof openSearch
  resetSearch: typeof resetSearch
  onResetSearch: typeof onResetSearch
  closeSearch: typeof closeSearch
  onCloseSearch: typeof onCloseSearch
  shortCuts: SearchShortCuts
  query: typeof query
  input: SearchInputUtils
  result: SearchResultOptions
}

export interface SearchUtils extends InitSearchUtils {
  id: string
  highlightQuery: typeof highlightQuery
  breadcrumb: typeof breadcrumb
  search?: UnifiedSearch
  history?: SearchHistoryService
}

export const searchUtilsProvider = Symbol() as InjectionKey<SearchUtils>

export function initSearchUtils(id: string): SearchUtils {
  return {
    id,
    openSearch,
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
      onCtrlArrowUp,
      onCtrlArrowDown,
      onCtrlK,
      onEscape,
      onCtrlEnter
    },
    highlightQuery,
    breadcrumb,
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
      hideSuggestions,
      onHideSuggestions,
      suggestionsActive,
      providerSelectActive,
      searchOperatorSelectActive
    },
    result: {
      getGroupPersistentRef,
      setResultGrouping,
      onSetResultGrouping,
      grouping: usePersistentRef<boolean>(
        id.concat('-grouping'),
        false,
        (v) => v as boolean,
        'local'
      )
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
