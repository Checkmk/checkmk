<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBoxDeprecated from 'cmk-ui-library/components/CmkAlertBoxDeprecated.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown/CmkDropdown.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'
import type { Suggestions as DropdownOptions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import RelationDetectionTable from './RelationDetectionTable.vue'
import RowPager from './RowPager.vue'
import { type RowQuery, fetchRows } from './api'
import { LISTED_OUTCOMES, outcomeLabel } from './outcomes'
import type { Outcome, RelationRow } from './types'
import usePagedRows from './usePagedRows'

const { _t, _tn } = usei18n()

const PAGE_SIZE = 100

const props = defineProps<{
  jobId: string
  part: 'relations' | 'failed'
  /** Only the rows of this finding, if given. */
  finding?: string
  /** The folders to offer as a filter, by path. */
  folders: string[]
  /** How many rows of each outcome there are, to offer only the outcomes that have any. */
  counts?: Record<string, number>
  relationTitles: Record<string, string>
  selectable: boolean
  excluded: ReadonlyMap<string, string>
}>()

const emit = defineEmits<{
  toggle: [row: RelationRow, picked: boolean]
  /** Every relation the filter matches, on all pages, by key. */
  toggleAll: [keys: string[], picked: boolean]
}>()

/** The failed rows are what a run did; the others are what storing would do. */
const done = computed(() => props.part === 'failed')

const folderId = useId()

const search = ref('')
const submittedSearch = ref('')
const folder = ref('')
const outcome = ref<Outcome | 'all'>('all')

function query(): Omit<RowQuery, 'offset' | 'limit'> {
  return {
    part: props.part,
    ...(props.finding !== undefined ? { finding: props.finding } : {}),
    outcome: outcome.value === 'all' ? undefined : outcome.value,
    search: submittedSearch.value,
    folder: folder.value
  }
}

const { page, offset, loading, failed } = usePagedRows(() => props.jobId, query, PAGE_SIZE)

/** Whether the list is narrowed down - only then is "all of them" something else than the finding. */
const narrowed = computed(
  () => submittedSearch.value !== '' || folder.value !== '' || outcome.value !== 'all'
)
const collecting = ref(false)

/**
 * Take every matching relation out of the run, or put them back: a pattern found by searching
 * is a pattern of hundreds of rows, not one to untick row by row.
 */
async function toggleAll(picked: boolean): Promise<void> {
  collecting.value = true
  try {
    const found = await fetchRows(props.jobId, { ...query(), offset: 0, limit: 1, allKeys: true })
    emit('toggleAll', found.keys, picked)
  } finally {
    collecting.value = false
  }
}

const matching = computed(() =>
  page.value === null
    ? ''
    : _tn('1 relation matches', '%{count} relations match', page.value.total, {
        count: page.value.total
      })
)

const folderOptions = computed<DropdownOptions>(() => ({
  type: 'filtered',
  suggestions: [
    { name: '', title: _t('All folders') },
    ...props.folders
      .filter((path) => path !== '')
      .map((path) => ({ name: path, title: untranslated(path) }))
  ]
}))

const outcomeOptions = computed(() => [
  { label: _t('All'), value: 'all' },
  ...LISTED_OUTCOMES.filter(
    (listed) => props.counts === undefined || (props.counts[listed] ?? 0) > 0
  ).map((listed) => ({
    label: props.counts
      ? `${outcomeLabel(listed, done.value)} (${props.counts[listed]})`
      : outcomeLabel(listed, done.value),
    value: listed
  }))
])
</script>

<template>
  <div class="mode-host-relation-detection-paged-relations">
    <div class="mode-host-relation-detection-paged-relations__filters">
      <CmkSearchInput
        v-model="search"
        :placeholder="_t('Search host names')"
        :aria-label="_t('Search host names')"
        @search="(query: string) => (submittedSearch = query)"
      />
      <div
        v-if="props.folders.length > 1"
        class="mode-host-relation-detection-paged-relations__folder"
      >
        <CmkLabel :for="folderId">{{ _t('Folder') }}</CmkLabel>
        <CmkDropdown
          :component-id="folderId"
          :model-value="folder"
          :options="folderOptions"
          :label="_t('Folder')"
          @update:model-value="(picked) => (folder = picked ?? '')"
        />
      </div>
      <CmkToggleButtonGroup
        v-if="outcomeOptions.length > 2"
        v-model="outcome"
        :options="outcomeOptions"
      />
    </div>

    <div
      v-if="page !== null && narrowed"
      class="mode-host-relation-detection-paged-relations__matching"
    >
      <CmkParagraph>{{ matching }}</CmkParagraph>
      <template v-if="props.selectable && page.total > 0">
        <CmkButton variant="optional" :disabled="collecting" @click="toggleAll(false)">
          {{ _t('Untick all of them') }}
        </CmkButton>
        <CmkButton variant="optional" :disabled="collecting" @click="toggleAll(true)">
          {{ _t('Tick all of them') }}
        </CmkButton>
      </template>
    </div>

    <CmkAlertBoxDeprecated v-if="failed" variant="error" size="small">
      {{ _t('The rows could not be read.') }}
    </CmkAlertBoxDeprecated>
    <CmkSkeleton v-else-if="page === null" type="box" />
    <CmkParagraph
      v-else-if="page.total === 0"
      class="mode-host-relation-detection-paged-relations__empty"
    >
      {{ _t('No relation matches.') }}
    </CmkParagraph>
    <RelationDetectionTable
      v-else
      :class="{ 'mode-host-relation-detection-paged-relations__stale': loading }"
      :rows="page.relations"
      :relation-titles="props.relationTitles"
      :done="done"
      :selectable="props.selectable"
      :excluded="props.excluded"
      @toggle="(row, picked) => emit('toggle', row, picked)"
    />
    <RowPager v-if="page" v-model:offset="offset" :total="page.total" :page-size="PAGE_SIZE" />
  </div>
</template>

<style scoped>
.mode-host-relation-detection-paged-relations {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.mode-host-relation-detection-paged-relations__filters,
.mode-host-relation-detection-paged-relations__folder,
.mode-host-relation-detection-paged-relations__matching {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing);
}

.mode-host-relation-detection-paged-relations__empty {
  color: var(--font-color-dimmed);
}

/* The page being replaced stays in place rather than jumping to a skeleton and back. */
.mode-host-relation-detection-paged-relations__stale {
  opacity: 0.5;
}
</style>
