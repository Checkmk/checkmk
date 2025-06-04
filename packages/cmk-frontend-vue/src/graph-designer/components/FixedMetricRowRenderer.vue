<!--
Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<template>
  <table>
    <tbody>
      <tr>
        <td><slot name="metric_cells"></slot></td>
        <td><slot name="metric_type"></slot></td>
      </tr>
    </tbody>
  </table>
</template>
