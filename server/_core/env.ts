export const ENV = {
  get appId() { return process.env.MANUS_PROJECT_ID || "original-store"; },
  get cookieSecret() { return process.env.MANUS_JWT_SECRET || "secret_token_123456789_abcdef_32_chars"; },
  get databaseUrl() { return process.env.DATABASE_URL || ""; },
  get oAuthServerUrl() { return process.env.MANUS_OAUTH_API_URL || ""; },
  get ownerOpenId() { return process.env.OWNER_OPEN_ID?.trim() || "admin-owner"; },
  get ownerEmail() { return process.env.OWNER_EMAIL?.trim().toLowerCase() || "admin@original.store"; },
  get isProduction() { return process.env.NODE_ENV === "production"; },
  get forgeApiUrl() { return process.env.MANUS_API_URL || ""; },
  get forgeApiKey() { return process.env.MANUS_API_KEY || ""; },
};
