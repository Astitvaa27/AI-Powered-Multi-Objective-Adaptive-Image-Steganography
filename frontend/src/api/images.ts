import { downloadFile, request, requestBlob } from "./client";
import type { ImageRecord, Paginated } from "./types";


export function listImages(params?: {
  limit?: number;
  offset?: number;
  image_type?: string;
}): Promise<Paginated<ImageRecord>> {
  return request<Paginated<ImageRecord>>("/images", { params });
}

export function getImage(imageId: string): Promise<ImageRecord> {
  return request<ImageRecord>(`/images/${imageId}`);
}

export function uploadImage(
  file: File,
  imageType: "COVER" | "SUSPECT" | "STEGO" = "COVER",
): Promise<ImageRecord> {
  const formData = new FormData();
  formData.append("file", file);

  return request<ImageRecord>("/images/upload", {
    method: "POST",
    formData,
    params: { image_type: imageType },
  });
}

/** Register a file that already lives under the storage directory. */
export function registerImagePath(
  storagePath: string,
  imageType: "COVER" | "SUSPECT" | "STEGO" = "SUSPECT",
): Promise<ImageRecord> {
  return request<ImageRecord>("/images/register-path", {
    method: "POST",
    params: { storage_path: storagePath, image_type: imageType },
  });
}

/**
 * Image bytes are behind bearer auth and PGM/TIFF sources are
 * transcoded server-side, so previews load as object URLs.
 */
export function loadImageObjectUrl(imageId: string): Promise<string> {
  return requestBlob(`/images/${imageId}/file`);
}

export function downloadImage(
  imageId: string,
  filename: string,
): Promise<void> {
  return downloadFile(`/images/${imageId}/file`, filename);
}