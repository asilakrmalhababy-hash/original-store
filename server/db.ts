import { and, eq, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import mysql from "mysql2/promise";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from "./_core/env";
import { isConfiguredOwnerEmail } from "./_core/owner";

let _db: ReturnType<typeof drizzle> | null = null;
let _pool: mysql.Pool | null = null;
const _userCache = new Map<string, { exp: number; user: any }>();

function createFreshPool() {
  if (!process.env.DATABASE_URL) return null;
  const cleanUrl = process.env.DATABASE_URL.split("?")[0];
  return mysql.createPool({
    uri: cleanUrl,
    ssl: { rejectUnauthorized: true },
    waitForConnections: true,
    connectionLimit: 6,
    maxIdle: 1,
    idleTimeout: 10000,
    connectTimeout: 5000,
    enableKeepAlive: true,
    keepAliveInitialDelay: 3000,
  });
}

export function resetDbPool() {
  try { _pool?.end().catch(() => {}); } catch {}
  _pool = createFreshPool();
  _db = _pool ? drizzle(_pool) : null;
  return _db;
}

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      resetDbPool();
    } catch (error) {
      console.warn("[Database] Failed to connect:", error instanceof Error ? error.message : "unknown error");
      _db = null;
    }
  }
  return _db;
}

// Background keep-alive & auto-heal every 20s so dead NAT sockets are replaced before any user request hits them
setInterval(async () => {
  if (!_pool) return;
  let timer: NodeJS.Timeout | null = null;
  try {
    await Promise.race([
      _pool.query("SELECT 1"),
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("DB ping timeout")), 4500); }),
    ]);
  } catch {
    resetDbPool();
  } finally {
    if (timer) clearTimeout(timer);
  }
}, 20000).unref();

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) throw new Error("User openId is required for upsert");
  const db = await getDb();
  if (!db) throw new Error("Database is not available");

  const ownerByOpenId = Boolean(ENV.ownerOpenId && user.openId === ENV.ownerOpenId);
  const ownerByEmail = isConfiguredOwnerEmail(user.email, ENV.ownerEmail);
  const trustedOwner = ownerByOpenId || ownerByEmail;
  const values: InsertUser = { openId: user.openId, role: trustedOwner ? "admin" : "user" };
  if (user.name !== undefined) values.name = user.name;
  if (user.email !== undefined) values.email = user.email?.trim().toLowerCase() ?? null;
  if (user.loginMethod !== undefined) values.loginMethod = user.loginMethod;
  if (user.lastSignedIn !== undefined) values.lastSignedIn = user.lastSignedIn;

  const updates: Partial<InsertUser> = {
    ...(user.name !== undefined ? { name: user.name } : {}),
    ...(user.email !== undefined ? { email: user.email?.trim().toLowerCase() ?? null } : {}),
    ...(user.loginMethod !== undefined ? { loginMethod: user.loginMethod } : {}),
    ...(user.lastSignedIn !== undefined ? { lastSignedIn: user.lastSignedIn } : {}),
    ...(trustedOwner ? { role: "admin" as const, suspended: false } : {}),
  };

  await db.insert(users).values(values).onDuplicateKeyUpdate({
    set: updates,
  });
  _userCache.delete(user.openId);
}

export async function getUserByOpenId(openId: string) {
  const now = Date.now();
  const cached = _userCache.get(openId);
  if (cached) {
    if (cached.exp <= now) {
      getDb().then(db => db?.select().from(users).where(eq(users.openId, openId)).limit(1))
        .then(res => { if (res?.[0]) _userCache.set(openId, { exp: Date.now() + 600_000, user: res[0] }); })
        .catch(() => {});
    }
    return cached.user;
  }
  const db = await getDb();
  if (!db) return undefined;
  try {
    const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
    const user = result[0];
    if (user) _userCache.set(openId, { exp: now + 600_000, user });
    return user;
  } catch {
    return undefined;
  }
}

export async function promoteConfiguredOwner(openId: string, email: string | null | undefined) {
  const ownerEmail = ENV.ownerEmail;
  if (!openId || !isConfiguredOwnerEmail(email, ownerEmail)) return undefined;

  const db = await getDb();
  if (!db) throw new Error("Database is not available");

  await db.update(users)
    .set({ role: "admin", suspended: false })
    .where(and(
      eq(users.openId, openId),
      sql`lower(trim(${users.email})) = ${ownerEmail}`,
    ));
  _userCache.delete(openId);
  return getUserByOpenId(openId);
}
