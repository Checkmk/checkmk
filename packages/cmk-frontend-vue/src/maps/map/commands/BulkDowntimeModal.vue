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
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Ref, computed, ref } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import MapsModal from '@/maps/shared/components/MapsModal.vue'
import type { CommandTarget } from '@/maps/types/api'
import type { ScheduleDowntimeOptions } from '@/monitoring/shared/api/actions/downtime'
import ScheduleDowntimeForm, {
  type ScheduleDowntimeFormValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { noDowntimeWindow } from '@/monitoring/shared/components/action/actions/scheduleDowntime'

import CommandFeedback from './CommandFeedback.vue'
import CommandTargetList from './CommandTargetList.vue'
import { messageOf } from './commandErrors'
import { childHostTargets, targetKindOf, useCommandForms } from './commandForms'
import { useBulkCommandSubmit } from './useBulkCommandSubmit'

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
const forms = useCommandForms()
const draft = ref(forms.downtimeValues()) as Ref<ScheduleDowntimeFormValues>
const valid = ref(false)
const children = ref<CommandTarget[]>([])
// Resolved once per submit, so every target gets the same window.
let downtime: ScheduleDowntimeOptions | null = null

const { submitting, progress, succeeded, pending, error, blocked, submit, reject } =
  useBulkCommandSubmit({
    what: 'bulk-downtime',
    targets: () => [...props.targets, ...children.value],
    onDone: () => emit('close', true),
    send: (target) => {
      const options = downtime!
      return target.service
        ? commands.downtimeService(target.host, target.service, options)
        : commands.downtimeHost(target.host, options)
    }
  })

const kind = computed(() => targetKindOf(props.targets))

async function onSubmit(): Promise<void> {
  if (!valid.value || blocked.value) {
    return
  }
  downtime = forms.downtimeOptions(draft.value)
  if (downtime === null) {
    reject(noDowntimeWindow().message)
    return
  }
  // Looked up before the first run only: a retry is about what refused.
  if (progress.value === 0) {
    try {
      children.value = draft.value.includeChildHosts
        ? await childHostTargets(commands, props.targets)
        : []
    } catch (caught) {
      reject(messageOf(caught, _t('Could not find the child hosts')))
      return
    }
  }
  await submit()
}
</script>

<template>
  <MapsModal
    :open="true"
    :title="_t('Schedule downtime for several')"
    :scrolls="false"
    closable
    @close="emit('close', succeeded > 0)"
  >
    <p class="maps-bulk-downtime-modal__subtitle">
      {{ _t('%{count} from "%{origin}"', { origin, count: targets.length }) }}
    </p>

    <CommandTargetList :targets="targets" />

    <ScheduleDowntimeForm
      v-model="draft"
      class="maps-bulk-downtime-modal__form"
      v-bind="forms.downtimeProps(kind)"
      @update:valid="valid = $event"
    />

    <CommandFeedback
      :error="error"
      :succeeded="succeeded > 0"
      :succeeded-text="_t('Downtime scheduled for %{count}', { count: succeeded })"
    />

    <template #footer>
      <CmkButton variant="secondary" @click="emit('close', succeeded > 0)">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="blocked || !valid" @click="onSubmit">
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

/* A fixed width, so opening the advanced options, whose labels are long, wraps
   them instead of widening the dialog around the form. */
.maps-bulk-downtime-modal__form {
  width: min(520px, 80vw);
  margin-top: var(--dimension-5);
}
</style>
