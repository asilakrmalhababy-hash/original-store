export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

export const startLogin = async () => {
  const pwd = window.prompt("أدخل كلمة مرور المدير للدخول إلى لوحة التحكم:");
  if (!pwd) return;
  try {
    const res = await fetch(`/api/admin-login?password=${encodeURIComponent(pwd.trim())}`, {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    const data = await res.json().catch(() => null);
    if (!res.ok || data?.error) {
      window.alert(data?.error || "كلمة المرور غير صحيحة");
      return;
    }
    window.location.href = "/admin";
  } catch {
    window.location.href = `/api/admin-login?password=${encodeURIComponent(pwd.trim())}&redirect=1`;
  }
};
