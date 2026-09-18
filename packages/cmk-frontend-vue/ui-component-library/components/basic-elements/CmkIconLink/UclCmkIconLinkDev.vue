<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { IconSizeNames } from 'cmk-ui-library/components/CmkIcon'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'

defineProps<{ screenshotMode: boolean }>()

const sizes: IconSizeNames[] = ['xsmall', 'small', 'medium', 'large', 'xlarge', 'xxlarge']
</script>

<template>
  <dl>
    <dt><code>&lt;CmkIconLink name="main-help" href="..." /&gt;</code></dt>
    <dd>
      <CmkIconLink name="main-help" href="https://docs.checkmk.com" />
    </dd>

    <dt><code>&lt;CmkIconLink name="main-help" title="Get Help" href="..." /&gt;</code></dt>
    <dd>
      <CmkIconLink name="main-help" title="Get Help" href="https://docs.checkmk.com" />
    </dd>

    <dt>Sizes</dt>
    <dd class="ucl-cmk-icon-link-dev__row">
      <div v-for="size in sizes" :key="size" class="ucl-cmk-icon-link-dev__size-entry">
        <span>{{ size }}</span>
        <CmkIconLink name="main-help" :size="size" :title="size" href="https://docs.checkmk.com" />
      </div>
    </dd>
    <dt>Variants</dt>
    <dd class="ucl-cmk-icon-link-dev__row">
      <CmkIconLink name="main-help" size="medium" title="plain" href="https://docs.checkmk.com" />
      <span>plain </span>

      <CmkIconLink
        name="main-help"
        variant="inline"
        size="medium"
        title="inline"
        href="https://docs.checkmk.com"
      />
      <span>inline </span>
    </dd>

    <dt>Various icons</dt>
    <dd class="ucl-cmk-icon-link-dev__row">
      <CmkIconLink name="close" title="Close" size="medium" href="https://docs.checkmk.com" />
      <CmkIconLink name="delete" title="Delete" size="medium" href="https://docs.checkmk.com" />
      <CmkIconLink name="edit" title="Edit" size="medium" href="https://docs.checkmk.com" />
      <CmkIconLink name="plus" title="Add" size="medium" href="https://docs.checkmk.com" />
    </dd>

    <dt>Multitone icons</dt>
    <dd class="ucl-cmk-icon-link-dev__row">
      <CmkIconLink
        name="more-actions"
        primary-color="font"
        title="More actions"
        size="large"
        href="https://docs.checkmk.com"
      />
      <CmkIconLink
        name="reload"
        primary-color="info"
        title="Reload"
        size="large"
        href="https://docs.checkmk.com"
      />
      <CmkIconLink
        name="success"
        primary-color="success"
        title="Success"
        size="large"
        href="https://docs.checkmk.com"
      />
      <CmkIconLink
        name="error"
        primary-color="danger"
        title="Error"
        size="large"
        href="https://docs.checkmk.com"
      />
      <CmkIconLink
        name="aggr"
        primary-color="info"
        secondary-color="warning"
        title="Aggregation (two-color)"
        size="large"
        href="https://docs.checkmk.com"
      />
      <CmkIconLink
        name="share"
        :primary-color="{ custom: 'var(--color-purple-60)' }"
        title="Custom color"
        size="large"
        href="https://docs.checkmk.com"
      />
    </dd>

    <dt>Target</dt>
    <dd class="ucl-cmk-icon-link-dev__row">
      <CmkIconLink
        name="main-help"
        title="Opens in a new tab"
        size="medium"
        href="https://docs.checkmk.com"
        target="_blank"
      />
      <span>target="_blank"</span>
    </dd>
  </dl>
</template>

<style scoped>
dt {
  margin-top: 2em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

dd {
  margin: 0;
  padding: 0;
}

.ucl-cmk-icon-link-dev__row {
  display: flex;
  align-items: center;
  gap: 1em;
}

.ucl-cmk-icon-link-dev__size-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25em;
}
</style>
