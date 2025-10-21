/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/*
 * This is a wrapper class for the FigureBase implementation within cmk-frontend.
 * Calling this class instead of referencing the cmk-frontend code directly keeps other Vue files
 * clean, i.e. well-typed.
 *
 * TODO: Once we migrate the figure code from cmk-frontend to cmk-frontend-vue we can remove/extend
 * this file.
 */
import axios from 'axios'
import { inject } from 'vue'

import type { FilterHTTPVars } from '@/dashboard-wip/types/widget.ts'

import type { NtopType } from './types.ts'

export const getIfid = async (): Promise<string> => {
  const urlParams = inject('urlParams') as FilterHTTPVars
  if ('ifid' in urlParams && urlParams.ifid) {
    return urlParams.ifid
  } else {
    try {
      const response = await axios.get('ajax_ntop_ifid.py')

      if (response.data.result_code !== 0) {
        throw new Error(`DashboardContentNtop: Error fetching ifid: ${response.data.result}`)
      } else {
        return response.data.result as string
      }
    } catch (error) {
      throw new Error(`DashboardContentNtop: Request of ifid failed: ${error}`)
    }
  }
}

class NtopQuickStatsInterface {
  // the correct type of instance would be interface_table from the JS ntop code
  qsInstance
  _vlanid = '0'

  constructor(interfaceDivId: string, ifid: string) {
    // @ts-expect-error comes from different javascript file
    const cmkToolkit = window['cmk']

    const httpVarsString: string = new URLSearchParams({
      ifid: ifid,
      vlanid: this._vlanid
    }).toString()
    const postUrl: string = `ajax_ntop_interface_quickstats.py?${httpVarsString}`

    const qsInstance = new cmkToolkit.ntop.utils.interface_table(`#${interfaceDivId}`)
    qsInstance.set_host_address('')
    qsInstance.set_ifid(ifid)
    qsInstance.set_vlanid(this._vlanid)
    qsInstance.set_post_url_and_body(postUrl)
    qsInstance.initialize()
    qsInstance.scheduler.set_update_interval(2)
    qsInstance.scheduler.force_update()
    this.qsInstance = qsInstance

    return this
  }

  public disable() {
    if (this.qsInstance && this.qsInstance.scheduler) {
      this.qsInstance.scheduler.disable()
    }
  }
}

export class NtopBase {
  // the correct type of instance would be NtopAlertsTabBar from the JS ntop code
  instance
  _quickStatsInterface: NtopQuickStatsInterface
  _type: NtopType

  constructor(type: NtopType, interfaceDivId: string, divSelectorId: string, ifid: string) {
    // Set up quickstats interface
    this._quickStatsInterface = new NtopQuickStatsInterface(interfaceDivId, ifid)

    // @ts-expect-error comes from different javascript file
    const cmkToolkit = window['cmk']

    // Set up type-specific ntop figure
    switch (type) {
      case 'ntop_alerts':
        this.instance = new cmkToolkit.ntop.alerts.NtopAlertsTabBar(`#${divSelectorId}`)
        break
      case 'ntop_flows':
        this.instance = new cmkToolkit.ntop.flows.FlowsDashlet(`#${divSelectorId}`)
        break
      case 'ntop_top_talkers':
        this.instance = new cmkToolkit.ntop.top_talkers.TopTalkersDashlet(`#${divSelectorId}`)
        break
      default:
        throw new Error(`DashboardContentNtop: invalid type "${type}"`)
    }

    this._type = type
    this.instance.initialize()
    if (type !== 'ntop_alerts') {
      this.instance.set_ids(ifid)
    }

    return this
  }

  public disable() {
    if (this._quickStatsInterface) {
      this._quickStatsInterface.disable()
    }

    if (this.instance) {
      if (this._type === 'ntop_alerts') {
        // cannot invoke type window['cmk'].ntop.alerts.ABCAlertsTab here
        // eslint-disable-next-line
        this.instance.get_tabs_list().forEach((tab: any) => {
          const page = tab.get_page()
          if (page) {
            if (page.scheduler) {
              page.scheduler.disable()
            }

            const multiDataFetcher = page.get_multi_data_fetcher()
            if (multiDataFetcher && multiDataFetcher.scheduler) {
              multiDataFetcher.scheduler.disable()
            }
          }
        })
      } else if (this.instance.scheduler) {
        // for ntop_flows and ntop_top_talkers
        this.instance.scheduler.disable()
      }
    }
  }
}
