<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
interface FieldDescriptionProps {
  dots?: boolean
}

withDefaults(defineProps<FieldDescriptionProps>(), {
  dots: true
})
</script>

<template>
  <div class="table-form-row">
    <div class="field-description">
      <span class="field-description__label">
        <slot />
        <span v-if="dots" class="field-description-dots"></span>
      </span>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.table-form-row {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.field-description {
  flex: 1;
  direction: ltr;
  overflow-wrap: break-word;
  overflow: hidden;
  text-align: left;
  text-wrap-mode: nowrap;
  position: relative;
  margin-right: 10px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.field-description__label {
  width: 100%;
  display: block;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.field-description-dots {
  position: absolute;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.field-description-dots::after {
  content: '........................................................................................................................................................................................................';
}
</style>
