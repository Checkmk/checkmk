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

import { urlParamsKey } from '@/dashboard/types/injectionKeys.ts'
import type { FilterHTTPVars } from '@/dashboard/types/widget.ts'

import type { NtopType } from './types.ts'

export const getIfid = async (cmkToken: string | undefined): Promise<string> => {
  const urlParams = inject(urlParamsKey) as FilterHTTPVars
  if ('ifid' in urlParams && urlParams.ifid) {
    return urlParams.ifid
  } else {
    let exceptionSeverity: 'warning' | 'error' | null = null
    try {
      let ifidEndpointUrl: string
      if (cmkToken === undefined) {
        ifidEndpointUrl = 'ajax_ntop_ifid.py'
      } else {
        const httpVarsString: string = new URLSearchParams({ 'cmk-token': cmkToken }).toString()
        ifidEndpointUrl = `ntop_ifid_token_auth.py?${httpVarsString}`
      }
      const response = await axios.get(ifidEndpointUrl)

      if (response.data.result_code !== 0) {
        exceptionSeverity = response.data.severity
        throw response.data.result
      } else {
        return response.data.result as string
      }
    } catch (exception) {
      throw exceptionSeverity === 'warning'
        ? exception
        : new Error(`DashboardContentNtop: Request of ifid failed: ${exception}`)
    }
  }
}

class NtopQuickStatsInterface {
  // the correct type of instance would be interface_table from the JS ntop code
  qsInstance
  _vlanid = '0'

  constructor(interfaceDivId: string, ifid: string, cmkToken: string | undefined) {
    // @ts-expect-error comes from different javascript file
    const cmkToolkit = window['cmk']

    const httpVars: FilterHTTPVars = {
      ifid: ifid,
      vlanid: this._vlanid
    }
    let baseUrl: string = 'ajax_ntop_interface_quickstats.py'
    if (cmkToken !== undefined) {
      httpVars['cmk-token'] = cmkToken
      baseUrl = 'ntop_interface_quickstats_token_auth.py'
    }
    const httpVarsString: string = new URLSearchParams(httpVars).toString()
    const postUrl = `${baseUrl}?${httpVarsString}`

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

  constructor(
    type: NtopType,
    interfaceDivId: string,
    divSelectorId: string,
    ifid: string,
    cmkToken: string | undefined
  ) {
    // Set up quickstats interface
    this._quickStatsInterface = new NtopQuickStatsInterface(interfaceDivId, ifid, cmkToken)

    // @ts-expect-error comes from different javascript file
    const cmkToolkit = window['cmk']

    // Set up type-specific ntop figure
    switch (type) {
      case 'ntop_alerts':
        this.instance = new cmkToolkit.ntop.alerts.NtopAlertsTabBar(`#${divSelectorId}`, cmkToken)
        break
      case 'ntop_flows':
        this.instance = new cmkToolkit.ntop.flows.FlowsDashlet(`#${divSelectorId}`, cmkToken)
        break
      case 'ntop_top_talkers':
        this.instance = new cmkToolkit.ntop.top_talkers.TopTalkersDashlet(
          `#${divSelectorId}`,
          cmkToken
        )
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
