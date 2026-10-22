import {
  createCipheriv,
  createDecipheriv,
  createECDH,
  createHash,
  hkdfSync,
  randomBytes,
} from "node:crypto";
import {
  sendNotification,
  setVapidDetails,
  type PushSubscription,
} from "web-push";
import { ENV } from "./env";

export type ProtectedPushSubscription = {
  endpointHash: string;
  encryptedPayload: string;
};

export type PushMessage = {
  title: string;
  body: string;
  url: string;
  tag: string;
};

let cachedKeys: { publicKey: string; privateKey: string } | undefined;
let vapidConfigured = false;

function deriveSecret(salt: string, info: string): Buffer {
  if (!ENV.cookieSecret) throw new Error("Web Push signing is unavailable");
  return Buffer.from(hkdfSync(
    "sha256",
    Buffer.from(ENV.cookieSecret, "utf8"),
    Buffer.from(salt, "utf8"),
    Buffer.from(info, "utf8"),
    32,
  ));
}

function getVapidKeys() {
  if (cachedKeys) return cachedKeys;
  for (let attempt = 0; attempt < 8; attempt += 1) {
    const privateBytes = deriveSecret("original-web-push-v1", `vapid-p256-${attempt}`);
    try {
      const ecdh = createECDH("prime256v1");
      ecdh.setPrivateKey(privateBytes);
      cachedKeys = {
        publicKey: ecdh.getPublicKey(undefined, "uncompressed").toString("base64url"),
        privateKey: privateBytes.toString("base64url"),
      };
      return cachedKeys;
    } catch {
      // An HKDF output outside the P-256 scalar range is discarded and re-derived.
    }
  }
  throw new Error("Web Push signing is unavailable");
}

export function getWebPushPublicKey() {
  return getVapidKeys().publicKey;
}

function configureVapid() {
  if (vapidConfigured) return;
  const keys = getVapidKeys();
  setVapidDetails("https://original-myavc6ud.manus.space", keys.publicKey, keys.privateKey);
  vapidConfigured = true;
}

export function isAllowedPushEndpoint(value: string) {
  try {
    const endpoint = new URL(value);
    const host = endpoint.hostname.toLowerCase();
    const trustedHost = host === "fcm.googleapis.com"
      || host === "updates.push.services.mozilla.com"
      || host.endsWith(".push.services.mozilla.com")
      || host === "web.push.apple.com"
      || host.endsWith(".push.apple.com")
      || host.endsWith(".notify.windows.com");
    return endpoint.protocol === "https:"
      && !endpoint.username
      && !endpoint.password
      && (!endpoint.port || endpoint.port === "443")
      && trustedHost;
  } catch {
    return false;
  }
}

export function protectPushSubscription(subscription: PushSubscription): ProtectedPushSubscription {
  if (!isAllowedPushEndpoint(subscription.endpoint)) throw new Error("Unsupported push endpoint");
  const endpointHash = createHash("sha256").update(subscription.endpoint).digest("hex");
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", deriveSecret("original-web-push-v1", "subscription-encryption"), iv);
  const ciphertext = Buffer.concat([
    cipher.update(JSON.stringify({ endpoint: subscription.endpoint, keys: subscription.keys }), "utf8"),
    cipher.final(),
  ]);
  const encryptedPayload = `v1.${Buffer.concat([iv, cipher.getAuthTag(), ciphertext]).toString("base64url")}`;
  return { endpointHash, encryptedPayload };
}

export function unprotectPushSubscription(encryptedPayload: string): PushSubscription {
  if (!encryptedPayload.startsWith("v1.")) throw new Error("Unsupported stored push subscription");
  const packed = Buffer.from(encryptedPayload.slice(3), "base64url");
  if (packed.length < 29) throw new Error("Invalid stored push subscription");
  const iv = packed.subarray(0, 12);
  const authTag = packed.subarray(12, 28);
  const ciphertext = packed.subarray(28);
  const decipher = createDecipheriv("aes-256-gcm", deriveSecret("original-web-push-v1", "subscription-encryption"), iv);
  decipher.setAuthTag(authTag);
  const decoded = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString("utf8");
  const subscription = JSON.parse(decoded) as PushSubscription;
  if (!subscription.endpoint || !subscription.keys?.p256dh || !subscription.keys?.auth || !isAllowedPushEndpoint(subscription.endpoint)) {
    throw new Error("Invalid stored push subscription");
  }
  return subscription;
}

export async function sendWebPush(subscription: PushSubscription, message: PushMessage) {
  configureVapid();
  return sendNotification(subscription, JSON.stringify(message), {
    TTL: 60 * 60 * 24,
    urgency: "high",
  });
}
