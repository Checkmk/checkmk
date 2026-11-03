<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Acknowledge several problems at once: the contributing leaves of a BI
aggregation, or the nodes an operator picked on a flow map.

Neither is a Checkmk host or service group, so there is no single command for
them and each is acknowledged in turn.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget } from '@/maps/types/api'
import AcknowledgeForm, {
  type AcknowledgeValues
} from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'

import CommandFeedback from './CommandFeedback.vue'
import CommandTargetList from './CommandTargetList.vue'
import { acknowledgeOptions, targetKindOf, useCommandForms } from './commandForms'
import { useBulkCommandSubmit } from './useBulkCommandSubmit'

const { commands } = useMapsApis()

const props = defineProps<{
  /** What the operator picked these from — an aggregation, a map. */
  origin: string
  targets: CommandTarget[]
  /** How many were picked but have no problem to acknowledge, and are left out. */
  skipped?: number
}>()

// Whether the operator's selection was actually commanded: the caller keeps it
// intact when it was not, so a cancelled dialog does not cost them the picking.
const emit = defineEmits<{ close: [sent: boolean] }>()

const { _t } = usei18n()
const forms = useCommandForms()
const draft = ref(forms.acknowledgeValues()) as Ref<AcknowledgeValues>
const valid = ref(false)

const { submitting, progress, succeeded, pending, error, blocked, submit } = useBulkCommandSubmit({
  what: 'bulk-ack',
  targets: () => props.targets,
  onDone: () => emit('close', true),
  send: (target) => {
    const options = acknowledgeOptions(draft.value)
    return target.service
      ? commands.acknowledgeService(target.host, target.service, options)
      : commands.acknowledgeHost(target.host, options)
  }
})

function onSubmit(): void {
  if (valid.value) {
    void submit()
  }
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Acknowledge several problems')"
    :scrolls="false"
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

    <AcknowledgeForm
      v-model="draft"
      class="maps-bulk-ack-modal__form"
      v-bind="forms.acknowledgeProps(targetKindOf(targets))"
      @update:valid="valid = $event"
    />

    <CommandFeedback
      :error="error"
      :succeeded="succeeded > 0"
      :succeeded-text="_t('%{count} acknowledged', { count: succeeded })"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close', succeeded > 0)">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="blocked || !valid" @click="onSubmit">
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

.maps-bulk-ack-modal__form {
  margin-top: var(--dimension-5);
}
</style>
