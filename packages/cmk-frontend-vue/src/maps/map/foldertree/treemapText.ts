/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a treemap tile says: its caption, its command-state markers and what a
 * screen reader hears -- each the most useful thing a few dozen pixels hold.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'

import type { FolderTreeNode } from '@/maps/types/api'
import { stateWordFromToken } from '@/maps/utils/objectAria'
import { severityPills } from '@/maps/utils/stateColors'

import { leafStateText } from './objects'
import type { Tile } from './treemapLayout'
import { isContainer, isEmptyFolder, isExpanded } from './treemapStyle'

type TranslateFn = ReturnType<typeof usei18n>['_t']
type PluralTranslateFn = ReturnType<typeof usei18n>['_tn']

interface TileTextOptions {
  _t: TranslateFn
  _tn: PluralTranslateFn
  /** A node the operator can drill into. */
  canExpand: (node: FolderTreeNode) => boolean
  serviceLoading: ReadonlySet<string>
  serviceError: ReadonlySet<string>
}

export interface TileText {
  /** The tile's own caption. */
  label: (tile: Tile) => string
  /** Command-state markers in the tile's corner. */
  mark: (node: FolderTreeNode) => string
  /** What a screen reader says about the tile. */
  aria: (tile: Tile) => string
}

/** Everything the tiles say, bound to the translator and the fetch state. */
export function tileText(options: TileTextOptions): TileText {
  const { _t, _tn, canExpand, serviceLoading, serviceError } = options
  const stateWord = (state: string): string => stateWordFromToken(_t, state)

  const breakdown = (node: FolderTreeNode): string => {
    const pills = severityPills(node.severity_counts)
    return pills.length
      ? pills.map((pill) => `${pill.count} ${stateWord(pill.state)}`).join(', ')
      : _t('all OK')
  }

  function folderLabel(node: FolderTreeNode): string {
    if (node.ok_group) {
      return node.title
    }
    const title = node.title
    if (node.is_empty) {
      return _t('%{title} · empty', { title })
    }
    const worst = severityPills(node.severity_counts)[0]
    return worst
      ? `${title} · ${worst.count} ${stateWord(worst.state)}`
      : `${title} · ${node.host_count}`
  }

  function label(tile: Tile): string {
    const node = tile.data
    if (isContainer(tile)) {
      const chevron = isExpanded(tile) ? '▾ ' : '▸ '
      return chevron + (node.kind === 'folder' ? folderLabel(node) : node.title)
    }
    if (node.kind === 'folder') {
      return folderLabel(node)
    }
    // A collapsed host that can drill into services: the chevron hints at that,
    // and an ellipsis says its services are on their way.
    if (node.kind === 'host' && canExpand(node)) {
      return `▸ ${node.title}${serviceLoading.has(node.title) ? ' …' : ''}`
    }
    return node.title
  }

  // Text rather than glyphs: a check mark in a tile corner reads as "OK". A
  // failed service fetch surfaces as "!" so the host does not just sit there.
  function mark(node: FolderTreeNode): string {
    const marks: string[] = []
    if (node.acknowledged) {
      marks.push(_t('ACK'))
    }
    if (node.in_downtime) {
      marks.push(_t('DT'))
    }
    if (node.is_flapping) {
      marks.push(_t('FLAP'))
    }
    if (node.kind === 'host' && serviceError.has(node.title)) {
      marks.push('!')
    }
    return marks.join(' ')
  }

  function aria(tile: Tile): string {
    const node = tile.data
    if (isEmptyFolder(node)) {
      return `${node.title}, ${_t('empty')}`
    }
    if (node.kind === 'folder') {
      const hosts = _tn('%{n} host', '%{n} hosts', node.host_count, { n: node.host_count })
      return `${node.title}, ${hosts}, ${breakdown(node)}`
    }
    return `${node.title}, ${leafStateText(_t, node)}`
  }

  return { label, mark, aria }
}
