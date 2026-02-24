/* ──────────────────────────────────────────────────────────────
 *  File upload helpers — category detection and validation
 * ────────────────────────────────────────────────────────────── */

const IMAGE_EXTS = ["png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "tif", "svg", "dicom", "dcm"];
const AUDIO_EXTS = ["mp3", "wav", "ogg", "m4a", "aac", "flac", "webm", "wma"];
const DOCUMENT_EXTS = ["pdf", "txt", "doc", "docx"];

/** Max file size in bytes (50 MB) */
export const MAX_FILE_SIZE = 50 * 1024 * 1024;

function fileExtension(file: File): string {
  return file.name.split(".").pop()?.toLowerCase() ?? "";
}

export type FileCategory = "image" | "audio" | "document";

/** Categorise a file by its extension / MIME type */
export function getFileCategory(file: File): FileCategory {
  const ext = fileExtension(file);
  if (IMAGE_EXTS.includes(ext) || file.type.startsWith("image/")) return "image";
  if (AUDIO_EXTS.includes(ext) || file.type.startsWith("audio/")) return "audio";
  return "document";
}

/** Check if file extension is in any allowed category */
export function isAllowedFile(file: File): boolean {
  const ext = fileExtension(file);
  return (
    IMAGE_EXTS.includes(ext) ||
    AUDIO_EXTS.includes(ext) ||
    DOCUMENT_EXTS.includes(ext) ||
    file.type.startsWith("image/") ||
    file.type.startsWith("audio/") ||
    file.type === "application/pdf" ||
    file.type === "text/plain"
  );
}

/** Human-readable file size */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Accepted MIME string for the file input (all categories) */
export const ACCEPT_ALL = "image/*,audio/*,.pdf,.txt,.doc,.docx";
export const ACCEPT_IMAGE = "image/*,.dcm,.dicom";
export const ACCEPT_AUDIO = "audio/*";
export const ACCEPT_DOCUMENT = ".pdf,.txt,.doc,.docx";
