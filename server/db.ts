import { and, eq, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import mysql from "mysql2/promise";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from "./_core/env";
import { isConfiguredOwnerEmail } from "./_core/owner";

let _db: ReturnType<typeof drizzle> | null = null;
let _initPromise: Promise<void> | null = null;

export function resetDbPool() {
  _db = null;
  _initPromise = null;
}

function getDatabaseUrl(): string {
  return (process.env.DATABASE_URL || "")
    .replace(/^DATABASE_URL\s*=\s*/i, "")
    .replace(/^["'`]+|["'`]+$/g, "")
    .trim()
    .split("?")[0]
    .trim();
}

function isRetryable(err: any): boolean {
  const m = String(err?.message || err?.cause?.message || "").toLowerCase();
  const c = String(err?.code || err?.cause?.code || "").toUpperCase();
  return (
    ["PROTOCOL_CONNECTION_LOST", "ECONNRESET", "ETIMEDOUT", "EPIPE"].includes(c) ||
    m.includes("connection lost") ||
    m.includes("closed state") ||
    m.includes("econnreset")
  );
}

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      const cleanUrl = getDatabaseUrl();
      const parsed = new URL(cleanUrl);
      const pool = mysql.createPool({
        host: parsed.hostname,
        port: Number(parsed.port || 4000),
        user: decodeURIComponent(parsed.username),
        password: decodeURIComponent(parsed.password),
        database: parsed.pathname.replace(/^\//, "") || "test",
        waitForConnections: true,
        connectionLimit: 5,
        maxIdle: 0,
        idleTimeout: 10000,
        enableKeepAlive: true,
        keepAliveInitialDelay: 5000,
        connectTimeout: 20000,
        ssl: { minVersion: "TLSv1.2", rejectUnauthorized: false },
      });

      const oq = pool.query.bind(pool);
      (pool as any).query = async (...a: any[]) => {
        try {
          return await (oq as any)(...a);
        } catch (e) {
          if (isRetryable(e)) return await (oq as any)(...a);
          throw e;
        }
      };

      const oe = pool.execute.bind(pool);
      (pool as any).execute = async (...a: any[]) => {
        try {
          return await (oe as any)(...a);
        } catch (e) {
          if (isRetryable(e)) return await (oe as any)(...a);
          throw e;
        }
      };

      _db = drizzle(pool);

      _initPromise = (async () => {
        try {
          await pool.query(
            "CREATE TABLE IF NOT EXISTS `store_settings` (`key` varchar(100) NOT NULL PRIMARY KEY, `value` text NOT NULL, `updatedAt` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)"
          );
          await pool.query(
            "INSERT IGNORE INTO `store_settings` (`key`, `value`) VALUES ('deliveryEnabled', 'true'), ('deliveryFee', '0')"
          );
        } catch (initErr) {
          console.error("[Database Init Error]:", initErr);
        }
      })();
    } catch (error) {
      console.error("[Database] Failed to connect:", error);
      _db = null;
    }
  }

  if (_initPromise) {
    await _initPromise;
  }

  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) throw new Error("User openId is required for upsert");
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  const trustedOwner =
    Boolean(ENV.ownerOpenId && user.openId === ENV.ownerOpenId) ||
    isConfiguredOwnerEmail(user.email, ENV.ownerEmail);
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
  await db.insert(users).values(values).onDuplicateKeyUpdate({ set: updates });
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
  return result[0];
}

export async function promoteConfiguredOwner(openId: string, email: string | null | undefined) {
  if (!openId || !isConfiguredOwnerEmail(email, ENV.ownerEmail)) return undefined;
  const db = await getDb();
  if (!db) throw new Error("Database is not available");
  await db.update(users).set({ role: "admin", suspended: false }).where(and(eq(users.openId, openId), sql`1=1`));
  return getUserByOpenId(openId);
}
