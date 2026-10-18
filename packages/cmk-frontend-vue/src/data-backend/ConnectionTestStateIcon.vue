<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{ state: components['schemas']['_ConnectionTestStep']['state'] | 'warning' }>()

const { _t } = usei18n()
</script>

<template>
  <CmkIcon v-if="state === 'running'" name="load-graph" size="medium" :title="_t('Running')" />
  <CmkMultitoneIcon
    v-else-if="state === 'passed'"
    name="success"
    primary-color="success"
    size="medium"
    :aria-label="_t('Passed')"
  />
  <CmkMultitoneIcon
    v-else-if="state === 'failed'"
    name="error"
    primary-color="danger"
    size="medium"
    :aria-label="_t('Failed')"
  />
  <CmkMultitoneIcon
    v-else-if="state === 'warning'"
    name="warning"
    primary-color="warning"
    size="medium"
    :aria-label="_t('Warning')"
  />
  <CmkMultitoneIcon
    v-else
    name="check-circle"
    primary-color="others"
    size="medium"
    :aria-label="_t('Pending')"
  />
</template>
