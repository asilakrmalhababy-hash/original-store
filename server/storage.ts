import { createHash } from "node:crypto";

export async function uploadToCloudinary(
  dataUrl: string,
  folder = "original-store/product",
): Promise<string> {
  const cloudName = (process.env.CLOUDINARY_CLOUD_NAME || "").trim();
  const apiKey = (process.env.CLOUDINARY_API_KEY || "").trim();
  const apiSecret = (process.env.CLOUDINARY_API_SECRET || "").trim();
  if (!cloudName || !apiKey || !apiSecret) {
    return dataUrl;
  }
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const cleanFolder = folder.replace(/^\/+|\/+$/g, "");
  const toSign = `folder=${cleanFolder}&timestamp=${timestamp}${apiSecret}`;
  const signature = createHash("sha1").update(toSign).digest("hex");

  const body = new URLSearchParams();
  body.set("file", dataUrl);
  body.set("api_key", apiKey);
  body.set("timestamp", timestamp);
  body.set("folder", cleanFolder);
  body.set("signature", signature);

  const res = await fetch(`https://api.cloudinary.com/v1_1/${cloudName}/image/upload`, {
    method: "POST",
    body,
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => "");
    throw new Error(`Cloudinary upload failed (${res.status}): ${errText.slice(0, 180)}`);
  }
  const json: any = await res.json();
  if (!json?.secure_url) {
    throw new Error("Cloudinary returned no secure_url");
  }
  return String(json.secure_url);
}

export async function storagePut(
  relKey: string,
  data: Buffer | Uint8Array | string,
  contentType = "image/webp",
): Promise<{ key: string; url: string }> {
  const b64 = typeof data === "string" ? Buffer.from(data).toString("base64") : Buffer.from(data).toString("base64");
  const dataUrl = `data:${contentType};base64,${b64}`;
  const url = await uploadToCloudinary(dataUrl, "original-store/uploads");
  return { key: relKey, url };
}
