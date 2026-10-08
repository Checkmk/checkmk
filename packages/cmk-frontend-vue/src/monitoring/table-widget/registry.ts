/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  HostsTableDescriptor,
  type MonitoringTableDescriptor,
  type MonitoringTableName,
  type MonitoringTableRows
} from './tableDescriptors'

export type MonitoringTableDescriptors = {
  [K in MonitoringTableName]: MonitoringTableDescriptor<MonitoringTableRows[K]>
}

export class MonitoringTableRegistry {
  private readonly descriptors: MonitoringTableDescriptors = {
    hosts: new HostsTableDescriptor()
  }

  descriptor<K extends MonitoringTableName>(table: K): MonitoringTableDescriptors[K] {
    return this.descriptors[table]
  }
}

export const monitoringTableRegistry = new MonitoringTableRegistry()
