/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { type Ref, ref } from 'vue'

import { useMaps, useToast } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'
import type { CfgImport, MapConfig } from '@/maps/types/api'

interface ImportConflict {
  name: string
  overwrite: () => Promise<string[]>
  // Carried along so confirming the overwrite still reports what the import
  // had to guess — the answer arrived before the conflict was known.
  warnings: string[]
}

/**
 * Bringing a map file into the site.
 *
 * ``.cfg`` files are the legacy NagVis format and go through the GUI's
 * importer (stateless — the daemon owns only live state); everything else is
 * read as a JSON map config. A name that is already taken raises an overwrite
 * confirmation instead of failing the import outright.
 *
 * The ``.cfg`` importer has to remap the source installation's monitoring
 * backends onto the connections configured here; it names every such guess, and
 * those are surfaced once the map is actually stored.
 *
 * A map file names its background image but does not bring it. Where the
 * server knows no such image for the map, the map is stored without it and the
 * operator is told to upload it.
 */
export function useMapImport(): {
  conflict: Ref<ImportConflict | null>
  importFile: (event: Event) => Promise<void>
  confirmOverwrite: () => Promise<void>
  dismissConflict: () => void
} {
  const maps = useMaps()
  const toast = useToast()
  const { _t } = usei18n()

  const conflict = ref<ImportConflict | null>(null)

  function isNameTaken(error: unknown): boolean {
    return error instanceof Error && error.message.includes('already exists')
  }

  function reportFailure(error: unknown): void {
    toast.error(errorText(error, _t('Import failed')))
  }

  function reportWarnings(warnings: string[]): void {
    // Server-composed and already localized; untranslated() is only the bridge
    // into the toast's TranslatedString (as in errorText).
    for (const warning of warnings) {
      toast.warning(untranslated(warning))
    }
  }

  function isUnknownBackground(error: unknown): boolean {
    if (!(error instanceof CmkApiError) || error.statusCode !== 400) {
      return false
    }
    const ext = (error.body as { ext?: { error?: unknown } } | undefined)?.ext
    return ext?.error === 'unknown_background'
  }

  /** Stores the map; returns what the operator has to know about how it was stored. */
  async function store(map: MapConfig, overwrite: boolean): Promise<string[]> {
    try {
      await maps.importMapJson(map, overwrite)
      return []
    } catch (error: unknown) {
      if (!map.background_image || !isUnknownBackground(error)) {
        throw error
      }
    }
    const { background_image: image, ...withoutBackground } = map
    await maps.importMapJson(withoutBackground, overwrite)
    return [
      _t(
        "The background image %{image} is not part of the map file. Upload it in the map's settings under Background image.",
        { image }
      )
    ]
  }

  async function readMap(file: File): Promise<CfgImport> {
    if (file.name.toLowerCase().endsWith('.cfg')) {
      return await maps.parseCfg(file)
    }
    return { map: JSON.parse(await file.text()) as MapConfig, warnings: [] }
  }

  async function importFile(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) {
      return
    }
    try {
      const { map, warnings } = await readMap(file)
      let stored: string[]
      try {
        stored = await store(map, false)
      } catch (error: unknown) {
        if (!isNameTaken(error)) {
          throw error
        }
        conflict.value = {
          name: map.name,
          overwrite: () => store(map, true),
          warnings
        }
        return
      }
      await maps.fetchMaps()
      reportWarnings([...warnings, ...stored])
    } catch (error: unknown) {
      reportFailure(error)
    } finally {
      // Cleared so picking the same file again still fires a change event.
      input.value = ''
    }
  }

  async function confirmOverwrite(): Promise<void> {
    const pending = conflict.value
    if (!pending) {
      return
    }
    conflict.value = null
    try {
      const stored = await pending.overwrite()
      await maps.fetchMaps()
      reportWarnings([...pending.warnings, ...stored])
    } catch (error: unknown) {
      reportFailure(error)
    }
  }

  function dismissConflict(): void {
    conflict.value = null
  }

  return { conflict, importFile, confirmOverwrite, dismissConflict }
}
