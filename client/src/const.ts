export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

export const startLogin = () => {
  const pwd = window.prompt("أدخل كلمة مرور الإدارة:");
  if (!pwd) return;
  window.location.href = `/api/admin-login?password=${encodeURIComponent(pwd.trim())}`;
};
