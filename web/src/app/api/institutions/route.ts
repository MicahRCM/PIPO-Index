import { NextResponse } from "next/server";
import { getInstitutions } from "@/lib/data";
import type { ApiResponse, Institution } from "@/lib/types";

/**
 * GET /api/institutions
 * Returns all normalized institutions. Optional `?q=` filters by name
 * (case-insensitive substring) so clients can do server-side search later.
 */
export async function GET(request: Request): Promise<NextResponse<ApiResponse<Institution[]>>> {
  const all = await getInstitutions();
  const q = new URL(request.url).searchParams.get("q")?.trim().toLowerCase();
  const data = q ? all.filter((i) => i.name.toLowerCase().includes(q)) : all;

  return NextResponse.json({
    data,
    meta: { count: data.length, generatedAt: new Date().toISOString() },
  });
}
