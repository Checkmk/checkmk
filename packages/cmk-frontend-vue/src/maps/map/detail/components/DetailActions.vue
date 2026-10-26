<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What can be done about this object, from here.

Only what applies is offered: an acknowledged object has no "acknowledge", a
healthy one has no reason to be acknowledged at all, and a permission the
operator lacks is not shown as a disabled button. A group offers only what
Checkmk applies to a whole group in one call, and says how many it reaches.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { CommandVerb } from '@/maps/api/ticket'
import { OBJECT_ACTION_IDS as ACTIONS } from '@/maps/map/commands/useObjectActions'
import type { ObjectState } from '@/maps/types/api'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'

const props = defineProps<{
  state: ObjectState | undefined
  /** Whether the state is one an acknowledgement would apply to. */
  problematic: boolean
  /** Whether this object stands for several -- a group's members. */
  isGroup: boolean
  memberCount: number
  /** Which commands this operator may send for this object. */
  can: (verb: CommandVerb) => boolean
  /** Whether an action's command is still on its way. */
  running: (actionId: string) => boolean
  /** How the last command went, shown as in the host view. */
  feedback: ActionFeedbackResult | null
}>()

const feedbackOpen = defineModel<boolean>('feedbackOpen', { required: true })

const emit = defineEmits<{ select: [actionId: string] }>()

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
        v-if="!state?.acknowledged && problematic && can('acknowledge')"
        variant="success"
        class="maps-detail-actions__action maps-detail-actions__action--primary"
        :title="
          groupHint(
            _t('Acknowledge problems on all %{n} members of this group', { n: memberCount })
          )
        "
        :running="running(ACTIONS.acknowledge)"
        @click="emit('select', ACTIONS.acknowledge)"
      >
        {{ isGroup ? _t('Acknowledge (%{n})', { n: memberCount }) : _t('Acknowledge') }}
      </CmkButton>
      <CmkButton
        v-if="!isGroup && state?.acknowledged && can('remove_acknowledgement')"
        variant="warning"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.removeAcknowledgement)"
        @click="emit('select', ACTIONS.removeAcknowledgement)"
      >
        {{ _t('Remove ACK') }}
      </CmkButton>
      <CmkButton
        v-if="!isGroup && can('force_check')"
        variant="optional"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.forceCheck)"
        @click="emit('select', ACTIONS.forceCheck)"
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
        :running="running(ACTIONS.scheduleDowntime)"
        @click="emit('select', ACTIONS.scheduleDowntime)"
      >
        {{ isGroup ? _t('Downtime (%{n})', { n: memberCount }) : _t('Schedule downtime') }}
      </CmkButton>
      <CmkButton
        v-if="
          !isGroup && state?.in_downtime && can('schedule_downtime') && can('remove_all_downtimes')
        "
        variant="warning"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.removeDowntimes)"
        @click="emit('select', ACTIONS.removeDowntimes)"
      >
        {{ _t('Remove downtimes') }}
      </CmkButton>
      <CmkButton
        v-if="!isGroup && can('add_comment')"
        variant="optional"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.comment)"
        @click="emit('select', ACTIONS.comment)"
      >
        {{ _t('Add comment') }}
      </CmkButton>
      <CmkButton
        v-if="!isGroup && can('disable_notifications') && state?.notifications_enabled !== false"
        variant="optional"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.disableNotifications)"
        @click="emit('select', ACTIONS.disableNotifications)"
      >
        {{ _t('Disable notifications') }}
      </CmkButton>
      <CmkButton
        v-else-if="!isGroup && can('enable_notifications')"
        variant="optional"
        class="maps-detail-actions__action"
        :running="running(ACTIONS.enableNotifications)"
        @click="emit('select', ACTIONS.enableNotifications)"
      >
        {{ _t('Enable notifications') }}
      </CmkButton>
    </div>
    <ActionFeedback
      v-if="feedback"
      v-model:open="feedbackOpen"
      :class="{ 'maps-detail-actions__overlay': feedback.variant === 'success' }"
      :feedback="feedback"
    />
  </footer>
</template>

<style scoped>
.maps-detail-actions {
  position: relative;
  border-top: 1px solid var(--default-border-color);
  padding: var(--dimension-5) var(--dimension-6);
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  flex-shrink: 0;
  background: var(--ux-theme-3);
}

.maps-detail-actions__title {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  margin: 0;
  font-weight: var(--font-weight-medium);
}

.maps-detail-actions__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--dimension-4);
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

/* A success fades on its own, so it is laid over the details above rather than
   moving the buttons under a pointer about to click again. A failure stays until
   the next command, so it takes its own room below them instead of covering the
   details. */
.maps-detail-actions__overlay {
  position: absolute;
  right: var(--dimension-6);
  bottom: calc(100% + var(--dimension-4));
  left: var(--dimension-6);
}
</style>
