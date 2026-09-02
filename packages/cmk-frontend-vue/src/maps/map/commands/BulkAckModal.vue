<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { onBeforeUnmount, onMounted, ref } from 'vue'

import type { AcknowledgeOptions } from '@/maps/api/commands'
import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { BulkAckTarget } from '@/maps/types/api'

import CommandFeedback from './CommandFeedback.vue'

const { commands } = useMapsApis()

const props = defineProps<{
  /** Aggregation that originated the bulk-ack — embedded in the comment
   * trailer so audit logs show "Bulk-ack: <agg> — <user comment>". */
  aggregationId: string
  targets: BulkAckTarget[]
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()
const comment = ref(`Bulk-ack: ${props.aggregationId}`)
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const submitting = ref(false)
const progress = ref(0)
const successCount = ref(0)
const error = ref<TranslatedString>(untranslated(''))
const commentEl = ref<HTMLInputElement | null>(null)
// True during the ~1.2s window between a fully successful run and auto-close, so
// a second click can't re-run the whole fan-out (a partial failure keeps the
// modal open with closing=false, leaving a retry possible).
const closing = ref(false)
let closeTimer: number | null = null
onBeforeUnmount(() => {
  if (closeTimer !== null) {
    window.clearTimeout(closeTimer)
  }
})

function options(): AcknowledgeOptions {
  return {
    comment: comment.value,
    sticky: sticky.value,
    notify: notify.value,
    persistent: persistent.value
  }
}

onMounted(() => commentEl.value?.focus())

async function submit() {
  if (!comment.value.trim() || submitting.value || closing.value) {
    return
  }
  submitting.value = true
  error.value = untranslated('')
  progress.value = 0
  successCount.value = 0
  const failures: string[] = []

  // Bounded parallelism: each leaf hits the same Checkmk site so we cap
  // concurrency to keep the GUI responsive without queueing up many
  // simultaneous COMMAND-pipe writes (livestatus serialises them
  // anyway). Five matches CMK's own bulk-action UI default.
  const CONCURRENCY = 5
  const queue = [...props.targets]
  const ackOne = async (tgt: BulkAckTarget): Promise<void> => {
    try {
      if (tgt.service) {
        await commands.acknowledgeService(tgt.host, tgt.service, options())
      } else {
        await commands.acknowledgeHost(tgt.host, options())
      }
      successCount.value += 1
    } catch (e) {
      failures.push(tgt.service ? `${tgt.host}/${tgt.service}` : tgt.host)
      console.warn('[Maps] bulk-ack failed for', tgt, e)
    } finally {
      progress.value += 1
    }
  }
  const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
    for (;;) {
      const next = queue.shift()
      if (!next) {
        return
      }
      await ackOne(next)
    }
  })
  await Promise.all(workers)
  submitting.value = false
  if (failures.length) {
    error.value = _t('%{failed} of %{total} failed: %{sample}', {
      failed: failures.length,
      total: props.targets.length,
      sample: failures.slice(0, 3).join(', ')
    })
  } else {
    closing.value = true
    closeTimer = window.setTimeout(() => emit('close'), 1200)
  }
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Acknowledge contributing leaves')"
    closable
    @close="$emit('close')"
  >
    <p class="maps-bulk-ack-modal__subtitle">
      {{
        _t('%{count} leaves from aggregation "%{aggregation}"', {
          aggregation: aggregationId,
          count: targets.length
        })
      }}
    </p>

    <ul class="maps-bulk-ack-modal__list">
      <li
        v-for="target in targets"
        :key="`${target.host};${target.service ?? ''}`"
        class="maps-bulk-ack-modal__item"
        :title="target.service ? `${target.host} / ${target.service}` : target.host"
      >
        {{ target.host
        }}<span v-if="target.service" class="maps-bulk-ack-modal__service">
          / {{ target.service }}</span
        >
      </li>
    </ul>

    <div class="maps-bulk-ack-modal__fields">
      <div>
        <label class="maps-bulk-ack-modal__label">{{ _t('Comment') }}</label>
        <CmkInput
          ref="commentEl"
          v-model="comment"
          field-size="fill"
          :placeholder="`${_t('Comment')}…`"
        />
      </div>
      <CmkCheckbox v-model="sticky" :label="_t('Sticky (stays until OK)')" />
      <CmkCheckbox v-model="notify" :label="_t('Send notification')" />
      <CmkCheckbox v-model="persistent" :label="_t('Persistent')" />
    </div>

    <CommandFeedback
      :error="error"
      :succeeded="successCount > 0"
      :succeeded-text="_t('%{count} leaves acknowledged', { count: successCount })"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        variant="primary"
        :disabled="submitting || closing || !comment.trim()"
        @click="submit"
      >
        {{
          submitting
            ? _t('Acknowledging %{current}/%{total}…', {
                current: progress,
                total: targets.length
              })
            : _t('Acknowledge %{count} leaves', { count: targets.length })
        }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-bulk-ack-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
}

.maps-bulk-ack-modal__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-normal);
}

.maps-bulk-ack-modal__item {
  padding: var(--dimension-3) var(--dimension-5);
  font-family: monospace;
  color: var(--font-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-bulk-ack-modal__list > .maps-bulk-ack-modal__item + .maps-bulk-ack-modal__item {
  border-top: 1px solid var(--default-border-color);
}

.maps-bulk-ack-modal__service {
  color: var(--font-color-dimmed);
}

.maps-bulk-ack-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-bulk-ack-modal__label {
  display: block;
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--font-color-dimmed);
  margin-bottom: var(--dimension-3);
}
</style>
