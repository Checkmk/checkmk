/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

abstract class UnitPrefixes {
    static _BASE: number;
    static _PREFIXES: string[];

    static scale_factor_and_prefix(value: number): [number, string] {
        let factor = this._BASE;
        let prefix = this._PREFIXES[this._PREFIXES.length - 1];

        for (const unit_prefix of this._PREFIXES.slice(0, -1)) {
            if (Math.abs(value) < factor) {
                prefix = unit_prefix;
                break;
            }
            factor *= this._BASE;
        }
        return [factor / this._BASE, prefix];
    }
}

export class SIUnitPrefixes extends UnitPrefixes {
    static override _BASE = 1000;
    static override _PREFIXES: string[] = [
        "",
        "k",
        "M",
        "G",
        "T",
        "P",
        "E",
        "Z",
        "Y",
    ];
}

export class IECUnitPrefixes extends UnitPrefixes {
    static override _BASE = 1024;
    static override _PREFIXES: string[] = [
        "",
        "Ki",
        "Mi",
        "Gi",
        "Ti",
        "Pi",
        "Ei",
        "Zi",
        "Yi",
    ];
}

export function drop_dotzero(value: number, digits = 2) {
    return value.toFixed(digits).replace(/\.0+$/, "");
}

export function fmt_number_with_precision(
    v: number,
    unit_prefix_type: typeof UnitPrefixes = SIUnitPrefixes,
    precision = 2,
    drop_zeroes = false,
    unit = ""
) {
    const [factor, prefix] = unit_prefix_type.scale_factor_and_prefix(v);
    const value = v / factor;
    const number = drop_zeroes
        ? drop_dotzero(value, precision)
        : value.toFixed(precision);
    return `${number} ${prefix + unit}`;
}

export function fmt_bytes(
    b: number,
    unit_prefix_type: typeof UnitPrefixes = IECUnitPrefixes,
    precision = 2,
    unit = "B"
) {
    return fmt_number_with_precision(
        b,
        unit_prefix_type,
        precision,
        false,
        unit
    );
}

export function fmt_nic_speed(speed: string) {
    const speedi = parseInt(speed);
    if (isNaN(speedi)) return speed;

    return fmt_number_with_precision(speedi, SIUnitPrefixes, 2, false, "bit/s");
}

export function percent(perc: number, scientific_notation = false) {
    if (perc == 0) return "0%";
    let result = "";
    if (scientific_notation && Math.abs(perc) >= 100000) {
        result = scientific(perc, 1);
    } else if (Math.abs(perc) >= 100) {
        result = perc.toFixed(0);
    } else if (0 < Math.abs(perc) && Math.abs(perc) < 0.01) {
        result = perc.toFixed(7);
        if (parseFloat(result) == 0) return "0%";
        if (scientific_notation && Math.abs(perc) < 0.0001) {
            result = scientific(perc, 1);
        } else {
            result = result.replace(/0+$/, "");
        }
    } else {
        result = drop_dotzero(perc, 2);
    }

    if (Number.isInteger(parseFloat(result)) && perc < 100)
        result = result + ".0";

    return result + "%";
}

export function scientific(v: number, precision: number): string {
    if (v == 0) return "0";
    if (v < 0) return "-" + scientific(-1 * v, precision);

    const exponent = frexpb(v, 10)[1];
    if (-3 <= exponent && exponent <= 4) {
        return v.toFixed(
            Math.min(precision, Math.max(0, precision - exponent))
        );
    }
    return v.toExponential(precision);
}

export function calculate_physical_precision(
    v: number,
    precision: number
): [string, number, number] {
    if (v == 0) return ["", precision - 1, 1];
    let exponent = frexpb(v, 10)[1];

    if (Number.isInteger(v)) precision = Math.min(precision, exponent + 1);

    let scale = 0;

    while (exponent < 0 && scale > -5) {
        scale -= 1;
        exponent += 3;
    }
    let places_before_comma = exponent + 1;
    let places_after_comma = precision - places_before_comma;
    while (places_after_comma < 0 && scale < 5) {
        scale += 1;
        exponent -= 3;
        places_before_comma = exponent + 1;
        places_after_comma = precision - places_before_comma;
    }

    const scale_symbols: Record<string, string> = {
        "-5": "f",
        "-4": "p",
        "-3": "n",
        "-2": "µ",
        "-1": "m",
        "0": "",
        "1": "k",
        "2": "M",
        "3": "G",
        "4": "T",
        "5": "P",
    };

    return [scale_symbols[scale], places_after_comma, 1000 ** scale];
}

export function physical_precision(
    v: number,
    precision: number,
    unit_symbol: string
): string {
    if (v < 0) return "-" + physical_precision(-1 * v, precision, unit_symbol);
    const [symbol, places_after_comma, factor] = calculate_physical_precision(
        v,
        precision
    );
    const scaled_value = v / factor;
    return (
        scaled_value.toFixed(places_after_comma) + " " + symbol + unit_symbol
    );
}

export function frexpb(x: number, base: number) {
    let exp = Math.floor(Math.log(x) / Math.log(base));
    let mantissa = x / base ** exp;
    if (mantissa < 1) {
        mantissa *= base;
        exp -= 1;
    }
    return [mantissa, exp];
}

export function approx_age(secs: number, negative = false): string {
    if (secs < 0) return approx_age(-1 * secs, true);
    if (negative) return "-" + calculate_approx_age_value(secs);
    return calculate_approx_age_value(secs);
}

function calculate_approx_age_value(secs: number): string {
    if (0 < secs && secs < 1) return physical_precision(secs, 3, "s");

    if (secs < 10) return secs.toFixed(2) + " s";
    if (secs < 60) return secs.toFixed(1) + " s";
    if (secs < 240) return secs.toFixed(0) + " s";

    const mins = Math.floor(secs / 60);
    if (mins < 360) return mins.toFixed(0) + " m";

    const hours = Math.floor(mins / 60);
    if (hours < 48) return hours.toFixed(0) + " h";

    const days = hours / 24;
    if (days < 6) return drop_dotzero(days, 1);
    if (days < 999) return days.toFixed() + " d";

    const years = days / 365;
    if (years < 10) return drop_dotzero(years, 1) + " y";

    return years.toFixed() + " y";
}

// When labeling domains we place ticks on integer values. Return integer
// divisors of the base we work on. Decimal by default, yet for Bytes we call
// it binary stepping and use the Hexadecimal.
export function domainIntervals(stepping: string) {
    if (stepping === "binary") return [1, 2, 4, 8, 16];
    return [1, 2, 5, 10];
}

function tickStep(range: number, ticks: number, increments: number[]) {
    const base = increments[increments.length - 1];
    const [mantissa, exp] = frexpb(range / ticks, base);
    return increments.find(e => mantissa <= e)! * base ** exp;
}

export function partitionableDomain(
    domain: [number, number],
    ticks: number,
    increments: number[]
) {
    let [start, end] = domain.map(x => x || 0).sort((a, b) => a - b);
    if (start === end) end += 1;
    let step = tickStep(end - start, ticks, increments);

    start = Math.floor(start / step) * step;
    end = Math.ceil(end / step) * step;
    step = tickStep(end - start, ticks, increments);
    return [start, end, step];
}

// test for later on a suite. JS can't compare arrays in a simple way ARRGG!
//function comp_array(a, b) {
//return a.every((val, i) => val === b[i]);
//}
//console.assert(comp_array(partitionableDomain([18, 2], 4, domainIntervals()), [0, 20, 5]));
//console.assert(comp_array(partitionableDomain([25, 2], 5, domainIntervals("binary")), [0, 32, 8]));
//console.assert(comp_array(partitionableDomain([NaN, 2], 2, domainIntervals("binary")), [0, 2, 2]));

export class AutoPrecision {
    digits: number;

    constructor(digits: number) {
        this.digits = digits;
    }
}

export class StrictPrecision {
    digits: number;

    constructor(digits: number) {
        this.digits = digits;
    }
}

interface Formatter {
    format_zero_or_one(value: number): string;
    format_small_number(value: number): string;
    format_large_number(value: number): string;
}

function apply_precision(
    value: number,
    precision: AutoPrecision | StrictPrecision
): number {
    const value_floor = Math.floor(value);
    if (value == value_floor) {
        return value;
    }
    const fractional_part = value - value_floor;
    let digits = precision.digits;
    if (precision instanceof AutoPrecision) {
        const exponent = Math.abs(Math.ceil(Math.log10(fractional_part)));
        if (exponent > 0) {
            digits = Math.max(exponent + 1, precision.digits);
        }
    }
    return value_floor + parseFloat(fractional_part.toPrecision(digits));
}

function rstrip(value: string, chars: string): string {
    let end = value.length - 1;
    while (chars.indexOf(value[end]) >= 0) {
        end -= 1;
    }
    return value.substr(0, end + 1);
}

function sanitize(value: string): string {
    value = rstrip(value, "0");
    return rstrip(value, ".");
}

class Preformatted {
    value: number;
    suffix: string;

    constructor(value: number, suffix: string) {
        this.value = value;
        this.suffix = suffix;
    }
}

interface preformat_number {
    (value: number, symbol: string): Preformatted;
}

export class NotationFormatter {
    symbol: string;
    precision: AutoPrecision | StrictPrecision;
    preformat_small_number: preformat_number;
    preformat_large_number: preformat_number;

    constructor(
        symbol: string,
        precision: AutoPrecision | StrictPrecision,
        preformat_small_number: preformat_number,
        preformat_large_number: preformat_number
    ) {
        this.symbol = symbol;
        this.precision = precision;
        this.preformat_small_number = preformat_small_number;
        this.preformat_large_number = preformat_large_number;
    }

    format_zero_or_one(value: number): string {
        return String(value) + " " + this.symbol;
    }

    format_small_number(value: number): string {
        const preformatted = this.preformat_small_number(value, this.symbol);
        const value_with_precision = apply_precision(
            preformatted.value,
            this.precision
        );
        return sanitize(String(value_with_precision)) + preformatted.suffix;
    }

    format_large_number(value: number): string {
        const preformatted = this.preformat_large_number(value, this.symbol);
        const value_with_precision = apply_precision(
            preformatted.value,
            this.precision
        );
        return sanitize(String(value_with_precision)) + preformatted.suffix;
    }
}

export function preformat_number(value: number, symbol: string): Preformatted {
    return new Preformatted(value, " " + symbol);
}

export function si_preformat_small_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value)) - 1;
    let factor: number;
    let prefix: string;
    if (exponent <= -24) {
        factor = Math.pow(1000, 8);
        prefix = "y";
    } else if (exponent <= -21) {
        factor = Math.pow(1000, 7);
        prefix = "z";
    } else if (exponent <= -18) {
        factor = Math.pow(1000, 6);
        prefix = "a";
    } else if (exponent <= -15) {
        factor = Math.pow(1000, 5);
        prefix = "f";
    } else if (exponent <= -12) {
        factor = Math.pow(1000, 4);
        prefix = "p";
    } else if (exponent <= -9) {
        factor = Math.pow(1000, 3);
        prefix = "n";
    } else if (exponent <= -6) {
        factor = Math.pow(1000, 2);
        prefix = "μ";
    } else if (exponent <= -3) {
        factor = 1000;
        prefix = "m";
    } else {
        factor = 1;
        prefix = "";
    }
    return new Preformatted(value * factor, " " + prefix + symbol);
}

export function si_preformat_large_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value));
    let factor: number;
    let prefix: string;
    if (exponent >= 24) {
        factor = Math.pow(1000, 8);
        prefix = "Y";
    } else if (exponent >= 21) {
        factor = Math.pow(1000, 7);
        prefix = "Z";
    } else if (exponent >= 18) {
        factor = Math.pow(1000, 6);
        prefix = "E";
    } else if (exponent >= 15) {
        factor = Math.pow(1000, 5);
        prefix = "P";
    } else if (exponent >= 12) {
        factor = Math.pow(1000, 4);
        prefix = "T";
    } else if (exponent >= 9) {
        factor = Math.pow(1000, 3);
        prefix = "G";
    } else if (exponent >= 6) {
        factor = Math.pow(1000, 2);
        prefix = "M";
    } else if (exponent >= 3) {
        factor = 1000;
        prefix = "k";
    } else {
        factor = 1;
        prefix = "";
    }
    return new Preformatted(value / factor, " " + prefix + symbol);
}

export function iec_preformat_large_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log2(value));
    let factor: number;
    let prefix: string;
    if (exponent >= 80) {
        factor = Math.pow(1024, 8);
        prefix = "Yi";
    } else if (exponent >= 70) {
        factor = Math.pow(1024, 7);
        prefix = "Zi";
    } else if (exponent >= 60) {
        factor = Math.pow(1024, 6);
        prefix = "Ei";
    } else if (exponent >= 50) {
        factor = Math.pow(1024, 5);
        prefix = "Pi";
    } else if (exponent >= 40) {
        factor = Math.pow(1024, 4);
        prefix = "Ti";
    } else if (exponent >= 30) {
        factor = Math.pow(1024, 3);
        prefix = "Gi";
    } else if (exponent >= 20) {
        factor = Math.pow(1024, 2);
        prefix = "Mi";
    } else if (exponent >= 10) {
        factor = 1024;
        prefix = "Ki";
    } else {
        factor = 1;
        prefix = "";
    }
    return new Preformatted(value / factor, " " + prefix + symbol);
}

export function standard_scientific_preformat_small_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value));
    return new Preformatted(
        value / Math.pow(10, exponent),
        "e" + exponent + " " + symbol
    );
}

export function standard_scientific_preformat_large_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value));
    return new Preformatted(
        value / Math.pow(10, exponent),
        "e+" + exponent + " " + symbol
    );
}

export function engineering_scientific_preformat_small_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value) / 3) * 3;
    return new Preformatted(
        value / Math.pow(10, exponent),
        "e" + exponent + " " + symbol
    );
}

export function engineering_scientific_preformat_large_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(10000) / 3) * 3;
    return new Preformatted(
        value / Math.pow(10, exponent),
        "e+" + exponent + " " + symbol
    );
}

export function time_preformat_small_number(
    value: number,
    symbol: string
): Preformatted {
    const exponent = Math.floor(Math.log10(value)) - 1;
    let factor: number;
    if (exponent <= -6) {
        factor = Math.pow(1000, 2);
        symbol = "µs";
    } else if (exponent <= -3) {
        factor = 1000;
        symbol = "ms";
    } else {
        factor = 1;
        symbol = "s";
    }
    return new Preformatted(value * factor, " " + symbol);
}

const _ONE_DAY = 86400;
const _ONE_HOUR = 3600;
const _ONE_MINUTE = 60;

export function time_preformat_large_number(
    value: number,
    symbol: string
): Preformatted {
    let factor: number;
    if (value >= _ONE_DAY) {
        factor = _ONE_DAY;
        symbol = "d";
    } else if (value >= _ONE_HOUR) {
        factor = _ONE_HOUR;
        symbol = "h";
    } else if (value >= _ONE_MINUTE) {
        factor = _ONE_MINUTE;
        symbol = "min";
    } else {
        factor = 1;
        symbol = "s";
    }
    return new Preformatted(value / factor, " " + symbol);
}

export function render(value: number, formatter: Formatter): string {
    if (value < 0) {
        return "-" + render(Math.abs(value), formatter);
    }
    if ([0, 1].includes(value)) {
        return formatter.format_zero_or_one(value).trim();
    }
    if (value < 1) {
        return formatter.format_small_number(value).trim();
    }
    // value > 1
    return formatter.format_large_number(value).trim();
}
