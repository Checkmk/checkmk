/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  CallerInfo,
  FlamegraphNode,
  HotspotData,
  ProfileMetadata,
  ProfileSourceType,
  ProfilingFlamegraphData
} from './shared_typing/flamegraph'

export type {
  CallerInfo,
  FlamegraphNode,
  HotspotData,
  ProfileMetadata,
  ProfileSourceType,
  ProfilingFlamegraphData
}

/** A laid-out rectangle ready for rendering. Frontend-only; not part of the wire format. */
export interface LayoutRect {
  x: number
  y: number
  width: number
  height: number
  name: string
  selfTime: number
  totalTime: number
  depth: number
  node: FlamegraphNode
}
