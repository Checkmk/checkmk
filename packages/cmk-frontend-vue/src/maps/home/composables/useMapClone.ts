/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, ref } from 'vue'

import { useMaps } from '@/maps/services/context'
import { errorText } from '@/maps/shared/errorText'
import type { MapRead } from '@/maps/types/api'
import { sanitizeMapName } from '@/maps/utils/naming'

/**
 * Copying a map: what the copy is called, and what went wrong if it did.
 *
 * The proposed id is ``<name>_copy``, sanitized as the operator types — a map
 * id is a file name on the site, so it cannot take everything a display name
 * can. The error stays in the dialog rather than becoming a toast: it is about
 * the value in the field the operator is looking at.
 */
export function useMapClone(): {
  source: Ref<string | null>
  name: Ref<string>
  alias: Ref<string>
  error: Ref<TranslatedString | null>
  start: (map: MapRead) => void
  cancel: () => void
  setName: (value: string) => void
  clone: () => Promise<void>
} {
  const maps = useMaps()
  const { _t } = usei18n()

  const source = ref<string | null>(null)
  const name = ref('')
  const alias = ref('')
  const error = ref<TranslatedString | null>(null)

  function start(map: MapRead): void {
    source.value = map.name
    name.value = `${map.name}_copy`
    alias.value = map.alias ? _t('%{alias} (Copy)', { alias: map.alias }) : ''
    error.value = null
  }

  function cancel(): void {
    source.value = null
  }

  function setName(value: string): void {
    name.value = sanitizeMapName(value)
  }

  async function clone(): Promise<void> {
    if (!source.value || !name.value) {
      return
    }
    try {
      await maps.cloneMap(source.value, name.value, alias.value || undefined)
      source.value = null
    } catch (e: unknown) {
      error.value = errorText(e, _t('Clone failed'))
    }
  }

  return { source, name, alias, error, start, cancel, setName, clone }
}
