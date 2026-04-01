import { AxiosError } from "axios";

export interface SystemError {
  code: string;
  message: string;
  detail?: string;
  status?: number;
}

export function mapAPIError(error: unknown): SystemError {
  if (error && typeof error === "object" && "isAxiosError" in error) {
    const axiosErr = error as AxiosError<any>;
    const status = axiosErr.response?.status;
    const detail = axiosErr.response?.data?.detail;

    switch (status) {
      case 400:
        return {
          code: "BAD_REQUEST",
          message: "The request payload parameters are invalid or corrupted.",
          detail,
          status,
        };
      case 401:
        return {
          code: "UNAUTHORIZED",
          message: "Your login session has expired. Please sign in again.",
          detail,
          status,
        };
      case 403:
        return {
          code: "FORBIDDEN",
          message: "You do not have administrative privileges to perform this operation.",
          detail,
          status,
        };
      case 404:
        return {
          code: "NOT_FOUND",
          message: "The requested resource record could not be found.",
          detail,
          status,
        };
      case 422:
        return {
          code: "UNPROCESSABLE_ENTITY",
          message: "Field validation failed. Please check input formats.",
          detail,
          status,
        };
      case 429:
        return {
          code: "TOO_MANY_REQUESTS",
          message: "Rate limit threshold exceeded. Please retry shortly.",
          detail,
          status,
        };
      case 500:
      case 502:
      case 503:
      case 504:
        return {
          code: "SERVER_ERROR",
          message: "A central microservice error occurred. Our engineers have been alerted.",
          detail,
          status,
        };
      default:
        break;
    }
  }

  // Generic fallback error
  const err = error as Error | undefined;
  return {
    code: "UNKNOWN_ERROR",
    message: err?.message || "An unexpected network communication error occurred.",
  };
}
export default mapAPIError;
