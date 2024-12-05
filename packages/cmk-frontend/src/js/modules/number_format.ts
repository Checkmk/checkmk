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
    unit = "",
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
    unit = "B",
) {
    return fmt_number_with_precision(
        b,
        unit_prefix_type,
        precision,
        false,
        unit,
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
            Math.min(precision, Math.max(0, precision - exponent)),
        );
    }
    return v.toExponential(precision);
}

export function calculate_physical_precision(
    v: number,
    precision: number,
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
    unit_symbol: string,
): string {
    if (v < 0) return "-" + physical_precision(-1 * v, precision, unit_symbol);
    const [symbol, places_after_comma, factor] = calculate_physical_precision(
        v,
        precision,
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
    increments: number[],
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

const MAX_DIGITS = 5;

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
    prefix: string;
    symbol: string;

    constructor(value: number, prefix: string, symbol: string) {
        this.value = value;
        this.prefix = prefix;
        this.symbol = symbol;
    }
}

class Formatted {
    text: string;
    prefix: string;
    symbol: string;

    constructor(text: string, prefix: string, symbol: string) {
        this.text = text;
        this.prefix = prefix;
        this.symbol = symbol;
    }
}

abstract class NotationFormatter {
    symbol: string;
    precision: AutoPrecision | StrictPrecision;

    constructor(symbol: string, precision: AutoPrecision | StrictPrecision) {
        this.symbol = symbol;
        this.precision = precision;
    }

    protected abstract preformat_small_number(value: number): Preformatted[];
    protected abstract preformat_large_number(value: number): Preformatted[];

    protected apply_precision(value: number): number {
        const value_floor = Math.floor(value);
        if (value == value_floor) {
            return value;
        }
        let digits = this.precision.digits;
        if (this.precision instanceof AutoPrecision) {
            const exponent = Math.abs(
                Math.ceil(Math.log10(value - value_floor)),
            );
            if (exponent > 0) {
                digits = Math.max(exponent + 1, this.precision.digits);
            }
        }
        return parseFloat(value.toFixed(Math.min(digits, MAX_DIGITS)));
    }

    protected preformat(value: number): Preformatted[] {
        if ([0, 1].includes(value)) {
            return [new Preformatted(value, "", this.symbol)];
        }
        if (value < 1) {
            return this.preformat_small_number(value);
        }
        // value > 1
        return this.preformat_large_number(value);
    }

    protected abstract compose(formatted: Formatted): string;

    protected postformat(formatted_parts: Preformatted[]): string {
        const results: string[] = [];
        let text;
        for (const formatted of formatted_parts) {
            text = String(this.apply_precision(formatted.value));
            if (text.includes(".")) {
                text = sanitize(text);
            }
            results.push(
                this.compose(
                    new Formatted(text, formatted.prefix, formatted.symbol),
                ).trim(),
            );
        }
        return results.join(" ");
    }

    public render(value: number): string {
        let sign;
        if (value < 0) {
            sign = "-";
        } else {
            sign = "";
        }
        return sign + this.postformat(this.preformat(value));
    }
}

export class DecimalFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
        return [new Preformatted(value, "", this.symbol)];
    }

    protected preformat_large_number(value: number): Preformatted[] {
        return [new Preformatted(value, "", this.symbol)];
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + " " + formatted.symbol;
    }
}

export class SIFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
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
        return [new Preformatted(value * factor, prefix, this.symbol)];
    }

    protected preformat_large_number(value: number): Preformatted[] {
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
        return [new Preformatted(value / factor, prefix, this.symbol)];
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + " " + formatted.prefix + formatted.symbol;
    }
}

export class IECFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
        return [new Preformatted(value, "", this.symbol)];
    }

    protected preformat_large_number(value: number): Preformatted[] {
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
        return [new Preformatted(value / factor, prefix, this.symbol)];
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + " " + formatted.prefix + formatted.symbol;
    }
}

export class StandardScientificFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
        const exponent = Math.floor(Math.log10(value));
        return [
            new Preformatted(
                value / Math.pow(10, exponent),
                "e" + exponent,
                this.symbol,
            ),
        ];
    }

    protected preformat_large_number(value: number): Preformatted[] {
        const exponent = Math.floor(Math.log10(value));
        return [
            new Preformatted(
                value / Math.pow(10, exponent),
                "e+" + exponent,
                this.symbol,
            ),
        ];
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + formatted.prefix + " " + formatted.symbol;
    }
}

export class EngineeringScientificFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
        const exponent = Math.floor(Math.log10(value) / 3) * 3;
        return [
            new Preformatted(
                value / Math.pow(10, exponent),
                "e" + exponent,
                this.symbol,
            ),
        ];
    }

    protected preformat_large_number(value: number): Preformatted[] {
        const exponent = Math.floor(Math.log10(10000) / 3) * 3;
        return [
            new Preformatted(
                value / Math.pow(10, exponent),
                "e+" + exponent,
                this.symbol,
            ),
        ];
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + formatted.prefix + " " + formatted.symbol;
    }
}

const _ONE_DAY = 86400;
const _ONE_HOUR = 3600;
const _ONE_MINUTE = 60;

class TimeLargeSymbol {
    factor: number;
    symbol: string;

    constructor(factor: number, symbol: string) {
        this.factor = factor;
        this.symbol = symbol;
    }
}

const _TIME_LARGE_SYMBOLS: TimeLargeSymbol[] = [
    new TimeLargeSymbol(_ONE_DAY, "d"),
    new TimeLargeSymbol(_ONE_HOUR, "h"),
    new TimeLargeSymbol(_ONE_MINUTE, "min"),
];

export class TimeFormatter extends NotationFormatter {
    protected preformat_small_number(value: number): Preformatted[] {
        const exponent = Math.floor(Math.log10(value)) - 1;
        let factor: number;
        let prefix: string;
        if (exponent <= -6) {
            factor = Math.pow(1000, 2);
            prefix = "µ";
        } else if (exponent <= -3) {
            factor = 1000;
            prefix = "m";
        } else {
            factor = 1;
            prefix = "";
        }
        return [new Preformatted(value * factor, prefix, this.symbol)];
    }

    protected preformat_large_number(value: number): Preformatted[] {
        let use_symbol = "";
        for (const time_large_symbol of _TIME_LARGE_SYMBOLS) {
            if (value >= time_large_symbol.factor) {
                use_symbol = time_large_symbol.symbol;
                break;
            }
        }
        const rounded_value = parseFloat(value.toFixed(0));
        const formatted_parts: Preformatted[] = [];
        let days;
        let hours;
        let minutes;
        let seconds;
        switch (use_symbol) {
            case "d": {
                days = Math.floor(rounded_value / _ONE_DAY);
                formatted_parts.push(new Preformatted(days, "", "d"));
                hours = parseFloat(
                    ((rounded_value - days * _ONE_DAY) / _ONE_HOUR).toFixed(),
                );
                if (days < 10 && hours > 0) {
                    formatted_parts.push(new Preformatted(hours, "", "h"));
                }
                break;
            }
            case "h": {
                hours = Math.floor(rounded_value / _ONE_HOUR);
                formatted_parts.push(new Preformatted(hours, "", "h"));
                minutes = parseFloat(
                    (
                        (rounded_value - hours * _ONE_HOUR) /
                        _ONE_MINUTE
                    ).toFixed(),
                );
                if (minutes > 0) {
                    formatted_parts.push(new Preformatted(minutes, "", "min"));
                }
                break;
            }
            case "min": {
                minutes = Math.floor(rounded_value / _ONE_MINUTE);
                formatted_parts.push(new Preformatted(minutes, "", "min"));
                seconds = parseFloat(
                    (rounded_value - minutes * _ONE_MINUTE).toFixed(),
                );
                if (seconds > 0) {
                    formatted_parts.push(new Preformatted(seconds, "", "s"));
                }
                break;
            }
            default: {
                formatted_parts.push(new Preformatted(value, "", "s"));
            }
        }
        return formatted_parts;
    }

    protected compose(formatted: Formatted): string {
        return formatted.text + " " + formatted.prefix + formatted.symbol;
    }
}
