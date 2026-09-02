<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Take an object out of monitoring for a while, because what is about to happen
to it is planned.

A group goes down in one call -- Checkmk's own bulk command. A BI aggregation
has no downtime of its own, so its real contributing hosts and services go down
instead, a few at a time so a wide aggregation does not arrive as a burst.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { DowntimeOptions } from '@/maps/api/commands'
import { useMapsApis, useStates } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { MapElement } from '@/maps/types/api'
import { flattenAggregationLeaves } from '@/maps/utils/aggregationTree'
import { objectDisplayName } from '@/maps/utils/dropdownOptions'

import CommandFeedback from './CommandFeedback.vue'
import { describeGroupCommandError, messageOf } from './commandErrors'
import { useCommandSubmit } from './useCommandSubmit'

/** How many of an aggregation's leaves are put into downtime at once. */
const LEAF_CONCURRENCY = 5

const { commands } = useMapsApis()
const statesStore = useStates()

const { _t } = usei18n()

const props = defineProps<{
  object: MapElement
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

function toLocalDatetimeString(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const now = new Date()
const startTime = ref(toLocalDatetimeString(now))
const endTime = ref(toLocalDatetimeString(new Date(now.getTime() + 3600_000)))
const comment = ref('')

const displayName = computed(() => objectDisplayName(props.object, _t))

const isGroup = computed(
  () => props.object.type === 'hostgroup' || props.object.type === 'servicegroup'
)
const isAggregation = computed(() => props.object.type === 'aggregation')
const groupTypeLabel = computed(() =>
  props.object.type === 'hostgroup' ? _t('host group') : _t('service group')
)

/** A downtime needs a window: both ends parseable, and the end after the start. */
const timesValid = computed(() => {
  const start = Date.parse(startTime.value)
  const end = Date.parse(endTime.value)
  return Number.isFinite(start) && Number.isFinite(end) && end > start
})

interface DowntimeTarget {
  host: string
  service: string | null
}

/** The real hosts and services below an aggregation -- what downtime applies to. */
function aggregationTargets(): DowntimeTarget[] {
  const tree = statesStore.getState(props.object.id)?.tree
  if (!tree) {
    return []
  }
  return flattenAggregationLeaves(tree)
    .filter((leaf) => !!leaf.host_name)
    .map((leaf) => ({
      host: leaf.host_name as string,
      service: leaf.service_description ?? null
    }))
}

/**
 * Puts every leaf into downtime, a few at a time. One leaf failing does not
 * abort the rest -- the operator wants the window on as much of the
 * aggregation as can take it -- but the count of failures is reported.
 */
async function downtimeAggregationLeaves(options: DowntimeOptions): Promise<void> {
  const targets = aggregationTargets()
  if (!targets.length) {
    throw new Error(_t('This aggregation has no hosts or services to put into downtime.'))
  }
  const queue = [...targets]
  const failed: string[] = []
  const worker = async (): Promise<void> => {
    for (let target = queue.shift(); target; target = queue.shift()) {
      try {
        if (target.service) {
          await commands.downtimeService(target.host, target.service, options)
        } else {
          await commands.downtimeHost(target.host, options)
        }
      } catch (caught) {
        failed.push(target.service ? `${target.host}/${target.service}` : target.host)
        console.warn('[Maps] bulk-downtime failed for', target, caught)
      }
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(LEAF_CONCURRENCY, queue.length) }, () => worker())
  )
  if (failed.length) {
    throw new Error(
      _t('%{failed}/%{total} failed to schedule downtime', {
        failed: failed.length,
        total: targets.length
      })
    )
  }
}

const { submitting, succeeded, error, blocked, submit, reject } = useCommandSubmit({
  fallbackError: _t('Failed to schedule downtime'),
  describeError: (caught) =>
    describeGroupCommandError(
      messageOf(caught, _t('Failed to schedule downtime')),
      isGroup.value,
      groupTypeLabel.value,
      _t
    ),
  onDone: () => emit('close'),
  send: async () => {
    const start = new Date(Date.parse(startTime.value)).toISOString()
    const end = new Date(Date.parse(endTime.value)).toISOString()
    const options: DowntimeOptions = { startTime: start, endTime: end, comment: comment.value }
    if (isAggregation.value) {
      await downtimeAggregationLeaves(options)
      return
    }
    if (props.object.type === 'hostgroup' && props.object.group_name) {
      await commands.downtimeHostgroup(props.checkmkUrl, props.object.group_name, options)
      return
    }
    if (props.object.type === 'servicegroup' && props.object.group_name) {
      await commands.downtimeServicegroup(props.checkmkUrl, props.object.group_name, options)
      return
    }
    if (
      props.object.type === 'service' &&
      props.object.host_name &&
      props.object.service_description
    ) {
      await commands.downtimeService(
        props.object.host_name,
        props.object.service_description,
        options
      )
      return
    }
    if (props.object.host_name) {
      await commands.downtimeHost(props.object.host_name, options)
    }
  }
})

function onSubmit(): void {
  if (!comment.value.trim()) {
    return
  }
  if (!timesValid.value) {
    reject(_t('Please provide a start and an end time, with the end after the start.'))
    return
  }
  void submit()
}
</script>

<template>
  <MapsModal :open="true" :title="_t('Schedule downtime')" closable @close="emit('close')">
    <p class="maps-downtime-modal__subtitle">{{ displayName }}</p>
    <p
      v-if="isGroup"
      class="maps-downtime-modal__group-hint"
      :title="
        _t(
          'Checkmk fans this command out across all members; partial failures abort the operation.'
        )
      "
    >
      {{ _t('Applies to every member of the %{type}', { type: groupTypeLabel }) }}
    </p>

    <div class="maps-downtime-modal__fields">
      <div>
        <label class="maps-downtime-modal__label">{{ _t('Start') }}</label>
        <input v-model="startTime" type="datetime-local" class="maps-downtime-modal__input" />
      </div>
      <div>
        <label class="maps-downtime-modal__label">{{ _t('End') }}</label>
        <input v-model="endTime" type="datetime-local" class="maps-downtime-modal__input" />
      </div>
      <div class="maps-downtime-modal__cmk-field">
        <CmkLabel>{{ _t('Comment') }}</CmkLabel>
        <CmkInput v-model="comment" field-size="fill" :placeholder="`${_t('Comment')}…`" />
      </div>
    </div>

    <CommandFeedback
      :error="error"
      :succeeded="succeeded"
      :succeeded-text="_t('Downtime scheduled')"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        variant="primary"
        :disabled="blocked || !comment.trim() || !timesValid"
        @click="onSubmit"
      >
        {{ submitting ? _t('Scheduling…') : _t('Schedule downtime') }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-downtime-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

/* A bulk command deserves a word of warning before it is sent. */
.maps-downtime-modal__group-hint {
  font-size: var(--font-size-normal);
  color: var(--color-yellow-50);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

.maps-downtime-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-downtime-modal__cmk-field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.maps-downtime-modal__label {
  display: block;
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-3);
}

/* A native datetime input, styled to sit with the form controls around it --
   the design system has no date/time field yet. */
.maps-downtime-modal__input {
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-large);
  color: var(--font-color);
}

.maps-downtime-modal__input:focus {
  outline: none;
  border-color: var(--color-corporate-green-50);
  box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}
</style>
