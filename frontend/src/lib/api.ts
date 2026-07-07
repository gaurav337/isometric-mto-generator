import { MTOResponse, UploadResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadDrawing(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

export async function getMTOResult(jobId: string): Promise<MTOResponse> {
  const response = await fetch(`${API_BASE_URL}/api/mto/${jobId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to fetch MTO result with status ${response.status}`);
  }

  return response.json();
}

export function getMtoCsvUrl(jobId: string): string {
  return `${API_BASE_URL}/api/mto/${jobId}/csv`;
}
