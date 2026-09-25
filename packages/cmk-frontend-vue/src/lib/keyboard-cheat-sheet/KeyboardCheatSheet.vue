<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Keyboard cheat sheet (CMK-38372): what the keyboard does on the current page, shown while
Alt+K is held or while pinned (see cheatSheetKey.ts), together with the key hints on the
page. Pinned, a row under the pointer highlights its key hint and vice versa. Only the pin
takes input; the list is hidden from assistive technology, which has the controls' own labels.
-->
<script setup lang="ts">
import CmkKeyboardKey from 'cmk-ui-library/components/CmkKeyboardKey.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import {
  type KeyboardHelpEntry,
  type KeyboardHelpKind,
  comboLabels,
  getKeyboardHelp,
  highlightCombo,
  highlightedCombo,
  subscribeKeyboardHelp
} from 'cmk-ui-library/lib/keyboardHelp'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { toggleCheatSheetPin, useCheatSheetPinned, useCheatSheetVisible } from './cheatSheetKey'

const props = defineProps<{
  kinds: readonly KeyboardHelpKind[]
}>()

const { _t } = usei18n()

interface ComboParts {
  modifiers: string[]
  key: string
}

interface Row {
  kind: KeyboardHelpKind
  description: string | undefined
  parts: ComboParts[]
  /** The raw combinations, for the highlight. */
  combos: string[][]
}

interface HintPart {
  key: string | undefined
  text: string
}

interface Group {
  scope: string
  rows: Row[]
  hints: HintPart[][]
}

const GLYPH_LABELS = new Set(['arrow-up', 'arrow-down', 'arrow-left', 'arrow-right'])
/** One symbol, but the box of a worded key. */
const WORDED_GLYPH_LABELS = new Set(['enter', 'backspace'])

const CAP = 'lib-keyboard-cheat-sheet__cap'

function capClass(label: string): string {
  if (GLYPH_LABELS.has(label) || [...label].length === 1) {
    return `${CAP} ${CAP}--glyph`
  }
  return WORDED_GLYPH_LABELS.has(label) ? `${CAP} ${CAP}--wide` : CAP
}

/** Characters per line, for a rough height in lines to pack the columns by. */
const ROW_CHARS = 30
const HINT_CHARS = 55
const COLUMN_COUNT = 3

function textLines(text: string, perLine: number): number {
  return Math.max(1, Math.ceil(text.length / perLine))
}

function groupLines(group: Group): number {
  const rows = group.rows.reduce(
    (lines, row) => lines + Math.max(row.parts.length, textLines(row.description ?? '', ROW_CHARS)),
    0
  )
  const hints = group.hints.reduce(
    (lines, hint) => lines + textLines(hint.map((part) => part.text || '[]').join(''), HINT_CHARS),
    0
  )
  return rows + hints + 2 // heading and gap
}

/** Always at the top of the first column. */
const firstScope = _t('Main menu')

const visible = useCheatSheetVisible()
const pinned = useCheatSheetPinned()
const entries = ref<KeyboardHelpEntry[]>([])

function refresh(): void {
  if (visible.value) {
    entries.value = getKeyboardHelp()
  }
}

/** `Press [/] to search` -> text, key cap, text. */
function hintParts(hint: string): HintPart[] {
  return hint
    .split(/\[([^\]]+)\]/)
    .map(
      (part, index): HintPart =>
        index % 2 === 1 ? { key: comboLabels([part])[0], text: '' } : { key: undefined, text: part }
    )
    .filter((part) => part.key !== undefined || part.text !== '')
}

const groups = computed<Group[]>(() => {
  const wanted = new Set(props.kinds)
  const byScope = new Map<string, Group>()
  const rowsByKey = new Map<string, Row>()
  const hintsSeen = new Set<string>()
  for (const entry of entries.value) {
    if (!wanted.has(entry.kind)) {
      continue
    }
    let group = byScope.get(entry.scope)
    if (!group) {
      group = { scope: entry.scope, rows: [], hints: [] }
      byScope.set(entry.scope, group)
    }
    if (entry.kind === 'hint') {
      const hintKey = `${entry.scope}\n${entry.description ?? ''}`
      if (entry.description && !hintsSeen.has(hintKey)) {
        hintsSeen.add(hintKey)
        group.hints.push(hintParts(entry.description))
      }
      continue
    }
    const labels = comboLabels(entry.combo)
    // Same text shares a row; undocumented entries stay apart.
    const rowKey = [entry.scope, entry.kind, entry.description ?? `\0${labels.join('+')}`].join(
      '\n'
    )
    let row = rowsByKey.get(rowKey)
    if (!row) {
      row = { kind: entry.kind, description: entry.description, parts: [], combos: [] }
      rowsByKey.set(rowKey, row)
      group.rows.push(row)
    }
    const combo = { modifiers: labels.slice(0, -1), key: labels[labels.length - 1] ?? '' }
    if (!row.parts.some((part) => [...part.modifiers, part.key].join('+') === labels.join('+'))) {
      row.parts.push(combo)
      row.combos.push(entry.combo)
    }
  }
  for (const group of byScope.values()) {
    group.rows.sort((a, b) => Number(a.kind === 'widget') - Number(b.kind === 'widget'))
  }
  return [...byScope.values()]
})

/** Tallest group first into the shortest column; CSS multi-columns split groups or balance badly. */
const columns = computed<Group[][]>(() => {
  type Column = { groups: Group[]; lines: number }
  const first: Column = { groups: [], lines: 0 }
  const packed: Column[] = [first]
  while (packed.length < COLUMN_COUNT) {
    packed.push({ groups: [], lines: 0 })
  }
  const place = (column: Column, group: Group): void => {
    column.groups.push(group)
    column.lines += groupLines(group)
  }
  const tallestFirst = [...groups.value].sort((a, b) => groupLines(b) - groupLines(a))
  for (const group of tallestFirst.filter((group) => group.scope === firstScope)) {
    place(first, group)
  }
  for (const group of tallestFirst.filter((group) => group.scope !== firstScope)) {
    place(
      packed.reduce((a, b) => (b.lines < a.lines ? b : a)),
      group
    )
  }
  return packed.map((column) => column.groups).filter((column) => column.length > 0)
})

function isHighlighted(row: Row): boolean {
  return row.parts.some(
    (part) => [...part.modifiers, part.key].join('+') === highlightedCombo.value
  )
}

function onRowEnter(row: Row): void {
  if (pinned.value) {
    highlightCombo(row.combos[0] ?? null)
  }
}

let unsubscribe: (() => void) | null = null

watch(visible, (shown) => {
  if (shown) {
    refresh()
  }
})

onMounted(() => {
  unsubscribe = subscribeKeyboardHelp(refresh)
  refresh()
})

onBeforeUnmount(() => {
  unsubscribe?.()
})
</script>

<template>
  <div
    class="lib-keyboard-cheat-sheet"
    :class="{
      'lib-keyboard-cheat-sheet--visible': visible,
      'lib-keyboard-cheat-sheet--pinned': pinned
    }"
  >
    <div class="lib-keyboard-cheat-sheet__header">
      <button
        type="button"
        class="lib-keyboard-cheat-sheet__pin"
        :class="{ 'lib-keyboard-cheat-sheet__pin--pinned': pinned }"
        :aria-pressed="pinned"
        :aria-label="pinned ? _t('Unpin the cheat sheet') : _t('Pin the cheat sheet')"
        :title="pinned ? _t('Unpin the cheat sheet') : _t('Pin the cheat sheet')"
        @click="toggleCheatSheetPin()"
      >
        <svg class="lib-keyboard-cheat-sheet__pin-icon" viewBox="0 0 16 16" aria-hidden="true">
          <circle cx="8" cy="5" r="3.4" />
          <path d="M7.3 8.3h1.4L8 14.5z" />
        </svg>
      </button>
      <span class="lib-keyboard-cheat-sheet__title">{{
        _t('Keyboard navigation cheat sheet')
      }}</span>
      <span class="lib-keyboard-cheat-sheet__usage">
        {{
          _t('Hold Alt+K to show with the key hints, press K twice to pin, Esc or Alt+K to hide')
        }}
      </span>
    </div>
    <div class="lib-keyboard-cheat-sheet__body" aria-hidden="true">
      <div
        v-for="(column, columnIndex) in columns"
        :key="columnIndex"
        class="lib-keyboard-cheat-sheet__column"
      >
        <section v-for="group in column" :key="group.scope" class="lib-keyboard-cheat-sheet__group">
          <h3 class="lib-keyboard-cheat-sheet__scope">{{ group.scope }}</h3>
          <div
            v-for="(row, rowIndex) in group.rows"
            :key="rowIndex"
            class="lib-keyboard-cheat-sheet__row"
            :class="{
              'lib-keyboard-cheat-sheet__row--widget': row.kind === 'widget',
              'lib-keyboard-cheat-sheet__row--undocumented': row.description === undefined,
              'lib-keyboard-cheat-sheet__row--highlighted': isHighlighted(row)
            }"
            @mouseenter="onRowEnter(row)"
            @mouseleave="highlightCombo(null)"
          >
            <span class="lib-keyboard-cheat-sheet__modifiers">
              <span
                v-for="(part, partIndex) in row.parts"
                :key="partIndex"
                class="lib-keyboard-cheat-sheet__cap-line"
              >
                <template v-for="(modifier, modifierIndex) in part.modifiers" :key="modifierIndex">
                  <span v-if="modifierIndex > 0" class="lib-keyboard-cheat-sheet__separator"
                    >+</span
                  >
                  <CmkKeyboardKey
                    :keyboard-key="modifier"
                    size="large"
                    :class="capClass(modifier)"
                  />
                </template>
              </span>
            </span>
            <span class="lib-keyboard-cheat-sheet__plus">
              <span
                v-for="(part, partIndex) in row.parts"
                :key="partIndex"
                class="lib-keyboard-cheat-sheet__cap-line"
              >
                <template v-if="part.modifiers.length > 0">+</template>
              </span>
            </span>
            <span class="lib-keyboard-cheat-sheet__keys">
              <span
                v-for="(part, partIndex) in row.parts"
                :key="partIndex"
                class="lib-keyboard-cheat-sheet__cap-line"
              >
                <CmkKeyboardKey :keyboard-key="part.key" size="large" :class="capClass(part.key)" />
              </span>
            </span>
            <span class="lib-keyboard-cheat-sheet__description">
              {{ row.description ?? _t('undocumented') }}
            </span>
          </div>
          <p
            v-for="(hint, hintIndex) in group.hints"
            :key="hintIndex"
            class="lib-keyboard-cheat-sheet__hint"
          >
            <template v-for="(part, partIndex) in hint" :key="partIndex">
              <CmkKeyboardKey
                v-if="part.key !== undefined"
                :keyboard-key="part.key"
                size="large"
                :class="capClass(part.key)"
              />
              <template v-else>{{ part.text }}</template>
            </template>
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Parchment on purpose: the same in both themes. */
.lib-keyboard-cheat-sheet {
  --cheat-sheet-paper: #f7f1e1;
  --cheat-sheet-ink: #4b3621;
  --cheat-sheet-ink-soft: rgb(75 54 33 / 70%);
  --cheat-sheet-ink-faint: rgb(75 54 33 / 45%);
  --cheat-sheet-highlight: rgb(75 54 33 / 15%);
  --cheat-sheet-font: 16px;
  --cheat-sheet-line: 24px;
  --cheat-sheet-cap: 22px;

  /* Relative to this sheet's own font, not the page's. */
  --cheat-sheet-column: 30em;

  /* The box of a three-letter cap like Esc. */
  --cheat-sheet-cap-wide: calc(3ch + 2 * var(--dimension-3) + 2px);

  position: fixed;
  inset: auto var(--dimension-10) var(--dimension-10);
  z-index: var(--z-index-modal-popup);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  max-height: calc(100vh - 2 * var(--dimension-10));
  padding: var(--cheat-sheet-line) var(--dimension-6);
  overflow: hidden;
  font-family: monospace;
  font-size: var(--cheat-sheet-font);
  line-height: var(--cheat-sheet-line);
  color: var(--cheat-sheet-ink);
  pointer-events: none;
  background: var(--cheat-sheet-paper);
  border-radius: 18px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 35%);
  visibility: hidden;
  opacity: 0;
  transition:
    opacity 400ms ease-out,
    visibility 400ms ease-out;
}

.lib-keyboard-cheat-sheet--visible {
  visibility: visible;
  opacity: 1;
}

.lib-keyboard-cheat-sheet__header {
  position: relative;
  display: flex;
  flex: 0 0 auto;
  gap: var(--dimension-6);
  align-items: baseline;
  justify-content: center;
  height: var(--cheat-sheet-line);
  margin-bottom: var(--cheat-sheet-line);
}

.lib-keyboard-cheat-sheet__title {
  font-weight: var(--font-weight-bold);
}

.lib-keyboard-cheat-sheet__pin {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--cheat-sheet-line);
  height: var(--cheat-sheet-line);
  padding: 0;
  color: var(--cheat-sheet-ink-soft);
  pointer-events: auto;
  cursor: pointer;
  background: none;
  border: 0;
}

.lib-keyboard-cheat-sheet__pin:hover,
.lib-keyboard-cheat-sheet__pin--pinned {
  color: var(--cheat-sheet-ink);
}

.lib-keyboard-cheat-sheet__pin-icon {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentcolor;
  stroke-width: 1.4px;
  transform: rotate(-35deg);
}

.lib-keyboard-cheat-sheet__pin--pinned .lib-keyboard-cheat-sheet__pin-icon {
  fill: currentcolor;
  stroke: none;
  transform: none;
}

.lib-keyboard-cheat-sheet__usage {
  font-style: italic;
  color: var(--cheat-sheet-ink-soft);
}

.lib-keyboard-cheat-sheet__body {
  display: flex;
  gap: var(--dimension-8);
  align-items: flex-start;
  justify-content: center;
  overflow: hidden;
}

.lib-keyboard-cheat-sheet__column {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  gap: var(--cheat-sheet-line);
  min-width: 0;
  max-width: var(--cheat-sheet-column);
}

/* Modifiers, `+`, key, text: one grid per group so its rows line up. */
.lib-keyboard-cheat-sheet__group {
  display: grid;
  grid-template-columns: auto auto auto minmax(0, 1fr);
  gap: var(--dimension-3) var(--dimension-2);
  align-items: center;
}

.lib-keyboard-cheat-sheet__scope {
  grid-column: 1 / -1;
  margin: 0;
  font-size: var(--cheat-sheet-font);
  font-weight: var(--font-weight-bold);
  color: var(--cheat-sheet-ink-soft);
}

.lib-keyboard-cheat-sheet__row {
  display: contents;
}

.lib-keyboard-cheat-sheet__modifiers,
.lib-keyboard-cheat-sheet__plus,
.lib-keyboard-cheat-sheet__keys {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.lib-keyboard-cheat-sheet__modifiers {
  justify-self: end;
}

.lib-keyboard-cheat-sheet__keys {
  justify-self: start;
}

.lib-keyboard-cheat-sheet__cap-line {
  display: flex;
  gap: var(--dimension-2);
  align-items: center;
  justify-content: center;
  min-height: var(--cheat-sheet-cap);
}

.lib-keyboard-cheat-sheet__modifiers .lib-keyboard-cheat-sheet__cap-line {
  justify-content: flex-end;
}

.lib-keyboard-cheat-sheet__keys .lib-keyboard-cheat-sheet__cap-line {
  justify-content: flex-start;
}

.lib-keyboard-cheat-sheet__description {
  padding-left: var(--dimension-4);
}

/* The row itself has no box: its cells take the highlight and the pointer. */
.lib-keyboard-cheat-sheet__row--highlighted > * {
  background: var(--cheat-sheet-highlight);
  border-radius: 4px;
}

.lib-keyboard-cheat-sheet--pinned .lib-keyboard-cheat-sheet__row > * {
  pointer-events: auto;
}

.lib-keyboard-cheat-sheet__row--widget {
  color: var(--cheat-sheet-ink-soft);
}

.lib-keyboard-cheat-sheet__row--undocumented .lib-keyboard-cheat-sheet__description {
  font-style: italic;
  color: var(--cheat-sheet-ink-faint);
}

.lib-keyboard-cheat-sheet__hint {
  grid-column: 1 / -1;
  margin: 0;
  font-style: italic;
  color: var(--cheat-sheet-ink-soft);
}

/* Doubled class: beats the component's own scoped rules. */
.lib-keyboard-cheat-sheet__cap.lib-keyboard-cheat-sheet__cap {
  top: 0;
  box-sizing: border-box;
  align-items: center;
  justify-content: center;
  height: var(--cheat-sheet-cap);
  padding: 0 var(--dimension-3);
  margin: 0;
  font-size: 13px;
  line-height: 1;
  color: var(--cheat-sheet-paper);
  background: var(--cheat-sheet-ink);
  border-color: var(--cheat-sheet-ink);
}

.lib-keyboard-cheat-sheet__row--widget
  .lib-keyboard-cheat-sheet__cap.lib-keyboard-cheat-sheet__cap {
  background: var(--cheat-sheet-ink-soft);
  border-color: var(--cheat-sheet-ink-soft);
}

.lib-keyboard-cheat-sheet__cap--glyph.lib-keyboard-cheat-sheet__cap--glyph {
  width: var(--cheat-sheet-cap);
  min-width: var(--cheat-sheet-cap);
  padding: 0;
  font-size: 15px;
}

.lib-keyboard-cheat-sheet__cap--wide.lib-keyboard-cheat-sheet__cap--wide {
  width: var(--cheat-sheet-cap-wide);
  min-width: var(--cheat-sheet-cap-wide);
  padding: 0;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.lib-keyboard-cheat-sheet__cap.lib-keyboard-cheat-sheet__cap :deep(span) {
  top: 0;
  margin: 0;
}
</style>
