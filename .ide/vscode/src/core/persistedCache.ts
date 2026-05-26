/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type * as vscode from 'vscode'

/**
 * Thin typed wrapper around `context.workspaceState` used to keep
 * stale-while-revalidate snapshots warm across window reloads, so the first
 * paint after a window reload renders from yesterday's value instead of
 * waiting on a subprocess.
 */
let _context: vscode.ExtensionContext | null = null

export function bindPersistedCacheContext(context: vscode.ExtensionContext): void {
  _context = context
}

export function loadPersisted<T>(key: string): T | null {
  if (!_context) return null
  return _context.workspaceState.get<T>(key, null as unknown as T) ?? null
}

export function savePersisted<T>(key: string, value: T): void {
  if (!_context) return
  void _context.workspaceState.update(key, value)
}
