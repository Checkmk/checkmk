<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import RowPager from './RowPager.vue'
import type { RelationGroup } from './types'
import { candidates, partnersOf } from './types'
import usePagedRows from './usePagedRows'

const PAGE_SIZE = 20

const { _t, _tn } = usei18n()

const props = defineProps<{
  jobId: string
  finding: string
  relationTitles: Record<string, string>
  relationNouns: Record<string, string>
  /** The host named per group so far, by group key. */
  answers: ReadonlyMap<string, { host: string }>
}>()

const emit = defineEmits<{
  answer: [group: RelationGroup, host: string | null]
}>()

const { page, offset, failed } = usePagedRows(
  () => props.jobId,
  () => ({ part: 'groups', finding: props.finding, outcome: 'undecided' }),
  PAGE_SIZE
)

function options(group: RelationGroup): Suggestions {
  return {
    type: 'fixed',
    suggestions: candidates(group).map((member) => ({
      name: member,
      title: untranslated(member)
    }))
  }
}

function noun(group: RelationGroup): string {
  return props.relationNouns[group.relation] ?? ''
}
</script>

<template>
  <div class="mode-host-relation-discovery-group-questions">
    <CmkAlertBox v-if="failed" variant="error" size="small">
      {{ _t('The questions could not be read.') }}
    </CmkAlertBox>
    <ul v-else-if="page" class="mode-host-relation-discovery-group-questions__list">
      <li
        v-for="group in page.groups"
        :key="group.key"
        class="mode-host-relation-discovery-group-questions__group"
      >
        <span class="mode-host-relation-discovery-group-questions__tag">
          <CmkTag
            :color="group.reason.source === 'label' ? 'label' : 'default'"
            variant="fill"
            size="small"
            :content="untranslated(`${group.reason.name ?? ''}:${group.reason.value ?? ''}`)"
          />
        </span>
        <CmkDropdown
          :model-value="props.answers.get(group.key)?.host ?? null"
          :options="options(group)"
          :input-hint="_t('Pick the %{noun}', { noun: noun(group) })"
          :label="_t('Which of them is the %{noun}', { noun: noun(group) })"
          @update:model-value="(host: string | null) => emit('answer', group, host)"
        />
        <span class="mode-host-relation-discovery-group-questions__text">
          <!-- Until one of them is named, the group is the choice rather than the partners. -->
          <span class="mode-host-relation-discovery-group-questions__relation">{{
            props.answers.get(group.key)
              ? (props.relationTitles[group.relation] ?? '')
              : _t('one of')
          }}</span>
          {{ ' ' }}
          <template
            v-for="(member, index) in props.answers.get(group.key)
              ? partnersOf(group, props.answers.get(group.key)?.host ?? '')
              : group.members"
            :key="member"
          >
            <template v-if="index > 0">, </template>
            <span class="mode-host-relation-discovery-group-questions__member">{{ member }}</span>
          </template>
          <span
            v-if="Object.keys(group.refusals).length > 0"
            class="mode-host-relation-discovery-group-questions__detail"
          >
            {{
              _tn(
                '1 host of this group cannot be written and is left out.',
                '%{count} hosts of this group cannot be written and are left out.',
                Object.keys(group.refusals).length,
                { count: Object.keys(group.refusals).length }
              )
            }}
          </span>
        </span>
      </li>
    </ul>
    <RowPager v-if="page" v-model:offset="offset" :total="page.total" :page-size="PAGE_SIZE" />
  </div>
</template>

<style scoped>
.mode-host-relation-discovery-group-questions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

/* A grid rather than a row per group, so that the choices line up whatever the tags say. */
.mode-host-relation-discovery-group-questions__list {
  display: grid;
  grid-template-columns: max-content max-content 1fr;
  gap: var(--spacing-half) var(--spacing);
  align-items: center;
  margin: 0;
  padding: 0;
  list-style: none;
}

.mode-host-relation-discovery-group-questions__group {
  display: contents;
}

.mode-host-relation-discovery-group-questions__text {
  font-weight: var(--font-weight-bold);
}

.mode-host-relation-discovery-group-questions__relation,
.mode-host-relation-discovery-group-questions__detail {
  color: var(--font-color-dimmed);
  font-weight: var(--font-weight-default);
}

.mode-host-relation-discovery-group-questions__detail {
  margin-left: var(--spacing-half);
}

/* A chassis can have dozens of hosts: the list wraps, but only between two names. */
.mode-host-relation-discovery-group-questions__member,
.mode-host-relation-discovery-group-questions__tag {
  white-space: nowrap;
}
</style>
