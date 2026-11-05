import zlib from "zlib";
import express, { type Express } from "express";
import fs from "fs";
import { type Server } from "http";
import { nanoid } from "nanoid";
import path from "path";
import { createServer as createViteServer } from "vite";
import viteConfig from "../../vite.config";

export async function setupVite(app: Express, server: Server) {
  const serverOptions = {
    middlewareMode: true,
    hmr: { server },
    allowedHosts: true as const,
  };

  const vite = await createViteServer({
    ...viteConfig,
    configFile: false,
    server: serverOptions,
    appType: "custom",
  });

  app.use(vite.middlewares);
  app.use("*", async (req, res, next) => {
    const url = req.originalUrl;

    try {
      const clientTemplate = path.resolve(
        import.meta.dirname,
        "../..",
        "client",
        "index.html"
      );

      let template = await fs.promises.readFile(clientTemplate, "utf-8");
      template = template.replace(
        "src=\"/src/main.tsx\"",
        "src=\"/src/main.tsx?v=" + nanoid() + "\""
      );
      const page = await vite.transformIndexHtml(url, template);
      res.status(200).set({ "Content-Type": "text/html" }).end(page);
    } catch (e) {
      vite.ssrFixStacktrace(e as Error);
      next(e);
    }
  });
}

export function serveStatic(app: Express) {
  const distPath =
    process.env.NODE_ENV === "development"
      ? path.resolve(import.meta.dirname, "../..", "dist", "public")
      : path.resolve(import.meta.dirname, "public");
  const indexPath = path.resolve(distPath, "index.html");
  let cachedIndexGzip: Buffer | null = null;
  let cachedIndexRaw = "";
  const gzipAssetCache = new Map<string, { buf: Buffer; ct: string }>();

  app.use("/assets", (req, res, next) => {
    if (!String(req.headers["accept-encoding"] || "").includes("gzip")) return next();
    if (!req.path.endsWith(".js") && !req.path.endsWith(".css")) return next();
    let hit = gzipAssetCache.get(req.path);
    if (!hit) {
      const fp = path.join(distPath, "assets", path.basename(req.path));
      if (!fs.existsSync(fp)) return next();
      hit = {
        buf: zlib.gzipSync(fs.readFileSync(fp), { level: zlib.constants.Z_BEST_SPEED }),
        ct: req.path.endsWith(".js") ? "application/javascript; charset=utf-8" : "text/css; charset=utf-8",
      };
      gzipAssetCache.set(req.path, hit);
    }
    res.set({ "Content-Type": hit.ct, "Content-Encoding": "gzip", "Cache-Control": "public, max-age=31536000, immutable", "Vary": "Accept-Encoding" });
    return res.send(hit.buf);
  });

  let lastHydratedTime = 0;
  let cachedHydratedGzip: Buffer | null = null;
  let cachedHydratedRaw = "";
  const sendFastIndex = (req: express.Request, res: express.Response) => {
    try {
      if (!cachedIndexRaw && fs.existsSync(indexPath)) {
        cachedIndexRaw = fs.readFileSync(indexPath, "utf-8");
        cachedIndexGzip = zlib.gzipSync(Buffer.from(cachedIndexRaw), { level: zlib.constants.Z_BEST_SPEED });
      }
      if (cachedIndexRaw) {
        const g = globalThis as any;
        if (g.__fastHomeData && g.__fastHomeTime !== lastHydratedTime) {
          const sj = JSON.stringify(g.__fastHomeData).replace(/</g, "\u003c").replace(/>/g, "\u003e");
          if (sj.length < 250000) {
            cachedHydratedRaw = cachedIndexRaw.replace("</head>", "<script>window.__INITIAL_CATALOG__=" + sj + ";</script></head>");
            cachedHydratedGzip = zlib.gzipSync(Buffer.from(cachedHydratedRaw), { level: zlib.constants.Z_BEST_SPEED });
            lastHydratedTime = g.__fastHomeTime || 1;
          }
        }
        const rawOut = cachedHydratedRaw || cachedIndexRaw;
        const gzOut = cachedHydratedGzip || cachedIndexGzip;
        if (String(req.headers["accept-encoding"] || "").includes("gzip") && gzOut) {
          res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Content-Encoding": "gzip", "Cache-Control": "no-cache", "Vary": "Accept-Encoding" }).send(gzOut);
          return;
        }
        res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }).send(rawOut);
        return;
      }
    } catch {}
    res.sendFile(indexPath);
  };

  app.get("/", sendFastIndex);
  app.get("/index.html", sendFastIndex);
  app.use(express.static(distPath, { index: false, maxAge: "1y", immutable: true }));
  app.use("*", sendFastIndex);
}
