export interface CMKAjaxReponse<Result> {
    result_code: 0 | 1;
    result: Result;
    severity: "success" | "error";
}

export type PartialK<T, K extends PropertyKey = PropertyKey> = Partial<
    Pick<T, Extract<keyof T, K>>
> &
    Omit<T, K> extends infer O
    ? {[P in keyof O]: O[P]}
    : never;

export interface PlotDefinition {
    id: string;
    color: string;
    plot_type: string;
    label: string;
    use_tags: string[];
    hidden: boolean;
    is_scalar: boolean;
    metric?: {
        bounds: Record<string, number>;
        unit: Record<string, string>;
    };
}
