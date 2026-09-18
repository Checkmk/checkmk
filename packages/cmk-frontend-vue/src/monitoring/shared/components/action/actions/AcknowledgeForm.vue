<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import type { ZonedDateTime } from '@internationalized/date'

export interface AcknowledgeValues {
  comment: string
  expireOnEnabled: boolean
  expireOn: ZonedDateTime | null
  sticky: boolean
  persistent: boolean
  notify: boolean
}

export function isAcknowledgeValid(values: AcknowledgeValues): boolean {
  const expiryValid = !values.expireOnEnabled || values.expireOn !== null
  return values.comment.trim() !== '' && expiryValid
}
</script>

<script setup lang="ts">
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkDateTimePicker from 'cmk-ui-library/components/date-time/CmkDateTimePicker.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import type { ActionTargetKind } from '../types'

const props = withDefaults(
  defineProps<{
    targetKind?: ActionTargetKind
    /** Where the option defaults are edited; absent for users who may not edit them. */
    presetsUrl?: string | null
    notificationRulesUrl?: string | null
  }>(),
  { targetKind: 'host', presetsUrl: null, notificationRulesUrl: null }
)

const model = defineModel<AcknowledgeValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t, _tp } = usei18n()

const expireOnHelp = computed(() =>
  props.targetKind === 'service'
    ? _t(
        'Let the acknowledgement expire automatically. Leave this off to keep it until the ' +
          'service recovers or it is removed manually.'
      )
    : _t(
        'Let the acknowledgement expire automatically. Leave this off to keep it until the ' +
          'host recovers or it is removed manually.'
      )
)

const stickyLabel = computed(() =>
  props.targetKind === 'service'
    ? _t('Ignore status changes until the service recovers (OK)')
    : _t('Ignore status changes until the host recovers (OK/UP)')
)

/**
 * The link sits inside the sentence, so the sentence stays one msgid - split into
 * fragments its word order could not survive translation - and the placeholder marks
 * where the link goes, the way the classic form does it.
 */
const notifyLabelParts = computed(() =>
  _tp(
    '%{link} is a link to the notification rules page',
    'Notify affected users if %{link} are in place (send notifications)'
  ).split('%{link}')
)

/**
 * The link sits inside the checkbox's own `<label>`, where a plain click would activate the
 * control as its default action and silently flip the option. Cancelling the event is the only
 * thing that stops that - stopping propagation does not, the activation is the default action,
 * not a listener - so the navigation has to be made explicitly.
 */
function openNotificationRules(event: MouseEvent): void {
  event.preventDefault()
  window.open(props.notificationRulesUrl ?? '', '_blank', 'noopener')
}

watch(model, (values) => emit('update:valid', isAcknowledgeValid(values)), {
  immediate: true,
  deep: true
})
</script>

<template>
  <div class="monitoring-acknowledge-form">
    <div class="monitoring-acknowledge-form__section">
      <label class="monitoring-acknowledge-form__field">
        <span class="monitoring-acknowledge-form__label">
          {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
        </span>
        <CmkInput
          v-model="model.comment"
          field-size="large"
          :placeholder="_t('Enter a comment…')"
        />
      </label>
    </div>

    <div class="monitoring-acknowledge-form__section">
      <div class="monitoring-acknowledge-form__options-header">
        <span class="monitoring-acknowledge-form__label">{{ _t('Options') }}</span>
        <CmkLink
          v-if="presetsUrl"
          class="monitoring-acknowledge-form__presets-link"
          :href="presetsUrl"
          target="_blank"
          rel="noopener"
        >
          {{ _t('(Edit defaults)') }}
        </CmkLink>
      </div>

      <CmkCheckbox v-model="model.expireOnEnabled" :label="_t('Expire on')" :help="expireOnHelp">
        <CmkDateTimePicker
          v-if="model.expireOnEnabled"
          v-model="model.expireOn"
          :nullable="true"
          :label="_t('Choose an expiry date & time')"
        />
      </CmkCheckbox>

      <CmkCheckbox v-model="model.sticky" :label="stickyLabel">
        <p class="monitoring-acknowledge-form__hint">
          <b>{{ _t('Example:') }}</b>
          {{ _t("Service was WARN and goes CRIT - acknowledgment doesn't expire.") }}
        </p>
      </CmkCheckbox>

      <CmkCheckbox
        v-model="model.persistent"
        :label="_t('Keep comment after acknowledgment expires')"
      />

      <CmkCheckbox v-model="model.notify">
        <template #label>
          {{ notifyLabelParts[0]
          }}<CmkLink
            v-if="notificationRulesUrl"
            :href="notificationRulesUrl"
            target="_blank"
            rel="noopener"
            @click="openNotificationRules"
            >{{ _t('notification rules') }}</CmkLink
          ><template v-else>{{ _t('notification rules') }}</template
          >{{ notifyLabelParts[1] }}
        </template>
      </CmkCheckbox>
    </div>
  </div>
</template>

<style scoped>
.monitoring-acknowledge-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-acknowledge-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-acknowledge-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-acknowledge-form__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  font-weight: var(--font-weight-bold);
}

.monitoring-acknowledge-form__options-header {
  display: flex;
  align-items: baseline;
  gap: var(--dimension-3);
}

.monitoring-acknowledge-form__presets-link {
  /* `.cmk-link` is `display: flex; width: 100%`, which would stretch the header row. */
  width: auto;
}

.monitoring-acknowledge-form__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}
</style>
