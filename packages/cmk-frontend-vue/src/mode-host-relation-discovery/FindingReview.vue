<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import GroupQuestions from './GroupQuestions.vue'
import PagedRelations from './PagedRelations.vue'
import RelationDiscoveryTable from './RelationDiscoveryTable.vue'
import { LISTED_OUTCOMES, countedOutcomes } from './outcomes'
import type { FindingSummary, RelationGroup, RelationRow } from './types'

const { _t, _tn } = usei18n()

/**
 * How many questions a user is still asked to answer one by one. Beyond that, telling Checkmk
 * how to recognise the deciding end is less work than answering them.
 */
const QUESTIONS_BY_HAND = 20

const props = defineProps<{
  jobId: string
  summary: FindingSummary
  title: string
  /** What the host a question asks for is called: "Management board". */
  noun: string
  folders: string[]
  relationTitles: Record<string, string>
  relationNouns: Record<string, string>
  ticked: boolean
  excluded: ReadonlyMap<string, string>
  answers: ReadonlyMap<string, { host: string }>
}>()

const emit = defineEmits<{
  tick: [picked: boolean]
  toggle: [row: RelationRow, picked: boolean]
  toggleAll: [keys: string[], picked: boolean]
  answer: [group: RelationGroup, host: string | null]
  back: []
}>()

const showAll = ref(false)

const count = (outcome: string): number => props.summary.counts[outcome] ?? 0
const relations = computed(() => LISTED_OUTCOMES.reduce((sum, listed) => sum + count(listed), 0))
const questions = computed(() => props.summary.questions)
const storable = computed(() => count('link') > 0 || questions.value > 0)

/** Its relations by outcome, then what is not a relation of it: groups and conflicts. */
const counted = computed(() =>
  [
    countedOutcomes(props.summary.counts),
    ...(props.summary.settled_groups > 0
      ? [
          _tn(
            '1 group already related',
            '%{count} groups already related',
            props.summary.settled_groups,
            {
              count: props.summary.settled_groups
            }
          )
        ]
      : []),
    ...(questions.value > 0
      ? [
          _tn('1 question to answer', '%{count} questions to answer', questions.value, {
            count: questions.value
          })
        ]
      : []),
    ...(props.summary.conflicts > 0
      ? [
          _tn('1 in a conflict above', '%{count} in conflicts above', props.summary.conflicts, {
            count: props.summary.conflicts
          })
        ]
      : [])
  ]
    .filter((part) => part !== '')
    .join(' \u00b7 ')
)
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

    <template v-if="questions > 0 && props.ticked">
      <CmkParagraph>
        {{
          _tn(
            'For one group of hosts nothing says which one is the %{noun}. Pick it:',
            'For %{count} groups of hosts nothing says which one is the %{noun}. Pick it for each:',
            questions,
            { count: questions, noun: props.noun }
          )
        }}
      </CmkParagraph>
      <CmkAlertBox v-if="questions > QUESTIONS_BY_HAND" variant="info" size="small">
        {{
          _t(
            'Rather than answering %{count} questions, go back and say how to recognise the %{noun} - by a word in its name or a label only it carries.',
            { count: questions, noun: props.noun }
          )
        }}
        <CmkButton variant="optional" @click="emit('back')">{{
          _t('Back to the findings')
        }}</CmkButton>
      </CmkAlertBox>
      <GroupQuestions
        :job-id="props.jobId"
        :finding="props.summary.id"
        :relation-titles="props.relationTitles"
        :relation-nouns="props.relationNouns"
        :answers="props.answers"
        @answer="(group, host) => emit('answer', group, host)"
      />
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
