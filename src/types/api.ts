export interface ApiResponse<T = any> {
    success: boolean;
    message?: string;
    data?: T;
}

export interface ProcessResponse extends ApiResponse {
    data?: {
        filename: string;
        result: string;
    };
}

export interface ReportResponse extends ApiResponse {
    content?: string;
}

export interface ProcessRequestBody {
    file: File;
    primaryEmails: string[];
    ccEmails: string[];
}
