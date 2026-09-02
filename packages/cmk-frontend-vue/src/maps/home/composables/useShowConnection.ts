/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed } from 'vue'

import { useAuth, useConnections } from '@/maps/services/context'

/**
 * Whether a listed map should name the monitoring connection it runs against.
 *
 * It is administration, so only an administrator sees it — and only where there
 * is something to tell apart: on an installation with a single connection the
 * same name would sit on every map and distinguish nothing.
 *
 * The card, the table and the table's header all ask here, because a header
 * that disagrees with its cells shifts the whole row.
 */
export function useShowConnection(): ComputedRef<boolean> {
  const auth = useAuth()
  const connections = useConnections()
  return computed(() => auth.isAdmin.value && connections.connections.value.length > 1)
}
