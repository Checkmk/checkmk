<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What can be done about this object, from here.

Only what applies is offered: an acknowledged object has no "acknowledge", a
healthy one has no reason to be acknowledged at all, and a permission the
operator lacks is not shown as a disabled button. On a group, every button
applies to all of its members -- so it says how many.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { CommandVerb } from '@/maps/api/ticket'
import type { ObjectState } from '@/maps/types/api'

const props = defineProps<{
  state: ObjectState | undefined
  /** Whether the state is one an acknowledgement would apply to. */
  problematic: boolean
  /** Whether this object stands for several -- a group's members. */
  isGroup: boolean
  memberCount: number
  /** Which commands this operator may send for this object. */
  can: (verb: CommandVerb) => boolean
}>()

const emit = defineEmits<{
  acknowledge: []
  'remove-ack': []
  'force-check': []
  'schedule-downtime': []
  'remove-downtime': []
  'add-comment': []
  'enable-notifications': []
  'disable-notifications': []
}>()

const { _t } = usei18n()

/** Spells out that a group command hits every member, and how many that is. */
function groupHint(one: string): string {
  return props.isGroup ? one : ''
}
</script>

<template>
  <footer class="maps-detail-actions">
    <h4 class="maps-detail-actions__title">{{ _t('Actions') }}</h4>
    <div class="maps-detail-actions__grid">
      <CmkButton
        v-if="!state?.acknowledged && (problematic || isGroup) && can('acknowledge')"
        variant="success"
        class="maps-detail-actions__action maps-detail-actions__action--primary"
        :title="
          groupHint(
            _t('Acknowledge problems on all %{n} members of this group', { n: memberCount })
          )
        "
        @click="emit('acknowledge')"
      >
        {{ isGroup ? _t('Acknowledge (%{n})', { n: memberCount }) : _t('Acknowledge') }}
      </CmkButton>
      <CmkButton
        v-if="state?.acknowledged && can('remove_acknowledgement')"
        variant="warning"
        class="maps-detail-actions__action"
        @click="emit('remove-ack')"
      >
        {{ _t('Remove ACK') }}
      </CmkButton>
      <CmkButton
        v-if="can('force_check')"
        variant="optional"
        class="maps-detail-actions__action"
        @click="emit('force-check')"
      >
        {{ _t('Force check') }}
      </CmkButton>
      <CmkButton
        v-if="!state?.in_downtime && can('schedule_downtime')"
        variant="optional"
        class="maps-detail-actions__action"
        :title="
          groupHint(_t('Schedule downtime on all %{n} members of this group', { n: memberCount }))
        "
        @click="emit('schedule-downtime')"
      >
        {{ isGroup ? _t('Downtime (%{n})', { n: memberCount }) : _t('Schedule downtime') }}
      </CmkButton>
      <CmkButton
        v-if="state?.in_downtime && can('schedule_downtime')"
        variant="warning"
        class="maps-detail-actions__action"
        @click="emit('remove-downtime')"
      >
        {{ _t('Remove downtime') }}
      </CmkButton>
      <CmkButton
        v-if="can('add_comment')"
        variant="optional"
        class="maps-detail-actions__action"
        @click="emit('add-comment')"
      >
        {{ _t('Add comment') }}
      </CmkButton>
      <CmkButton
        v-if="can('disable_notifications') && state?.notifications_enabled !== false"
        variant="optional"
        class="maps-detail-actions__action"
        @click="emit('disable-notifications')"
      >
        {{ _t('Disable notifications') }}
      </CmkButton>
      <CmkButton
        v-else-if="can('enable_notifications')"
        variant="optional"
        class="maps-detail-actions__action"
        @click="emit('enable-notifications')"
      >
        {{ _t('Enable notifications') }}
      </CmkButton>
    </div>
  </footer>
</template>

<style scoped>
.maps-detail-actions {
  border-top: 1px solid var(--default-border-color);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  flex-shrink: 0;
  background: var(--ux-theme-3);
}

.maps-detail-actions__title {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--font-color-dimmed);
  margin: 0;
  font-weight: var(--font-weight-bold);
}

.maps-detail-actions__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  align-items: stretch;
}

/* CmkButton is inline-flex; stretched across its grid cell so the actions line
   up, and given room to grow so a wrapped long label is not clipped. */
.maps-detail-actions__grid .maps-detail-actions__action {
  width: 100%;
  height: auto;
  min-height: var(--dimension-10);
  padding-top: var(--dimension-3);
  padding-bottom: var(--dimension-3);
  line-height: 1.25;
}

/* The one action the state is asking for gets the full width. */
.maps-detail-actions__action--primary {
  grid-column: span 2;
}
</style>
