<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import PagedRelations from './PagedRelations.vue'
import RelationDiscoveryTable from './RelationDiscoveryTable.vue'
import { LISTED_OUTCOMES, countedOutcomes } from './outcomes'
import type { FindingSummary, RelationRow } from './types'

const { _t, _tn } = usei18n()

const props = defineProps<{
  jobId: string
  summary: FindingSummary
  title: string
  folders: string[]
  relationTitles: Record<string, string>
  ticked: boolean
  excluded: ReadonlyMap<string, string>
}>()

const emit = defineEmits<{
  tick: [picked: boolean]
  toggle: [row: RelationRow, picked: boolean]
  toggleAll: [keys: string[], picked: boolean]
}>()

const showAll = ref(false)

const count = (outcome: string): number => props.summary.counts[outcome] ?? 0
const relations = computed(() => LISTED_OUTCOMES.reduce((sum, listed) => sum + count(listed), 0))
const storable = computed(() => count('link') > 0)
const counted = computed(() => countedOutcomes(props.summary.counts))
</script>

<template>
  <section class="mode-host-relation-discovery-finding-review">
    <CmkCheckbox
      :model-value="props.ticked && storable"
      :disabled="!storable"
      @update:model-value="(picked: boolean) => emit('tick', picked)"
    >
      <template #label>
        <span class="mode-host-relation-discovery-finding-review__title">{{ props.title }}</span>
      </template>
    </CmkCheckbox>
    <CmkParagraph class="mode-host-relation-discovery-finding-review__counts">{{
      counted || _t('Nothing found.')
    }}</CmkParagraph>

    <template v-if="relations > 0">
      <PagedRelations
        v-if="showAll"
        :job-id="props.jobId"
        part="relations"
        :finding="props.summary.id"
        :folders="props.folders"
        :counts="props.summary.counts"
        :relation-titles="props.relationTitles"
        :selectable="props.ticked"
        :excluded="props.excluded"
        @toggle="(row, picked) => emit('toggle', row, picked)"
        @toggle-all="(keys, picked) => emit('toggleAll', keys, picked)"
      />
      <template v-else>
        <RelationDiscoveryTable
          :rows="props.summary.samples"
          :relation-titles="props.relationTitles"
          :done="false"
          :selectable="props.ticked"
          :excluded="props.excluded"
          @toggle="(row, picked) => emit('toggle', row, picked)"
        />
      </template>
      <div v-if="relations > props.summary.samples.length">
        <CmkButton variant="optional" @click="showAll = !showAll">
          {{
            showAll
              ? _t('Show examples only')
              : _tn('Show the relation', 'Show all %{count} relations', relations, {
                  count: relations
                })
          }}
        </CmkButton>
      </div>
    </template>
  </section>
</template>

<style scoped>
.mode-host-relation-discovery-finding-review {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border: 1px solid var(--ux-theme-4);
  border-radius: var(--border-radius);
}

.mode-host-relation-discovery-finding-review__title {
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-discovery-finding-review__counts {
  color: var(--font-color-dimmed);
}
</style>
