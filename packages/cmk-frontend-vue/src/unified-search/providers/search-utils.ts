/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { inject, provide, type InjectionKey, type Ref, ref } from 'vue'
import type { UnifiedSearch } from '@/lib/unified-search/unified-search'
import { KeyShortcutService } from '@/lib/keyShortcuts'
import type { UnifiedSearchProviderIdentifier } from '@/lib/unified-search/providers/unified'
import type { SearchHistoryService } from '@/lib/unified-search/searchHistory'

const query = ref<string>('')
const shortcuts = new KeyShortcutService(window)
const shortCutEventIds = ref<string[]>([])
const callbacks: { [key: string]: { id: string; cb: (query?: string) => void }[] } = {}

function ensureKey(key: string) {
  if (!callbacks[key]) {
    callbacks[key] = []
  }
}

function pushCallBack(key: string, cb: (query?: string) => void) {
  ensureKey(key)
  const id = crypto.randomUUID()
  callbacks[key]?.push({ id, cb })
  return id
}

function dispatchCallback(key: string, query?: string) {
  ensureKey(key)
  callbacks[key]?.forEach((c) => {
    c.cb(query)
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

function setValue(query?: string) {
  dispatchCallback('setValue', query)
}

function onSetValue(cb: typeof setValue): string {
  return pushCallBack('setValue', cb)
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
  return s.replace(new RegExp(query.value, 'ig'), `<span class="highlight-query">$&</span>`)
}

function breadcrumb(provider: UnifiedSearchProviderIdentifier, topic: string): string[] {
  const breadcrumb: string[] = [provider]
  if (provider.toLowerCase() !== topic.toLowerCase()) {
    breadcrumb.push(topic)
  }

  return breadcrumb
}

export interface SearchShortCuts {
  enable: typeof enableShortCuts
  disable: typeof disableShortCuts
  remove: typeof removeShortCuts
  onArrowDown: typeof onArrowDown
  onArrowUp: typeof onArrowUp
  onCtrlArrowLeft: typeof onCtrlArrowLeft
  onCtrlArrowRight: typeof onCtrlArrowRight
  onCtrlK: typeof onCtrlK
  onEscape: typeof onEscape
  onCtrlEnter: typeof onCtrlEnter
}

export interface SearchInputUtils {
  setValue: typeof setValue
  onSetValue: typeof onSetValue
  setFocus: typeof setFocus
  onSetFocus: typeof onSetFocus
  setBlur: typeof setBlur
  onSetBlur: typeof onSetBlur
}

export interface InitSearchUtils {
  resetSearch: typeof resetSearch
  onResetSearch: typeof onResetSearch
  closeSearch: typeof closeSearch
  onCloseSearch: typeof onCloseSearch
  shortCuts: SearchShortCuts
  input: SearchInputUtils
  query: Ref<string>
}

export interface SearchUtils extends InitSearchUtils {
  highlightQuery: typeof highlightQuery
  breadcrumb: typeof breadcrumb
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
      onCtrlArrowLeft,
      onCtrlArrowRight,
      onCtrlK,
      onEscape,
      onCtrlEnter
    },
    query: query,
    highlightQuery: highlightQuery,
    breadcrumb,
    input: {
      setValue,
      onSetValue,
      setFocus,
      onSetFocus,
      setBlur,
      onSetBlur
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
