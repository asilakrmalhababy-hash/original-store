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
  if (!fs.existsSync(distPath)) {
    console.error(
      "Could not find the build directory: " + distPath + ", make sure to build the client first"
    );
  }

  const indexPath = path.resolve(distPath, "index.html");
  let cachedIndexHtml = "";
  try {
    if (fs.existsSync(indexPath)) {
      cachedIndexHtml = fs.readFileSync(indexPath, "utf-8");
    }
  } catch {}

  const sendHydratedIndex = async (_req: express.Request, res: express.Response) => {
    try {
      if (!cachedIndexHtml && fs.existsSync(indexPath)) {
        cachedIndexHtml = fs.readFileSync(indexPath, "utf-8");
      }
      if (cachedIndexHtml) {
        const g = globalThis as any;
        if (!g.__fastHomeData && typeof g.__loadCatalogHome === "function") {
          try { await Promise.race([g.__loadCatalogHome(), new Promise(r => setTimeout(r, 900))]); } catch {}
        }
        if (g.__fastHomeData) {
          const safeJson = JSON.stringify(g.__fastHomeData)
            .replace(/</g, "\\u003c")
            .replace(/>/g, "\\u003e")
            .replace(/\u2028/g, "\\u2028")
            .replace(/\u2029/g, "\\u2029");
          const hydrated = cachedIndexHtml.replace(
            "</head>",
            "<script>window.__INITIAL_CATALOG__=" + safeJson + ";</script></head>"
          );
          res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }).send(hydrated);
          return;
        }
        res.status(200).set({ "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" }).send(cachedIndexHtml);
        return;
      }
    } catch {}
    res.sendFile(indexPath);
  };

  app.get("/", sendHydratedIndex);
  app.get("/index.html", sendHydratedIndex);
  app.use(express.static(distPath, { index: false }));
  app.use("*", sendHydratedIndex);
}
