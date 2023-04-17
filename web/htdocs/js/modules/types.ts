export interface CMKAjaxReponse<Result> {
    result_code: 0 | 1;
    result: Result;
    serverity: "success" | "error";
}

export type PartialK<T, K extends PropertyKey = PropertyKey> = Partial<
    Pick<T, Extract<keyof T, K>>
> &
    Omit<T, K> extends infer O
    ? {[P in keyof O]: O[P]}
    : never;
