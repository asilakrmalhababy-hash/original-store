export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

export const startLogin = async () => {
  const pwd = window.prompt("أدخل كلمة مرور المدير للدخول إلى لوحة التحكم:");
  if (!pwd) return;

  try {
    const res = await fetch("/api/admin-login", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password: pwd.trim() }),
    });

    const data = await res.json().catch(() => null);
    if (!res.ok || data?.error) {
      window.alert(data?.error || "تعذر تسجيل الدخول");
      return;
    }

    window.location.href = "/admin";
  } catch {
    window.alert("تعذر الاتصال بالخادم. تحقق من اتصال الإنترنت وحاول مجددًا.");
  }
};
