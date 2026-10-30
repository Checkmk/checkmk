/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, type Ref, computed, ref } from 'vue'

import { getCustomGraph, listCustomGraphMetadata } from '@/graphing/designer/api'

import type { UseEmbeddedCustomGraph } from '../../create/composables/useEmbeddedCustomGraph'

const { _t } = usei18n()

const DEFAULT_TITLE = '$DEFAULT_TITLE$'

interface CatalogGraph {
  name: string
  owner: string
  title: string
}

const errorMessage = (reason: unknown): string =>
  reason instanceof Error ? reason.message : String(reason)

// Graphs of different owners may share a name, so a pick names both.
const catalogKey = (graph: CatalogGraph): string => `${graph.owner}/${graph.name}`

interface SelectedGraph {
  key: string
  title: string
}

export interface UseCustomGraphClone {
  /** The catalog graphs to clone from, as menu items keyed by owner and name. */
  catalogItems: ComputedRef<CmkMenuItem[]>
  /** The catalog graph the copy was made from. */
  selected: Ref<SelectedGraph | null>
  loading: Ref<boolean>
  /** Why the catalog or the picked graph could not be loaded. */
  error: Ref<string | null>
  selectionErrors: Ref<string[]>
  /** Whether the copy's sources or options differ from the cloned graph's. */
  hasEdits: (editorModified: boolean) => boolean
  /** Marks the copy as edited, so an editor mounted later (e.g. coming back to stage 1
   *  from stage 2) knows about the modified state. */
  markAsEdited: () => void
  /** Replaces the copy with one of the catalog graph of the given key. */
  clone: (key: string) => Promise<void>
  validate: () => boolean
}

/** `initialGraph` names a catalog graph to copy as soon as the catalog has loaded. */
export function useCustomGraphClone(
  handler: UseEmbeddedCustomGraph,
  initialGraph: string | null = null
): UseCustomGraphClone {
  const catalog = ref<CatalogGraph[]>([])
  const selected = ref<SelectedGraph | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectionErrors = ref<string[]>([])

  let editedSources = false
  let clonedOptions: string | null = null
  // Counts clones, so the response to a request that was overtaken by a later request is dropped
  let latestClone = 0

  const catalogItems = computed<CmkMenuItem[]>(() =>
    catalog.value.map((graph) => ({
      label: [{ text: graph.title }],
      value: catalogKey(graph),
      icon: 'clone'
    }))
  )

  const loadCatalog = async (): Promise<void> => {
    try {
      const collection = await listCustomGraphMetadata()
      catalog.value = collection.value.flatMap((entry) =>
        entry.id === undefined
          ? []
          : [{ name: entry.id, owner: entry.extensions.owner, title: entry.title ?? entry.id }]
      )
    } catch (reason) {
      error.value = errorMessage(reason)
    }
  }
  const hasEdits = (editorModified: boolean): boolean =>
    editedSources ||
    editorModified ||
    (clonedOptions !== null && JSON.stringify(handler.graphOptions.value) !== clonedOptions)

  const markAsEdited = (): void => {
    editedSources = true
  }

  const clone = async (key: string): Promise<void> => {
    const picked = catalog.value.find((graph) => catalogKey(graph) === key)
    if (picked === undefined) {
      return
    }
    const previousTitle = selected.value?.title ?? null
    selected.value = { key, title: picked.title }
    selectionErrors.value = []
    error.value = null
    editedSources = false
    clonedOptions = null
    handler.dataSources.value = []

    const request = ++latestClone
    loading.value = true
    try {
      const { graph } = await getCustomGraph(picked.name, picked.owner)
      if (request !== latestClone) {
        return
      }
      handler.dataSources.value = graph.extensions.content.data_sources
      handler.graphOptions.value = graph.extensions.content.graph_options
      clonedOptions = JSON.stringify(graph.extensions.content.graph_options)

      // Only a title the user has not changed follows the cloned graph.
      const title = handler.visualization.title
      if (title.value === DEFAULT_TITLE || title.value === previousTitle) {
        title.value = picked.title
      }
    } catch (reason) {
      if (request !== latestClone) {
        return
      }
      // Nothing was cloned, so the same graph can be picked again.
      selected.value = null
      error.value = errorMessage(reason)
    } finally {
      if (request === latestClone) {
        // Also re-mounts the editor, so it starts over from the copy.
        loading.value = false
      }
    }
  }

  const validate = (): boolean => {
    selectionErrors.value = selected.value === null ? [_t('Select a custom graph to clone.')] : []
    return selectionErrors.value.length === 0 && error.value === null
  }

  // The catalog holds one graph per name, the one a linked widget shows.
  void loadCatalog().then(() => {
    if (initialGraph === null) {
      return
    }
    const linked = catalog.value.find((graph) => graph.name === initialGraph)
    if (linked !== undefined) {
      void clone(catalogKey(linked))
    } else if (error.value === null) {
      error.value = _t('The linked custom graph is not available for cloning.')
    }
  })

  return {
    catalogItems,
    selected,
    loading,
    error,
    selectionErrors,
    hasEdits,
    markAsEdited,
    clone,
    validate
  }
}
