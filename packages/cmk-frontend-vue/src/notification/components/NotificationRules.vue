<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { RuleSection } from 'cmk-shared-typing/typescript/notifications'

defineProps<{
  rule_sections: RuleSection[]
}>()
</script>

<template>
  <div class="notification-rules">
    <div
      v-for="(section, index) in rule_sections"
      :key="index"
      class="notification-rules__section rulesets"
    >
      <h3>{{ section['i18n'] }}</h3>
      <table v-for="(topic, key) in section['topics']" :key="key" class="notification-rules__table">
        <thead>
          <tr>
            <th>
              <div v-if="topic.i18n" class="notification-rules__ruleset-topic">
                {{ topic.i18n }}
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td colspan="2">
              <div v-for="(rule, idx) in topic['rules']" :key="idx" class="ruleset">
                <div class="text">
                  <a :href="rule['link']" :title="rule['i18n']">{{ rule['i18n'] }}</a>
                  <span class="dots"
                    >.....................................................................</span
                  >
                </div>
                <div class="rulecount nonzero">{{ rule['count'] }}</div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.notification-rules {
  display: flex;
  flex-grow: 1;

  .notification-rules__section {
    flex-grow: 1;
    flex-basis: 0;
    border: 1px solid var(--default-border-color);
    margin-left: 4px;

    h3 {
      margin-top: 0;
      font-size: var(--font-size-normal);
    }
  }
  div.ruleset > div.text {
    max-width: calc(100% - 20px);
  }

  .notification-rules__ruleset-topic {
    margin: var(--spacing-half) var(--spacing) 0 var(--spacing);
    float: left;
    font-weight: var(--font-weight-bold);
  }
}
</style>
