<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'

const { _t } = usei18n()

defineProps<{
  activationIssues?: boolean
  hasForeignChangesWithoutPermission?: boolean
  siteProblems?: boolean
}>()
</script>

<template>
  <CmkIcon
    v-if="activationIssues"
    name="warning"
    variant="inline"
    :title="_t('Activation issues encountered')"
    class="mm-site-status-icons"
  />
  <CmkIcon
    v-if="hasForeignChangesWithoutPermission"
    name="contactgroups"
    variant="inline"
    :title="_t('Activation blocked by missing permissions for foreign changes')"
    class="mm-site-status-icons"
  />
  <CmkIcon
    v-if="siteProblems"
    name="assume-2"
    variant="inline"
    :title="_t('Activation blocked by site problems')"
    class="mm-site-status-icons"
  />
</template>

<style scoped>
.mm-site-status-icons {
  gap: var(--dimension-2);
}
</style>
