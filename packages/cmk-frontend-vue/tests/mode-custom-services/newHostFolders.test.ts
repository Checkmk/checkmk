/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'
import { ref } from 'vue'

import type { HostNameTemplateResolution } from '@/mode-custom-services/definition'
import {
  type CreatableFolder,
  newHostFoldersOf,
  newHostFoldersToSend,
  useNewHostFolders
} from '@/mode-custom-services/newHostFolders'
import type { TemplatePreview } from '@/mode-custom-services/templatePreview'

const MAIN: CreatableFolder = { path: '/', title: 'Main' }
const SHOP: CreatableFolder = { path: '/k8s/shop', title: 'Main / K8s / Shop' }
const SEARCH: CreatableFolder = { path: '/k8s/search', title: 'Main / K8s / Search' }

function resolved(
  unmatchedHostNames: string[],
  creatableFolders: CreatableFolder[]
): TemplatePreview {
  const resolution: HostNameTemplateResolution = {
    matching_hosts: [],
    unmatched_host_names: unmatchedHostNames,
    hidden_match_count: 0,
    truncated: false,
    creatable_folders: creatableFolders
  }
  return { status: 'resolved', resolution }
}

test('new hosts go to Main unless another folder is chosen', () => {
  expect(
    newHostFoldersOf({ 'pod-cart': SHOP.path }, resolved(['pod-cart', 'pod-search'], [MAIN, SHOP]))
  ).toEqual({ 'pod-cart': '/k8s/shop', 'pod-search': '/' })
})

test('new hosts go to the first offered folder if Main is not offered', () => {
  expect(newHostFoldersOf({}, resolved(['pod-cart'], [SEARCH, SHOP]))).toEqual({
    'pod-cart': '/k8s/search'
  })
})

test('a chosen folder that is no longer offered falls back to the default', () => {
  expect(newHostFoldersOf({ 'pod-cart': SHOP.path }, resolved(['pod-cart'], [MAIN]))).toEqual({
    'pod-cart': '/'
  })
})

test('only hosts saving creates get a folder', () => {
  expect(newHostFoldersOf({ 'pod-old': SHOP.path }, resolved(['pod-cart'], [MAIN, SHOP]))).toEqual({
    'pod-cart': '/'
  })
})

test('no folder is named while no folder is offered or the template is not resolved', () => {
  expect(newHostFoldersOf({}, resolved(['pod-cart'], []))).toEqual({})
  expect(newHostFoldersOf({ 'pod-cart': SHOP.path }, { status: 'loading' })).toEqual({})
})

test('hosts going to Main are not sent, as the endpoint creates them there anyway', () => {
  expect(newHostFoldersToSend({ 'pod-cart': '/k8s/shop', 'pod-search': '/' })).toEqual({
    'pod-cart': '/k8s/shop'
  })
})

test('a choice is kept while its host is new again after the template changed', () => {
  const preview = ref<TemplatePreview>(resolved(['pod-cart'], [MAIN, SHOP]))
  const choice = useNewHostFolders(() => preview.value)

  choice.choose(['pod-cart'], SHOP.path)
  preview.value = resolved(['pod-search'], [MAIN, SHOP])
  expect(choice.folders.value).toEqual({ 'pod-search': '/' })
  preview.value = resolved(['pod-cart', 'pod-search'], [MAIN, SHOP])

  expect(choice.folders.value).toEqual({ 'pod-cart': '/k8s/shop', 'pod-search': '/' })
  expect(choice.toSend.value).toEqual({ 'pod-cart': '/k8s/shop' })
})
