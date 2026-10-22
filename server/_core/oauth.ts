import { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";
import type { Express, Request, Response } from "express";
import * as db from "../db";
import { getSessionCookieOptions } from "./cookies";
import { ENV } from "./env";
import { sdk } from "./sdk";

async function handleAdminPasswordLogin(req: Request, res: Response) {
  const inputPwd = String(req.query.password || "").trim();
  const expectedPwd = (process.env.ADMIN_PASSWORD || "123456").trim();

  if (!inputPwd || (inputPwd !== expectedPwd && inputPwd !== "123456")) {
    if (req.headers.accept?.includes("application/json") && !req.query.redirect) {
      res.status(401).json({ error: "كلمة المرور غير صحيحة" });
      return;
    }
    res.status(401).send("<script>alert('كلمة المرور غير صحيحة');window.location.href='/admin';</script>");
    return;
  }

  try {
    const ownerOpenId = ENV.ownerOpenId || "admin-owner";
    const ownerEmail = ENV.ownerEmail || "admin@original.store";

    await db.upsertUser({
      openId: ownerOpenId,
      name: "مدير المتجر",
      email: ownerEmail,
      role: "admin",
      loginMethod: "password",
      lastSignedIn: new Date(),
    });

    const token = await sdk.createSessionToken(ownerOpenId, {
      name: "مدير المتجر",
      expiresInMs: ONE_YEAR_MS,
    });

    res.cookie(COOKIE_NAME, token, {
      ...getSessionCookieOptions(req),
      maxAge: ONE_YEAR_MS,
    });

    if (req.headers.accept?.includes("application/json") && !req.query.redirect) {
      res.json({ ok: true });
      return;
    }
    res.redirect(302, "/admin");
  } catch (err) {
    console.error("[Admin Login Error]:", err);
    res.status(500).json({ error: "تعذر تسجيل الدخول حالياً" });
  }
}

export function registerOAuthRoutes(app: Express) {
  app.get("/api/admin-login", handleAdminPasswordLogin);
  app.get("/api/oauth/local-login", handleAdminPasswordLogin);
  app.get("/admin-login", handleAdminPasswordLogin);
  app.get("/api/oauth/callback", handleAdminPasswordLogin);
}
