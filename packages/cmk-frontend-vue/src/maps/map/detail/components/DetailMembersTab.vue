<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a group is made of, one row per member, worst first.

A group is opened because something under it is wrong, so the counts double as
the filter: picking any problem count narrows the list to problems, picking OK
widens it again. Each row opens that member in this same drawer.
-->
<script setup lang="ts">
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { GroupMember } from '@/maps/types/api'
import { formatRelativeDuration } from '@/maps/utils/time'

import DetailChipGrid, { type DetailChip } from './DetailChipGrid.vue'

const props = defineProps<{
  members: GroupMember[]
  visibleMembers: GroupMember[]
  filteredCount: number
  truncatedCount: number
  loading: boolean
  chips: { label: string; count: number; tone: DetailChip['tone'] }[]
  search: string
  onlyProblems: boolean
  /** Ticks once a second so the "how long ago" column moves on its own. */
  nowMs: number
  stateTone: (state: string) => string
  stateBadge: (state: string) => string
}>()

const emit = defineEmits<{
  'update:search': [needle: string]
  'update:onlyProblems': [value: boolean]
  'select-member': [hostName: string, serviceDescription: string | null]
}>()

const { _t } = usei18n()

const memberChips = computed<DetailChip[]>(() =>
  props.chips.map((chip) => ({
    key: chip.label,
    label: chip.label,
    count: chip.count,
    tone: chip.tone
  }))
)

function formatAge(seconds: number | null | undefined): string {
  return formatRelativeDuration(seconds, props.nowMs)
}

function formatExact(seconds: number | null | undefined): string {
  return seconds ? new Date(seconds * 1000).toLocaleString() : ''
}
</script>

<template>
  <div class="maps-detail-members-tab">
    <DetailChipGrid
      v-if="members.length"
      interactive
      :chips="memberChips"
      @pick="emit('update:onlyProblems', $event.label !== 'OK')"
    />

    <div class="maps-detail-members-tab__controls">
      <CmkSearchInput
        :model-value="search"
        :placeholder="_t('Search members…')"
        class="maps-detail-members-tab__search"
        @update:model-value="emit('update:search', $event)"
      />
      <CmkCheckbox
        :model-value="onlyProblems"
        :label="_t('Only problems')"
        @update:model-value="emit('update:onlyProblems', $event)"
      />
    </div>

    <p v-if="loading" class="maps-detail-members-tab__empty">{{ _t('Loading…') }}</p>
    <p v-else-if="filteredCount === 0" class="maps-detail-members-tab__empty">
      {{ _t('No members match the current filter') }}
    </p>
    <ul v-else class="maps-detail-members-tab__list">
      <li
        v-for="member in visibleMembers"
        :key="`${member.host};${member.service}`"
        class="maps-detail-members-tab__item"
      >
        <button
          type="button"
          class="maps-detail-members-tab__row"
          :title="
            _t('Open %{name} in the drawer', {
              name: member.service ? `${member.host} / ${member.service}` : member.host
            })
          "
          @click="emit('select-member', member.host, member.service || null)"
        >
          <span
            class="maps-detail-members-tab__state"
            :class="`maps-detail-members-tab__state--${stateTone(member.state)}`"
            :title="member.state"
          >
            {{ stateBadge(member.state) }}
          </span>
          <div class="maps-detail-members-tab__body">
            <div class="maps-detail-members-tab__name">
              <span>{{ member.host }}</span>
              <span v-if="member.service" class="maps-detail-members-tab__service">{{
                member.service
              }}</span>
              <span
                v-if="member.acknowledged"
                class="maps-detail-members-tab__flag maps-detail-members-tab__flag--ack"
                >{{ _t('ACK') }}</span
              >
              <span
                v-if="member.in_downtime"
                class="maps-detail-members-tab__flag maps-detail-members-tab__flag--downtime"
                >{{ _t('DT') }}</span
              >
              <span
                v-if="member.notifications_enabled === false"
                class="maps-detail-members-tab__flag maps-detail-members-tab__flag--muted"
                >{{ _t('MUTED') }}</span
              >
            </div>
            <div
              v-if="member.output"
              class="maps-detail-members-tab__output"
              :title="member.output"
            >
              {{ member.output }}
            </div>
          </div>
          <span
            v-if="member.last_state_change"
            class="maps-detail-members-tab__since"
            :title="formatExact(member.last_state_change)"
          >
            {{ formatAge(member.last_state_change) }}
          </span>
        </button>
      </li>
    </ul>
    <p v-if="truncatedCount > 0" class="maps-detail-members-tab__truncated">
      {{ _t('+%{n} more — refine the filter to see them', { n: truncatedCount }) }}
    </p>
  </div>
</template>

<style scoped>
.maps-detail-members-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: 12px 16px;
}

.maps-detail-members-tab__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-detail-members-tab__search {
  flex: 1;
  min-width: 0;
}

.maps-detail-members-tab__empty {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  padding: var(--dimension-6);
  text-align: center;
  margin: 0;
}

.maps-detail-members-tab__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.maps-detail-members-tab__item {
  list-style: none;
}

.maps-detail-members-tab__row {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: var(--dimension-4);
  align-items: start;
  padding: 6px 8px;
  border-radius: var(--border-radius);
  background: var(--ux-theme-1);
  border: none;
  width: 100%;
  text-align: left;
  color: inherit;
  font: inherit;
  cursor: pointer;
  transition: background 100ms ease;
}

.maps-detail-members-tab__row:hover {
  background: var(--input-hover-bg-color);
}

.maps-detail-members-tab__row:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: -2px;
}

.maps-detail-members-tab__state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  color: var(--white);
}

.maps-detail-members-tab__state--ok {
  background: var(--color-state-ok);
}

.maps-detail-members-tab__state--warn {
  background: var(--color-state-warning);

  /* The warning colour is light enough that white text on it is unreadable. */
  color: var(--black);
}

.maps-detail-members-tab__state--crit {
  background: var(--color-state-critical);
}

.maps-detail-members-tab__state--unknown {
  background: var(--color-state-unknown);
}

.maps-detail-members-tab__state--pending {
  background: var(--font-color-dimmed);
}

.maps-detail-members-tab__body {
  min-width: 0;
}

.maps-detail-members-tab__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.maps-detail-members-tab__service {
  color: var(--font-color-dimmed);
  font-style: italic;
}

.maps-detail-members-tab__flag {
  font-size: 9px;
  font-weight: var(--font-weight-bold);
  padding: 1px 5px;
  border-radius: 3px;
  text-transform: uppercase;
}

/* The same two modifier colours the map view names, so a member row and a
   marker on the map agree on what "acknowledged" looks like. */
.maps-detail-members-tab__flag--ack {
  color: var(--maps-map-view-acknowledged);
  background: color-mix(in srgb, var(--maps-map-view-acknowledged) 20%, transparent);
}

.maps-detail-members-tab__flag--downtime {
  color: var(--maps-map-view-downtime);
  background: color-mix(in srgb, var(--maps-map-view-downtime) 20%, transparent);
}

.maps-detail-members-tab__flag--muted {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--font-color-dimmed) 30%, transparent);
}

.maps-detail-members-tab__output {
  color: var(--font-color-dimmed);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: var(--dimension-1);
}

.maps-detail-members-tab__since {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  white-space: nowrap;
  align-self: center;
  font-variant-numeric: tabular-nums;
}

.maps-detail-members-tab__truncated {
  color: var(--font-color-dimmed);
  font-size: 11px;
  text-align: center;
  margin: var(--dimension-4) 0 0;
  font-style: italic;
}
</style>
