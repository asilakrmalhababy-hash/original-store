import "dotenv/config";
import express from "express";
import { createServer } from "http";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { publicPlatformScript } from "./publicConfig";
import { appRouter } from "../routers";
import { getDb } from "../db";
import { storeSettings } from "../../drizzle/schema";
import { eq } from "drizzle-orm";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";

async function startServer() {
  const app = express();
  const server = createServer(app);
  // Configure body parser with larger size limit for file uploads
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));
  app.get("/api/health", (_req, res) => res.json({ status: "ok" }));
  const publicBrand = async () => {
    try {
      const db = await getDb();
      if (!db) return { name: "ORIGINAL – أوريجنال", icon: "" };
      const rows = await db.select({ key: storeSettings.key, value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeIconUrl")).limit(1);
      const nameRows = await db.select({ value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeName")).limit(1);
      const candidate = rows[0]?.value ?? "";
      const icon = candidate.startsWith("/manus-storage/") || candidate.startsWith("https://") ? candidate : "";
      return { name: nameRows[0]?.value || "ORIGINAL – أوريجنال", icon };
    } catch {
      return { name: "ORIGINAL – أوريجنال", icon: "" };
    }
  };
  app.get("/api/app-manifest.webmanifest", async (_req, res) => {
    const brand = await publicBrand();
    const imagePath = brand.icon ? new URL(brand.icon, "https://app.invalid").pathname : "";
    const type = imagePath.endsWith(".png") ? "image/png" : imagePath.endsWith(".jpg") || imagePath.endsWith(".jpeg") ? "image/jpeg" : imagePath.endsWith(".webp") ? "image/webp" : "image/svg+xml";
    const icons = brand.icon ? [{ src: brand.icon, sizes: "any", type, purpose: "any" }] : [
      { src: "/app-icon-192-v2.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/app-icon-512-v2.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
    ];
    res.set("Cache-Control", "no-store").type("application/manifest+json").send(JSON.stringify({ id: "/", name: brand.name, short_name: "أوريجنال", description: "متجر ORIGINAL – أوريجنال", lang: "ar", dir: "rtl", start_url: "/", scope: "/", display: "standalone", background_color: "#f8f8f2", theme_color: "#174b36", icons }));
  });
  app.get("/api/store-icon", async (_req, res) => {
    const brand = await publicBrand();
    res.set("Cache-Control", "no-store").redirect(302, brand.icon || "/app-icon-180-v2.png");
  });
  app.get("/api/platform/config.js", (_req, res) => {
    res.set("Cache-Control", "no-store").type("application/javascript").send(publicPlatformScript());
  });
  registerOAuthRoutes(app);
  // tRPC API
  app.use(
    "/api/trpc",
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );
  // development mode uses Vite, production mode uses static files
  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  const port = Number(process.env.PORT || "3000");
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid PORT");
  server.on("error", error => { console.error("Server failed:", error.message); process.exit(1); });
  server.listen(port, "0.0.0.0", () => console.log(`Server listening on port ${port}`));
}

startServer().catch(error => { console.error(error); process.exit(1); });
