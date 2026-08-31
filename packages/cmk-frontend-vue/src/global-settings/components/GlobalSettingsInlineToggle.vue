<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalSettingsVariable } from 'cmk-shared-typing/typescript/global_settings'
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject, ref } from 'vue'

import { GLOBAL_SETTINGS_TOGGLE } from '../api'

const { _t } = usei18n()

const { variable } = defineProps<{ variable: GlobalSettingsVariable }>()

const injectedToggleSetting = inject(GLOBAL_SETTINGS_TOGGLE)
if (injectedToggleSetting === undefined) {
  throw new Error('GlobalSettingsInlineToggle requires an injected toggle handler')
}
const toggleSetting = injectedToggleSetting

type ToggleState =
  | { variant: 'idle' }
  | { variant: 'pending' }
  | { variant: 'error'; message: TranslatedString }

const state = ref<ToggleState>({ variant: 'idle' })

const checked = computed(() => variable.value === true)

async function toggle(): Promise<void> {
  if (state.value.variant === 'pending') {
    return
  }
  state.value = { variant: 'pending' }
  const failure = await toggleSetting(variable, !checked.value)
  state.value = failure === null ? { variant: 'idle' } : { variant: 'error', message: failure }
}
</script>

<template>
  <span
    class="global-settings-inline-toggle"
    role="switch"
    tabindex="0"
    :aria-checked="checked"
    :aria-busy="state.variant === 'pending'"
    :aria-label="_t('Toggle %{title}', { title: variable.spec.title })"
    @click.stop="toggle"
    @keydown.space.stop.prevent="toggle"
    @keydown.enter.stop.prevent="toggle"
  >
    <CmkSwitch inert :model-value="checked" />
  </span>
  <span v-if="state.variant === 'error'" class="global-settings-inline-toggle__error">
    {{ state.message }}
  </span>
</template>

<style scoped>
.global-settings-inline-toggle {
  display: inline-flex;
  border-radius: 2px;

  &:focus-visible {
    outline: 1px solid var(--success);
  }

  &[aria-busy='true'] {
    opacity: 0.5;
    cursor: wait;
  }
}

.global-settings-inline-toggle__error {
  color: var(--color-danger);
}
</style>
