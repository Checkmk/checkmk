/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { useMapsApis } from '@/maps/services/context'

type GroupType = 'hostgroup' | 'servicegroup'

interface RadarLikeForm {
  map_type: string
  radar_filter: string
  connection_id: string
  radar_filter_value: string
}

// Fetches the host- / service-group choices for a Radar map's filter field
// and resets the picked value when the operator switches the filter type so
// stale values can't survive the type swap.
export function useRadarGroups(form: Ref<RadarLikeForm>) {
  const { objects } = useMapsApis()
  const names = ref<string[]>([])
  const loading = ref(false)

  async function fetchGroups(type: GroupType) {
    if (!form.value.connection_id) {
      names.value = []
      return
    }
    loading.value = true
    try {
      names.value = await objects.fetchObjects(type)
    } catch {
      names.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => [form.value.map_type, form.value.radar_filter, form.value.connection_id] as const,
    ([mapType, filter], old) => {
      if (mapType === 'radar' && (filter === 'hostgroup' || filter === 'servicegroup')) {
        void fetchGroups(filter)
      } else {
        names.value = []
      }
      if (old && old[1] !== filter) {
        form.value.radar_filter_value = ''
      }
    },
    { immediate: true }
  )

  return { names, loading }
}
