export interface CMKAjaxReponse<Result> {
    result_code: 0 | 1;
    result: Result;
    serverity: "success" | "error";
}
