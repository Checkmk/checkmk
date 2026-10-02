/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// The flamegraph wire format is defined once in
// packages/cmk-shared-typing/source/profiling_flamegraph.json and generated for
// both the backend (dataclasses) and the frontend (these interfaces). Re-exported
// here so the profiling components keep importing from a single local module.
import type {
  CallerInfo,
  FlamegraphNode,
  HotspotData,
  ProfileMetadata,
  ProfileSourceType,
  ProfilingFlamegraphData
} from 'cmk-shared-typing/typescript/profiling_flamegraph'

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
