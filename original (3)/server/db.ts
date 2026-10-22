import { and, eq, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from "./_core/env";
import { isConfiguredOwnerEmail } from "./_core/owner";

let _db: ReturnType<typeof drizzle> | null = null;

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error instanceof Error ? error.message : "unknown error");
      _db = null;
    }
  }
  return _db;
}

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
    // Never downgrade an existing owner on an ordinary session refresh. Promotion
    // remains exclusively tied to a server-configured Manus identity.
    ...(trustedOwner ? { role: "admin" as const, suspended: false } : {}),
  };

  await db.insert(users).values(values).onDuplicateKeyUpdate({
    set: updates,
  });
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
  return result[0];
}

/** Promote only the currently authenticated account whose stored OAuth email matches OWNER_EMAIL. */
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

  return getUserByOpenId(openId);
}
