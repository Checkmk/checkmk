<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { outcomeColor, outcomeLabel } from './outcomes'
import type { RelationReason, RelationRow } from './types'

const { _t } = usei18n()

const props = defineProps<{
  rows: RelationRow[]
  /** How each relation reads in a row, by the name the wire uses for it. */
  relationTitles: Record<string, string>
  /** Whether these rows are what storing would do, or what a run has done. */
  done: boolean
  /** Whether a row that can be stored can be taken out of the run - never after it. */
  selectable: boolean
  /** The rows taken out, by key. */
  excluded: ReadonlyMap<string, string>
}>()

const emit = defineEmits<{
  toggle: [row: RelationRow, picked: boolean]
}>()

function relationTitle(relation: string): string {
  return props.relationTitles[relation] ?? relation
}

/** The short form of what found a row: the word, or the shared value as a label reads. */
function wordReason(reason: RelationReason): TranslatedString {
  return _t('"%{word}" in the name', { word: reason.word ?? '' })
}

function valueReason(reason: RelationReason): TranslatedString {
  return untranslated(`${reason.name ?? ''}:${reason.value ?? ''}`)
}
</script>

<template>
  <div class="mode-host-relation-discovery-relation-discovery-table">
    <table class="mode-host-relation-discovery-relation-discovery-table__table">
      <thead>
        <tr>
          <th v-if="props.selectable">
            <CmkVisuallyHidden :text="_t('Store')" />
          </th>
          <th>{{ _t('Host') }}</th>
          <th>{{ _t('Relation') }}</th>
          <th>{{ _t('Related host') }}</th>
          <th>{{ props.done ? _t('Result') : _t('Status') }}</th>
          <th>{{ _t('Why') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in props.rows" :key="row.key">
          <td v-if="props.selectable">
            <CmkCheckbox
              v-if="row.outcome === 'link'"
              :model-value="!props.excluded.has(row.key)"
              padding="both"
              :aria-label="`${row.source_host} ${relationTitle(row.relation)} ${row.target_host}`"
              @update:model-value="(picked: boolean) => emit('toggle', row, picked)"
            />
          </td>
          <td class="mode-host-relation-discovery-relation-discovery-table__host">
            {{ row.source_host }}
          </td>
          <td class="mode-host-relation-discovery-relation-discovery-table__relation">
            {{ relationTitle(row.relation) }}
          </td>
          <td class="mode-host-relation-discovery-relation-discovery-table__host">
            {{ row.target_host }}
          </td>
          <td class="mode-host-relation-discovery-relation-discovery-table__result">
            <span class="mode-host-relation-discovery-relation-discovery-table__badge">
              <CmkBadge size="small" :color="outcomeColor(row.outcome)">
                {{ outcomeLabel(row.outcome, props.done) }}
              </CmkBadge>
            </span>
            <span
              v-if="row.detail"
              class="mode-host-relation-discovery-relation-discovery-table__detail"
            >
              {{ row.detail }}
            </span>
          </td>
          <td
            class="mode-host-relation-discovery-relation-discovery-table__evidence"
            :title="row.evidence"
          >
            <span
              v-if="row.reason?.word"
              class="mode-host-relation-discovery-relation-discovery-table__reason"
              >{{ wordReason(row.reason) }}</span
            >
            <CmkTag
              v-else-if="row.reason?.value"
              class="mode-host-relation-discovery-relation-discovery-table__reason"
              :color="row.reason.source === 'label' ? 'label' : 'default'"
              variant="fill"
              size="small"
              :content="valueReason(row.reason)"
            />
            <template v-else>{{ row.evidence }}</template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
/* Scrolls sideways rather than running out of a narrow page: host names do not wrap. */
.mode-host-relation-discovery-relation-discovery-table {
  overflow-x: auto;
}

.mode-host-relation-discovery-relation-discovery-table__table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.mode-host-relation-discovery-relation-discovery-table th {
  padding: var(--spacing-half) var(--spacing);
  border-bottom: 1px solid var(--ux-theme-4);
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-discovery-relation-discovery-table td {
  padding: var(--spacing-half) var(--spacing);
  border-bottom: 1px solid var(--ux-theme-3);
  vertical-align: top;
}

/* A host name is the row's identity - broken over two lines it stops reading as one. */
.mode-host-relation-discovery-relation-discovery-table__host {
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.mode-host-relation-discovery-relation-discovery-table__reason,
.mode-host-relation-discovery-relation-discovery-table__relation,
.mode-host-relation-discovery-relation-discovery-table__result {
  white-space: nowrap;
}

/* What joins the two hosts into a sentence; the hosts are what the row is about. */
.mode-host-relation-discovery-relation-discovery-table__relation {
  color: var(--font-color-dimmed);
}

/* A badge is a state, not a button: it has to be as wide as its word, and a badge is a
   flex box that would otherwise take the whole cell. */
.mode-host-relation-discovery-relation-discovery-table__badge {
  display: inline-block;
}

.mode-host-relation-discovery-relation-discovery-table__evidence,
.mode-host-relation-discovery-relation-discovery-table__detail {
  color: var(--font-color-dimmed);
}

.mode-host-relation-discovery-relation-discovery-table__detail {
  margin-left: var(--spacing-half);
  white-space: normal;
}
</style>
