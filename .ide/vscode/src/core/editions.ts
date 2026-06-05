/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

/** All Checkmk editions accepted by `--cmk_edition`. */
export const ALL_EDITIONS = ['community', 'pro', 'ultimate', 'ultimatemt', 'cloud'] as const
export type Edition = (typeof ALL_EDITIONS)[number]

/** The only edition buildable without the commercial `non-free/` source tree. */
export const FREE_EDITION: Edition = 'community'

/** Default edition on a full checkout (matches the `cmk.bazelTests.edition` schema default). */
const DEFAULT_EDITION: Edition = 'pro'

function workspacePath(wsPath?: string): string | undefined {
  return wsPath ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

/**
 * True when the checkout contains the commercial (`non-free/`) source tree.
 * Open-source clones (github.com/Checkmk/checkmk) don't ship it, so only the
 * community edition can be built there. `fs.existsSync` on a local path returns
 * in microseconds, so this is safe on the render/run path.
 */
export function isNonFreeAvailable(wsPath?: string): boolean {
  const root = workspacePath(wsPath)
  if (!root) return false
  return fs.existsSync(path.join(root, 'non-free'))
}

/** Editions selectable in this checkout — all of them, or just community. */
export function availableEditions(wsPath?: string): readonly Edition[] {
  return isNonFreeAvailable(wsPath) ? ALL_EDITIONS : [FREE_EDITION]
}

/**
 * The edition `--cmk_edition` should use. Reads `cmk.bazelTests.edition`, but
 * clamps to community on a community-only checkout so a stale `pro` setting (or
 * the `pro` default) never points Bazel at enterprise targets that aren't there.
 */
export function effectiveEdition(wsPath?: string): Edition {
  const available = availableEditions(wsPath)
  const stored = vscode.workspace.getConfiguration('cmk.bazelTests').get<string>('edition')
  if (stored && available.includes(stored as Edition)) return stored as Edition
  return available.includes(DEFAULT_EDITION) ? DEFAULT_EDITION : FREE_EDITION
}
