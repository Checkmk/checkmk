/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapConfig, RenderMode } from '@/maps/types/api'

/** The rotation interval in minutes, out of its cascading-choice shape. */
function rotationIntervalOf(value: unknown): number {
  if (Array.isArray(value) && value.length === 2) {
    const [choice, minutes] = value
    if (choice === 'every' && typeof minutes === 'number') {
      return minutes
    }
  }
  return 0
}

/**
 * How each field of the metadata form is read into the map it describes.
 *
 * Three fields are shaped differently in the form than on the map: the click
 * action is a boolean choice there but 'link'/'none' here, the rotation
 * interval a cascading choice but a plain number, and a template left blank
 * means "no override" rather than an empty string. One table so the single-map
 * and the bulk dialog cannot drift apart on any of them.
 */
const METADATA_READERS: Record<string, (value: unknown) => Partial<MapConfig>> = {
  alias: (value) => ({ alias: value as string }),
  connection_id: (value) => ({ connection_id: value as string }),
  icon_size: (value) => ({ icon_size: (value as number | null | undefined) ?? null }),
  rotation_interval: (value) => ({ rotation_interval: rotationIntervalOf(value) }),
  click_action: (value) => ({ click_action: value === false ? 'none' : 'link' }),
  render_mode: (value) => ({ render_mode: (value as RenderMode | undefined) ?? 'default' }),
  default_z: (value) => ({ default_z: (value as number | undefined) ?? 1 }),
  hover_template: (value) => ({ hover_template: ((value as string) ?? '') || null }),
  context_template: (value) => ({ context_template: ((value as string) ?? '') || null })
}

/**
 * The map fields a metadata form's values describe.
 *
 * Only the fields the values actually carry: an untouched field is left out
 * entirely, which is what lets a bulk edit overwrite exactly what was ticked
 * and nothing else.
 */
export function metadataUpdatesFrom(values: Record<string, unknown>): Partial<MapConfig> {
  const updates: Partial<MapConfig> = {}
  for (const [field, read] of Object.entries(METADATA_READERS)) {
    if (field in values) {
      Object.assign(updates, read(values[field]))
    }
  }
  return updates
}
