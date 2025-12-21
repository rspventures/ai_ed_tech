/**
 * Image Compression Utility
 * Resizes and compresses images client-side before upload
 */

const MAX_WIDTH = 1024;
const MAX_HEIGHT = 1024;
const QUALITY = 0.8;

/**
 * Compress and resize an image file to reduce payload size
 * @param file - The image file to compress
 * @param maxWidth - Maximum width (default 1024)
 * @param maxHeight - Maximum height (default 1024)
 * @param quality - JPEG quality 0-1 (default 0.8)
 * @returns Promise resolving to base64 string
 */
export async function compressImage(
    file: File,
    maxWidth: number = MAX_WIDTH,
    maxHeight: number = MAX_HEIGHT,
    quality: number = QUALITY
): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (e) => {
            const img = new Image();

            img.onload = () => {
                // Calculate new dimensions
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxHeight) {
                    const ratio = Math.min(maxWidth / width, maxHeight / height);
                    width = Math.round(width * ratio);
                    height = Math.round(height * ratio);
                }

                // Create canvas and draw resized image
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                    reject(new Error('Could not get canvas context'));
                    return;
                }

                ctx.drawImage(img, 0, 0, width, height);

                // Convert to base64
                const base64 = canvas.toDataURL('image/jpeg', quality);
                resolve(base64);
            };

            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = e.target?.result as string;
        };

        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
    });
}

/**
 * Check if a file is an image
 */
export function isImageFile(file: File): boolean {
    return file.type.startsWith('image/');
}

/**
 * Get file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default compressImage;
