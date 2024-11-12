import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

interface RouteParams {
  params: {
    type: string;
    filename: string;
  };
}

export async function GET(
  request: NextRequest,
  context: RouteParams
): Promise<NextResponse> {
  try {
    // Await the params to ensure they're accessed asynchronously
    const params = await Promise.resolve(context.params);
    const { type, filename } = params;

    // Validate type parameter
    if (!['md', 'txt'].includes(type)) {
      return NextResponse.json(
        { success: false, message: 'Invalid report type' },
        { status: 400 }
      );
    }

    // Validate filename to prevent directory traversal
    if (filename.includes('..') || !filename.match(/^[a-zA-Z0-9_\-\.]+$/)) {
      return NextResponse.json(
        { success: false, message: 'Invalid filename' },
        { status: 400 }
      );
    }

    const outputDir = path.join(process.cwd(), 'data', 'output');
    const filePath = path.join(outputDir, filename);

    try {
      const content = await readFile(filePath, 'utf-8');
      
      // Set appropriate content type and disposition headers
      const contentType = type === 'md' ? 'text/markdown' : 'text/plain';
      
      return new NextResponse(content, {
        headers: {
          'Content-Type': contentType,
          'Content-Disposition': `inline; filename="${filename}"`,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
    } catch (error) {
      console.error('File read error:', error);
      return NextResponse.json(
        { success: false, message: 'Report not found' },
        { status: 404 }
      );
    }
  } catch (error) {
    console.error('Error fetching report:', error);
    return NextResponse.json(
      { 
        success: false, 
        message: error instanceof Error ? error.message : 'Failed to fetch report' 
      },
      { status: 500 }
    );
  }
}