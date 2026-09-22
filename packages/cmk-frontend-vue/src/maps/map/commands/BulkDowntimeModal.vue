<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Take several things out of monitoring for the same window, because what is
about to happen to them is planned — the nodes an operator picked on a flow
map, say, before a switch is swapped out.

They are not a Checkmk host or service group, so there is no single command for
them; each is scheduled in turn, a few at a time.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkTimeRangePicker from 'cmk-ui-library/components/date-time/CmkTimeRangePicker.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import type { DowntimeOptions } from '@/maps/api/commands'
import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget } from '@/maps/types/api'

import CommandFeedback from './CommandFeedback.vue'
import CommandTargetList from './CommandTargetList.vue'
import { useBulkCommandSubmit } from './useBulkCommandSubmit'
import { useDowntimeWindow } from './useDowntimeWindow'

const { commands } = useMapsApis()

const props = defineProps<{
  /** What the operator picked these from, named in the confirmation. */
  origin: string
  targets: CommandTarget[]
}>()

// Whether the operator's selection was actually commanded: the caller keeps it
// intact when it was not, so a cancelled dialog does not cost them the picking.
const emit = defineEmits<{ close: [sent: boolean] }>()

const { _t } = usei18n()
const { range, isValid, asIso } = useDowntimeWindow()
const comment = ref('')

const { submitting, progress, succeeded, pending, error, blocked, submit, reject } =
  useBulkCommandSubmit({
    what: 'bulk-downtime',
    targets: () => props.targets,
    onDone: () => emit('close', true),
    send: (target) => {
      const window = asIso()
      const options: DowntimeOptions = {
        startTime: window.start,
        endTime: window.end,
        comment: comment.value
      }
      return target.service
        ? commands.downtimeService(target.host, target.service, options)
        : commands.downtimeHost(target.host, options)
    }
  })

function onSubmit(): void {
  if (!comment.value.trim()) {
    return
  }
  if (!isValid.value) {
    reject(_t('Please provide a start and an end time, with the end after the start.'))
    return
  }
  void submit()
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Schedule downtime for several')"
    closable
    @close="emit('close', succeeded > 0)"
  >
    <p class="maps-bulk-downtime-modal__subtitle">
      {{ _t('%{count} from "%{origin}"', { origin, count: targets.length }) }}
    </p>

    <CommandTargetList :targets="targets" />

    <div class="maps-bulk-downtime-modal__fields">
      <div class="maps-bulk-downtime-modal__field">
        <CmkLabel>{{ _t('Downtime period') }}</CmkLabel>
        <CmkTimeRangePicker v-model="range" :label="_t('Downtime period')" />
      </div>
      <div class="maps-bulk-downtime-modal__field">
        <CmkLabel>{{ _t('Comment') }}</CmkLabel>
        <CmkInput v-model="comment" field-size="fill" :placeholder="`${_t('Comment')}…`" />
      </div>
    </div>

    <CommandFeedback
      :error="error"
      :succeeded="succeeded > 0"
      :succeeded-text="_t('Downtime scheduled for %{count}', { count: succeeded })"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close', succeeded > 0)">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton
        variant="primary"
        :disabled="blocked || !comment.trim() || !isValid"
        @click="onSubmit"
      >
        {{
          submitting
            ? _t('Scheduling %{current}/%{total}…', { current: progress, total: pending })
            : _t('Schedule downtime for %{count}', { count: pending })
        }}
      </CmkButton>
    </template>
  </MapsModal>
</template>

<style scoped>
.maps-bulk-downtime-modal__subtitle {
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
  color: var(--font-color-dimmed);
  font-size: var(--font-size-normal);
}

.maps-bulk-downtime-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.maps-bulk-downtime-modal__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}
</style>
