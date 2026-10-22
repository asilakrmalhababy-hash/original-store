import fs from "node:fs";
import { and, eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import mysql from "mysql2/promise";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from "./_core/env";
import { isConfiguredOwnerEmail } from "./_core/owner";

let activeDb: ReturnType<typeof drizzle> | null = null;
let setupTask: Promise<void> | null = null;

export function resetDbPool() {
  activeDb = null;
  setupTask = null;
}

async function createWorkingPool(): Promise<mysql.Pool> {
  const raw = (process.env.DATABASE_URL || "")
    .replace(/^DATABASE_URL\s*=\s*/i, "")
    .replace(/^["'`]+|["'`]+$/g, "")
    .trim()
    .split("?")[0]
    .trim();

  if (raw.startsWith("mysql://") && raw.includes("@")) {
    try {
      const u = new URL(raw);
      const remotePool = mysql.createPool({
        host: u.hostname,
        port: Number(u.port || 4000),
        user: decodeURIComponent(u.username),
        password: decodeURIComponent(u.password),
        database: u.pathname.replace(/^\//, "") || "test",
        waitForConnections: true,
        connectionLimit: 5,
        connectTimeout: 8000,
        ssl: u.hostname === "127.0.0.1" || u.hostname === "localhost"
          ? undefined
          : { minVersion: "TLSv1.2", rejectUnauthorized: false },
      });
      await remotePool.query("SELECT 1");
      console.log("[DB] Connected to remote DATABASE_URL:", u.hostname);
      return remotePool;
    } catch (err: any) {
      console.warn("[DB] Remote DATABASE_URL rejected, switching to embedded MariaDB:", err?.message);
    }
  }

  const localPool = mysql.createPool({
    host: "127.0.0.1",
    port: 3306,
    user: "root",
    database: "test",
    waitForConnections: true,
    connectionLimit: 5,
  });
  await localPool.query("SELECT 1");
  console.log("[DB] Connected to embedded MariaDB on 127.0.0.1:3306");
  return localPool;
}

async function initializeSchemaAndSeed(pool: mysql.Pool) {
  const sqlFiles = [
    "drizzle/0000_initial_users.sql",
    "drizzle/0001_original_store.sql",
    "drizzle/0002_grey_baron_zemo.sql",
  ];
  for (const file of sqlFiles) {
    if (!fs.existsSync(file)) continue;
    const parts = fs.readFileSync(file, "utf8").split("--> statement-breakpoint");
    for (const stmt of parts) {
      const s = stmt.trim();
      if (s) await pool.query(s).catch(() => {});
    }
  }

  await pool.query(`CREATE TABLE IF NOT EXISTS owner_push_subscriptions (
    id int AUTO_INCREMENT PRIMARY KEY,
    userId int NOT NULL,
    endpointHash varchar(64) NOT NULL,
    encryptedPayload text NOT NULL,
    createdAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY owner_push_user_endpoint_uq (userId, endpointHash)
  )`).catch(() => {});

  await pool.query(`CREATE TABLE IF NOT EXISTS customer_push_subscriptions (
    id int AUTO_INCREMENT PRIMARY KEY,
    orderId int NOT NULL,
    endpointHash varchar(64) NOT NULL,
    encryptedPayload text NOT NULL,
    createdAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY customer_push_order_endpoint_uq (orderId, endpointHash)
  )`).catch(() => {});

  await pool.query(
    "INSERT IGNORE INTO store_settings (`key`, `value`) VALUES ('deliveryEnabled', 'true'), ('deliveryFee', '0'), ('storeName', 'ORIGINAL – أوريجنال'), ('currency', 'ر.ي')"
  ).catch(() => {});

  const [prodRows]: any = await pool.query("SELECT COUNT(*) as cnt FROM products").catch(() => [[{ cnt: 0 }]]);
  if (Number(prodRows?.[0]?.cnt ?? 0) === 0) {
    await pool.query(
      "INSERT IGNORE INTO categories (id, name, slug, color, isActive, sortOrder) VALUES (1, 'المواد الغذائية الأساسية', 'essentials', '#397a54', true, 1), (2, 'المعلبات والبقوليات', 'canned', '#2d6a4f', true, 2), (3, 'البهارات والزيوت', 'spices-oils', '#40916c', true, 3)"
    ).catch(() => {});
    await pool.query(`INSERT IGNORE INTO products (id, name, slug, description, categoryId, price, unit, stock, minQuantity, quantityStep, isPublished, isAvailable, sortOrder) VALUES
      (1, 'أرز بسمتي فاخر 5 كيلو', 'basmati-rice-5kg', 'أرز بسمتي طويل الحبة للكبسة والمندي', 1, 4500, 'كيس', 50, 1, 1, true, true, 1),
      (2, 'تونة الغويزي 185 جرام', 'tuna-ghuwaizi', 'تونة يمنية فاخرة بالزيت النباتي', 2, 950, 'علبة', 100, 1, 1, true, true, 2),
      (3, 'فاصوليا حمراء مطبوخة', 'red-beans-can', 'فاصوليا جاهزة للكشنة والقلابة اليمنية', 2, 500, 'علبة', 80, 1, 1, true, true, 3),
      (4, 'معجون طماطم مركز', 'tomato-paste', 'صلصة طماطم طبيعية مركزة للتسبيك', 2, 350, 'علبة', 120, 1, 1, true, true, 4),
      (5, 'زيت طبخ نقي 1.5 لتر', 'cooking-oil-1-5l', 'زيت نباتي صافي للطبخ والقلي', 3, 1800, 'عبوة', 60, 1, 1, true, true, 5),
      (6, 'حوائج وبهارات مرق يمنية', 'yemeni-maraq-spices', 'تشكيلة حوائج يمنية أصيلة للمرق والسلتة', 3, 600, 'عبوة', 90, 1, 1, true, true, 6),
      (7, 'قشطة التاج فاخرة', 'cream-taj', 'قشطة غنية للحلويات والمعصوب اليمني', 2, 650, 'علبة', 70, 1, 1, true, true, 7),
      (8, 'عسل يمني طبيعي', 'yemeni-honey', 'عسل يمني صافي للتحلية والفطور', 1, 3500, 'عبوة', 30, 1, 1, true, true, 8)
    `).catch(() => {});
  }
}

export async function getDb() {
  if (!activeDb) {
    setupTask = (async () => {
      const pool = await createWorkingPool();
      await initializeSchemaAndSeed(pool);
      activeDb = drizzle(pool);
    })();
  }
  if (setupTask) {
    await setupTask.catch(err => console.error("[DB Setup Error]:", err));
  }
  return activeDb;
}

export async function upsertUser(u: InsertUser): Promise<void> {
  const db = await getDb();
  if (!db || !u.openId) return;
  const isOwner = Boolean(ENV.ownerOpenId && u.openId === ENV.ownerOpenId) || isConfiguredOwnerEmail(u.email, ENV.ownerEmail);
  const row: InsertUser = {
    openId: u.openId,
    role: isOwner ? "admin" : "user",
    name: u.name,
    email: u.email?.trim().toLowerCase() ?? null,
    loginMethod: u.loginMethod,
    lastSignedIn: u.lastSignedIn,
  };
  await db.insert(users).values(row).onDuplicateKeyUpdate({ set: row });
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const rows = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
  return rows[0];
}

export async function promoteConfiguredOwner(openId: string, email: string | null | undefined) {
  if (!openId || !isConfiguredOwnerEmail(email, ENV.ownerEmail)) return undefined;
  const db = await getDb();
  if (!db) return undefined;
  await db.update(users).set({ role: "admin", suspended: false }).where(and(eq(users.openId, openId)));
  return getUserByOpenId(openId);
}
