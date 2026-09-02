/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { resolveAssetBase } from '@/maps/utils/deploymentBase'

// Build a URL for a statically-served Maps asset (uploaded image, map
// background). These files are owned by the GUI (cmk.maps.gui._images) and
// served directly by Apache under the site. The prefix is exempt from the
// site's auth realm, so these URLs are readable without a session: icons are a
// shared library, and a background's filename carries an unguessable token.
export function assetUrl(relPath: string): string {
  return `${resolveAssetBase()}${relPath}`
}
