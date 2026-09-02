<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What people have already done about this object: the downtimes on it and the
comments on it.

Downtimes come first and carry the downtime colour -- they explain why nobody
has been notified, which is the question an operator has before they read
anybody's note.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ObjectDetails } from '@/maps/types/api'

import { commentRows, downtimeRows } from '../activityFacts'

const props = defineProps<{
  details: ObjectDetails | null
  /** Ticks once a second so the ageing labels move on their own. */
  nowMs: number
}>()

const { _t } = usei18n()

const downtimes = computed(() => downtimeRows(props.details))
const comments = computed(() => commentRows(props.details, props.nowMs, _t))
</script>

<template>
  <div class="maps-detail-activity-tab">
    <div v-if="downtimes.length">
      <div class="maps-detail-activity-tab__heading">{{ _t('Active downtimes') }}</div>
      <ul class="maps-detail-activity-tab__list">
        <li
          v-for="downtime in downtimes"
          :key="downtime.id"
          class="maps-detail-activity-tab__row maps-detail-activity-tab__row--downtime"
        >
          <div class="maps-detail-activity-tab__meta">
            <span class="maps-detail-activity-tab__author">{{ downtime.author }}</span>
            <span
              v-if="!downtime.fixed"
              class="maps-detail-activity-tab__tag"
              :title="_t('Flexible (triggered) downtime')"
              >{{ _t('FLEX') }}</span
            >
            <span class="maps-detail-activity-tab__time">{{ downtime.timeRange }}</span>
          </div>
          <div v-if="downtime.comment" class="maps-detail-activity-tab__text">
            {{ downtime.comment }}
          </div>
        </li>
      </ul>
    </div>

    <div v-if="comments.length">
      <div class="maps-detail-activity-tab__heading">{{ _t('Comments') }}</div>
      <ul class="maps-detail-activity-tab__list">
        <li v-for="comment in comments" :key="comment.id" class="maps-detail-activity-tab__row">
          <div class="maps-detail-activity-tab__meta">
            <span class="maps-detail-activity-tab__author">{{ comment.author }}</span>
            <span class="maps-detail-activity-tab__time">{{ comment.age }}</span>
            <span v-if="comment.expires" class="maps-detail-activity-tab__time">
              · {{ _t('expires') }} {{ comment.expires }}
            </span>
          </div>
          <div class="maps-detail-activity-tab__text">{{ comment.text }}</div>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.maps-detail-activity-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: 12px 16px;
}

.maps-detail-activity-tab__heading {
  font-size: var(--font-size-small);
  text-transform: uppercase;
  color: var(--font-color-dimmed);
  letter-spacing: 0.04em;
  font-weight: var(--font-weight-bold);
  margin: 4px 0 6px;
}

.maps-detail-activity-tab__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.maps-detail-activity-tab__row {
  background: var(--ux-theme-1);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  padding: 6px 8px;
  font-size: 11px;
}

.maps-detail-activity-tab__row--downtime {
  border-color: color-mix(in srgb, var(--maps-map-view-downtime) 35%, transparent);
  background: color-mix(in srgb, var(--maps-map-view-downtime) 6%, transparent);
}

.maps-detail-activity-tab__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  margin-bottom: var(--dimension-2);
  align-items: center;
}

.maps-detail-activity-tab__author {
  color: var(--font-color);
  font-weight: var(--font-weight-bold);
}

.maps-detail-activity-tab__tag {
  color: var(--maps-map-view-downtime);
  background: color-mix(in srgb, var(--maps-map-view-downtime) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--maps-map-view-downtime) 40%, transparent);
  border-radius: 999px;
  padding: 0 6px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.04em;
}

.maps-detail-activity-tab__text {
  color: var(--font-color);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
</style>
