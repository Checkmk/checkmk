<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, onMounted, ref } from 'vue'

import {
  configNameFormatErrors,
  configNameTakenErrors,
  nextAvailableConfigName
} from '@/lib/configuration-name'

import { listCustomServiceNames } from '../api'

const NAME_PREFIX = 'custom_service_config_'

const { _t } = usei18n()

const configurationNameId = useId()

const configurationName = defineModel<string>('configurationName', { required: true })

const displayErrors = ref(false)
const takenErrors = ref<string[]>([])

const formatErrors = computed<string[]>(() =>
  displayErrors.value ? configNameFormatErrors(configurationName.value) : []
)
const allErrors = computed<string[]>(() => [...formatErrors.value, ...takenErrors.value])

onMounted(async () => {
  if (configurationName.value !== '') {
    return
  }
  let existingNames: string[] = []
  try {
    existingNames = await listCustomServiceNames()
  } catch {
    // Fall back to the first slot.
  }
  if (configurationName.value === '') {
    configurationName.value = nextAvailableConfigName(existingNames, NAME_PREFIX)
  }
})

async function validate(): Promise<boolean> {
  displayErrors.value = true
  takenErrors.value = []
  if (formatErrors.value.length > 0) {
    return false
  }
  try {
    takenErrors.value = configNameTakenErrors(
      configurationName.value,
      await listCustomServiceNames()
    )
  } catch {
    takenErrors.value = [_t('Failed to validate the configuration name. Please try again.')]
  }
  return takenErrors.value.length === 0
}

defineExpose({ validate })
</script>

<template>
  <div
    class="mode-custom-services-configure-name-step"
    role="group"
    :aria-label="_t('General configuration properties')"
  >
    <CmkLabel :for="configurationNameId"
      >{{ _t('Configuration name') }} <CmkLabelRequired
    /></CmkLabel>
    <CmkInput
      :id="configurationNameId"
      v-model="configurationName"
      type="text"
      field-size="medium"
      :placeholder="`${NAME_PREFIX}1`"
      :external-errors="allErrors"
      aria-required="true"
    />
  </div>
</template>

<style scoped>
.mode-custom-services-configure-name-step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--spacing) var(--dimension-6);
  align-items: start;
}
</style>
