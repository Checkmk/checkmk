<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import NotificationRules from '@/notification/components/NotificationRules.vue'
import type { RuleSection } from 'cmk-shared-typing/typescript/notifications'

defineProps<{
  parameters: RuleSection[]
  i18n: Record<string, string>
}>()
</script>

<template>
  <NotificationRules v-if="parameters.length !== 0" :rule_sections="parameters"></NotificationRules>
  <table v-else class="table ruleset">
    <tbody>
      <tr>
        <td>
          <div class="ruleset data odd0 no_match">
            {{ i18n.no_parameter_match }}
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped></style>
