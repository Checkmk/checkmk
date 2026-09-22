<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Acknowledge several problems at once: the contributing leaves of a BI
aggregation, or the nodes an operator picked on a flow map.

Neither is a Checkmk host or service group, so there is no single command for
them and each is acknowledged in turn. What they were picked from goes into the
comment, so the audit log traces every entry back to where it was asked for.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { onMounted, ref } from 'vue'

import type { AcknowledgeOptions } from '@/maps/api/commands'
import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget } from '@/maps/types/api'

import CommandFeedback from './CommandFeedback.vue'
import CommandTargetList from './CommandTargetList.vue'
import { useBulkCommandSubmit } from './useBulkCommandSubmit'

const { commands } = useMapsApis()

const props = defineProps<{
  /**
   * What the operator picked these from — an aggregation, a map. It rides along
   * in the comment, so the audit log says where the acknowledgement came from.
   */
  origin: string
  targets: CommandTarget[]
  /** How many were picked but have no problem to acknowledge, and are left out. */
  skipped?: number
}>()

// Whether the operator's selection was actually commanded: the caller keeps it
// intact when it was not, so a cancelled dialog does not cost them the picking.
const emit = defineEmits<{ close: [sent: boolean] }>()

const { _t } = usei18n()
const comment = ref(`Bulk-ack: ${props.origin}`)
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const commentEl = ref<HTMLInputElement | null>(null)

function options(): AcknowledgeOptions {
  return {
    comment: comment.value,
    sticky: sticky.value,
    notify: notify.value,
    persistent: persistent.value
  }
}

onMounted(() => commentEl.value?.focus())

const { submitting, progress, succeeded, pending, error, blocked, submit } = useBulkCommandSubmit({
  what: 'bulk-ack',
  targets: () => props.targets,
  onDone: () => emit('close', true),
  send: (target) =>
    target.service
      ? commands.acknowledgeService(target.host, target.service, options())
      : commands.acknowledgeHost(target.host, options())
})

function onSubmit(): void {
  if (comment.value.trim()) {
    void submit()
  }
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Acknowledge several problems')"
    closable
    @close="emit('close', succeeded > 0)"
  >
    <p class="maps-bulk-ack-modal__subtitle">
      {{ _t('%{count} from "%{origin}"', { origin, count: targets.length }) }}
    </p>

    <p v-if="skipped" class="maps-bulk-ack-modal__skipped">
      {{ _t('%{count} without a problem left out', { count: skipped }) }}
    </p>

    <CommandTargetList :targets="targets" />

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
      :succeeded="succeeded > 0"
      :succeeded-text="_t('%{count} acknowledged', { count: succeeded })"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close', succeeded > 0)">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="blocked || !comment.trim()" @click="onSubmit">
        {{
          submitting
            ? _t('Acknowledging %{current}/%{total}…', {
                current: progress,
                total: pending
              })
            : _t('Acknowledge %{count}', { count: pending })
        }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-bulk-ack-modal__subtitle {
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
}

.maps-bulk-ack-modal__skipped {
  margin: 0 0 var(--dimension-4);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
}

.maps-bulk-ack-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-bulk-ack-modal__label {
  display: block;
  margin-bottom: var(--dimension-3);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
  font-weight: 500;
}
</style>
