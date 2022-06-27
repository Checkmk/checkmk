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
    static _BASE: number = 1000;
    static _PREFIXES: string[] = ["", "k", "M", "G", "T", "P", "E", "Z", "Y"];
}

export class IECUnitPrefixes extends UnitPrefixes {
    static _BASE: number = 1024;
    static _PREFIXES: string[] = [
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

export function drop_dotzero(value, digits = 2) {
    return value.toFixed(digits).replace(/\.0+$/, "");
}

export function fmt_number_with_precision(
    v,
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
    b,
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

export function fmt_nic_speed(speed) {
    const speedi = parseInt(speed);
    if (isNaN(speedi)) return speed;

    return fmt_number_with_precision(speedi, SIUnitPrefixes, 2, false, "bit/s");
}

export function percent(perc, scientific_notation = false) {
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

export function scientific(v, precision) {
    if (v == 0) return "0";
    if (v < 0) return "-" + scientific(-1 * v, precision);

    let [mantissa, exponent] = frexpb(v, 10);
    if (-3 <= exponent && exponent <= 4) {
        return v.toFixed(
            Math.min(precision, Math.max(0, precision - exponent))
        );
    }
    return v.toExponetial(precision);
}

export function calculate_physical_precision(v, precision) {
    if (v == 0) return ["", precision - 1, 1];

    let [_mantissa, exponent] = frexpb(v, 10);

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

    const scale_symbols = {
        "-5": "f",
        "-4": "p",
        "-3": "n",
        "-2": "µ",
        "-1": "m",
        0: "",
        1: "k",
        2: "M",
        3: "G",
        4: "T",
        5: "P",
    };

    return [scale_symbols[scale], places_after_comma, 1000 ** scale];
}

export function physical_precision(v, precision, unit_symbol) {
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

export function frexpb(x, base) {
    let exp = Math.floor(Math.log(x) / Math.log(base));
    let mantissa = x / base ** exp;
    if (mantissa < 1) {
        mantissa *= base;
        exp -= 1;
    }
    return [mantissa, exp];
}

export function approx_age(secs) {
    if (secs < 0) return approx_age(-1 * secs);

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
export function domainIntervals(stepping) {
    if (stepping === "binary") return [1, 2, 4, 8, 16];
    return [1, 2, 5, 10];
}

function tickStep(range, ticks, increments) {
    const base = increments[increments.length - 1];
    const [mantissa, exp] = frexpb(range / ticks, base);
    return increments.find(e => mantissa <= e) * base ** exp;
}

export function partitionableDomain(domain, ticks, increments) {
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
