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
  const cand = path.resolve(process.cwd(), "dist", "public");
  const distPath = fs.existsSync(cand) ? cand : path.resolve(import.meta.dirname, "public");
  const assetsDir = path.join(distPath, "assets");
  const indexPath = path.resolve(distPath, "index.html");
  let cachedIndexGzip: Buffer | null = null;
  let cachedIndexRaw = "";
  const gzipCache = new Map<string, Buffer>();

  app.use("/assets", (req, res) => {
    const reqBase = path.basename(req.path);
    let fp = path.join(assetsDir, reqBase);
    let isFallback = false;
    if (!fs.existsSync(fp)) {
      const m = reqBase.match(/^([a-zA-Z0-9_]+)-[a-zA-Z0-9_-]+(\.(?:js|css))$/);
      const found = m && fs.existsSync(assetsDir) ? fs.readdirSync(assetsDir).find(f => f.startsWith(m[1] + "-") && f.endsWith(m[2])) : null;
      if (!found) return res.status(404).end();
      fp = path.join(assetsDir, found);
      isFallback = true;
    }
    const isJs = fp.endsWith(".js");
    const isCss = fp.endsWith(".css");
    if (!isJs && !isCss) return res.sendFile(fp);
    const ct = isJs ? "application/javascript; charset=utf-8" : "text/css; charset=utf-8";
    const cc = isFallback ? "no-cache" : "public, max-age=31536000, immutable";
    if (!String(req.headers["accept-encoding"] || "").includes("gzip")) {
      res.set({ "Content-Type": ct, "Cache-Control": cc });
      return res.sendFile(fp);
    }
    let gz = gzipCache.get(fp);
    if (!gz) {
      gz = zlib.gzipSync(fs.readFileSync(fp), { level: zlib.constants.Z_BEST_SPEED });
      gzipCache.set(fp, gz);
    }
    res.set({ "Content-Type": ct, "Content-Encoding": "gzip", "Cache-Control": cc, "Vary": "Accept-Encoding" });
    return res.send(gz);
  });

  const sendFastIndex = (req: express.Request, res: express.Response) => {
    try {
      if (!cachedIndexRaw && fs.existsSync(indexPath)) {
        cachedIndexRaw = fs.readFileSync(indexPath, "utf-8");
        cachedIndexGzip = zlib.gzipSync(Buffer.from(cachedIndexRaw), { level: zlib.constants.Z_BEST_SPEED });
      }
      if (cachedIndexRaw) {
        if (String(req.headers["accept-encoding"] || "").includes("gzip") && cachedIndexGzip) {
          res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Content-Encoding": "gzip", "Cache-Control": "no-store", "Vary": "Accept-Encoding" }).send(cachedIndexGzip);
          return;
        }
        res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" }).send(cachedIndexRaw);
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
