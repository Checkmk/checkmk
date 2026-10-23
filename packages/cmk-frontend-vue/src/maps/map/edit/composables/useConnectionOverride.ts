/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { type ComputedRef, computed, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'

/**
 * The connections an object may read from instead of the map's own, offered as
 * a dropdown whose empty value means "inherit from map".
 */
export function useConnectionOverride(): { options: ComputedRef<Suggestions> } {
  const { connections: connectionsApi } = useMapsApis()
  const { _t } = usei18n()

  const connections = ref<{ id: string; label: string }[]>([])

  void (async () => {
    try {
      connections.value = (await connectionsApi.list()).map((connection) => ({
        id: connection.id,
        label: connection.label || connection.id
      }))
    } catch {
      connections.value = []
    }
  })()

  const options = computed<Suggestions>(() => ({
    type: 'fixed',
    suggestions: [
      { name: '', title: _t('Inherit from map') },
      ...connections.value.map((connection) => ({
        name: connection.id,
        title: untranslated(connection.label)
      }))
    ]
  }))

  return { options }
}
