<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CalendarDate } from '@internationalized/date'
import { useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { TriggerAria } from '@/components/CmkFlyout'

import type { DateFormatParts } from '../../types'
import FieldBox from './FieldBox.vue'
import SegmentedField from './SegmentedField.vue'
import { useDateField } from './useDateField'
import { useSegmentedField } from './useSegmentedField'

const props = withDefaults(
  defineProps<{
    /** Resolved date section order/separator (e.g. `settings.dateFormat` from the resolver). */
    dateFormat: DateFormatParts
    /** Full month names (index 0 = January) for the month segment's spoken value. */
    monthNames: TranslatedString[]
    /** Show the leading calendar icon. Fields inside a flyout render without icons. */
    showIcon?: boolean
    /** Render the field non-interactive and dimmed. */
    disabled?: boolean
    /** Accessible name for the field; defaults to "Date". */
    ariaLabel?: TranslatedString
    /** Merge the field box into the popup opening below it (see FieldBox). */
    open?: boolean
    /** ARIA wiring from the flyout, placed on the icon trigger button (see FieldBox). */
    triggerAria?: TriggerAria | undefined
  }>(),
  { showIcon: true }
)

/** The selected date; `null` while empty. */
const model = defineModel<CalendarDate | null>({ required: true })

const emit = defineEmits<{
  /** The user requested commit (Enter in a cell). */
  (e: 'commit'): void
  /** The user requested the popup open (click) — only emitted in trigger mode. */
  (e: 'open'): void
  /** The user toggled the popup via the icon button — only emitted in trigger mode. */
  (e: 'toggle'): void
}>()

const { _t } = usei18n()

const api = useSegmentedField(
  useDateField(
    () => props.dateFormat,
    () => props.monthNames
  ),
  model,
  {
    commit: () => emit('commit')
  }
)

const fieldBoxRef = useTemplateRef<InstanceType<typeof FieldBox>>('fieldBoxRef')

/** Focus the icon trigger button so the flyout can restore focus on close (see `CmkFlyout`'s
 *  `restoreFocus`). No-op unless the icon trigger button is rendered. */
defineExpose({ focusTriggerButton: () => fieldBoxRef.value?.focusTriggerButton() })
</script>

<template>
  <FieldBox
    ref="fieldBoxRef"
    :icon="props.showIcon ? 'user-interface' : undefined"
    :disabled="props.disabled"
    :open="props.open"
    as-trigger
    :trigger-aria="props.triggerAria"
    :icon-label="_t('Open calendar')"
    @open="emit('open')"
    @toggle="emit('toggle')"
  >
    <SegmentedField
      :api="api"
      :disabled="props.disabled"
      :aria-label="props.ariaLabel ?? _t('Date')"
    />
  </FieldBox>
</template>
