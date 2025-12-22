/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from '@/lib/i18n'

import type { Suggestion } from '@/components/CmkSuggestions'

const { _t } = usei18n()

export const DATA_RANGE_SYMBOL_SUGGESTIONS: Suggestion[] = [
  { name: 'DecimalNotation_%_AutoPrecision_2', title: _t('% (Decimal, auto precision, 2 digits)') },
  {
    name: 'DecimalNotation_%_StrictPrecision_0',
    title: _t('% (Decimal, strict precision, 0 digits)')
  },
  {
    name: 'DecimalNotation_%_StrictPrecision_2',
    title: _t('% (Decimal, strict precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_%/m_AutoPrecision_2',
    title: _t('%/m (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_/s_AutoPrecision_2',
    title: _t('/s (Decimal, auto precision, 2 digits)')
  },
  { name: 'DecimalNotation_A_AutoPrecision_3', title: _t('A (Decimal, auto precision, 3 digits)') },
  {
    name: 'DecimalNotation_A_StrictPrecision_3',
    title: _t('A (Decimal, strict precision, 3 digits)')
  },
  { name: 'IECNotation_B_AutoPrecision_2', title: _t('B (IEC, auto precision, 2 digits)') },
  { name: 'IECNotation_B_StrictPrecision_2', title: _t('B (IEC, strict precision, 2 digits)') },
  { name: 'IECNotation_B/d_AutoPrecision_2', title: _t('B/d (IEC, auto precision, 2 digits)') },
  { name: 'IECNotation_B/op_AutoPrecision_2', title: _t('B/op (IEC, auto precision, 2 digits)') },
  { name: 'SINotation_B/req_AutoPrecision_2', title: _t('B/req (SI, auto precision, 2 digits)') },
  { name: 'IECNotation_B/s_AutoPrecision_2', title: _t('B/s (IEC, auto precision, 2 digits)') },
  { name: 'SINotation_B/s_AutoPrecision_2', title: _t('B/s (SI, auto precision, 2 digits)') },
  {
    name: 'DecimalNotation_Hz_AutoPrecision_2',
    title: _t('Hz (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_Pa_AutoPrecision_3',
    title: _t('Pa (Decimal, auto precision, 3 digits)')
  },
  {
    name: 'DecimalNotation_Percent_AutoPrecision_2',
    title: _t('Percent (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_RCU_AutoPrecision_2',
    title: _t('RCU (Decimal, auto precision, 2 digits)')
  },
  { name: 'DecimalNotation_V_AutoPrecision_3', title: _t('V (Decimal, auto precision, 3 digits)') },
  {
    name: 'DecimalNotation_VA_AutoPrecision_3',
    title: _t('VA (Decimal, auto precision, 3 digits)')
  },
  {
    name: 'DecimalNotation_Volt_AutoPrecision_2',
    title: _t('Volt (Decimal, auto precision, 2 digits)')
  },
  { name: 'DecimalNotation_W_AutoPrecision_3', title: _t('W (Decimal, auto precision, 3 digits)') },
  {
    name: 'DecimalNotation_WCU_AutoPrecision_2',
    title: _t('WCU (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_Watt_AutoPrecision_2',
    title: _t('Watt (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_Wh_AutoPrecision_3',
    title: _t('Wh (Decimal, auto precision, 3 digits)')
  },
  {
    name: 'DecimalNotation_bar_AutoPrecision_4',
    title: _t('bar (Decimal, auto precision, 4 digits)')
  },
  {
    name: 'IECNotation_bits/d_AutoPrecision_2',
    title: _t('bits/d (IEC, auto precision, 2 digits)')
  },
  {
    name: 'IECNotation_bits/s_AutoPrecision_2',
    title: _t('bits/s (IEC, auto precision, 2 digits)')
  },
  { name: 'SINotation_bits/s_AutoPrecision_2', title: _t('bits/s (SI, auto precision, 2 digits)') },
  {
    name: 'DecimalNotation_dB_AutoPrecision_2',
    title: _t('dB (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_dBm_AutoPrecision_2',
    title: _t('dBm (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_dBmV_AutoPrecision_2',
    title: _t('dBmV (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_days_StrictPrecision_2',
    title: _t('days (Decimal, strict precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_l/s_AutoPrecision_3',
    title: _t('l/s (Decimal, auto precision, 3 digits)')
  },
  {
    name: 'DecimalNotation__AutoPrecision_2',
    title: _t('no symbol (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation__StrictPrecision_0',
    title: _t('no symbol (Decimal, strict precision, 0 digits)')
  },
  {
    name: 'DecimalNotation__StrictPrecision_2',
    title: _t('no symbol (Decimal, strict precision, 2 digits)')
  },
  {
    name: 'SINotation__StrictPrecision_2',
    title: _t('no symbol (SI, strict precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_ppm_AutoPrecision_2',
    title: _t('ppm (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_req/s_AutoPrecision_2',
    title: _t('req/s (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_rpm_AutoPrecision_4',
    title: _t('rpm (Decimal, auto precision, 4 digits)')
  },
  { name: 'TimeNotation_s_AutoPrecision_0', title: _t('s (Time, auto precision, 0 digits)') },
  { name: 'TimeNotation_s_AutoPrecision_2', title: _t('s (Time, auto precision, 2 digits)') },
  {
    name: 'DecimalNotation_s/s_AutoPrecision_2',
    title: _t('s/s (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_Tasks_StrictPrecision_0',
    title: _t('tasks (Decimal, strict precision, 0 digits)')
  },
  {
    name: 'DecimalNotation_°C_AutoPrecision_2',
    title: _t('°C (Decimal, auto precision, 2 digits)')
  },
  {
    name: 'DecimalNotation_€_StrictPrecision_2',
    title: _t('€ (Decimal, strict precision, 2 digits)')
  }
]
