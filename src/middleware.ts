import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // Handle CORS
  const response = NextResponse.next();

  response.headers.set("Access-Control-Allow-Origin", "*");
  response.headers.set(
    "Access-Control-Allow-Methods",
    "GET, POST, PUT, DELETE, OPTIONS"
  );
  response.headers.set(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization"
  );

  // Handle uploads
  if (request.nextUrl.pathname.startsWith("/api/process")) {
    const contentType = request.headers.get("content-type");
    if (!contentType?.includes("multipart/form-data")) {
      return new NextResponse("Invalid content type", { status: 400 });
    }
  }

  return response;
}

export const config = {
  matcher: "/api/:path*",
};
