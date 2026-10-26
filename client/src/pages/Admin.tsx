import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "wouter";
import {
  AlertTriangle, ArrowLeft, BadgePercent, BellRing, Box, Check, ChevronDown, CircleUserRound, ClipboardList,
  ImagePlus, LayoutDashboard, Leaf, LoaderCircle, LogOut, Megaphone, Package, Plus, Save,
  Settings2, ShieldCheck, ShoppingBag, SlidersHorizontal, Sparkles, Trash2, Truck, Users, X, Download,
} from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";
import { useAuth } from "@/_core/hooks/useAuth";
import { startLogin, submitAdminCredentials } from "@/const";
import { PERMISSION_KEYS, PERMISSION_LABELS, ROLE_DEFINITIONS, type AdminRoleKey, type PermissionKey } from "@shared/rbac";
import ImageEditor from "@/components/ImageEditor";
import { ensureBrowserPushSubscription, getExistingBrowserPushSubscription, getPushPermissionState, requestPushPermission } from "@/lib/pushNotifications";

const money = (value: number) => `${Number(value || 0).toLocaleString("en-US")} ر.ي`;
const labels: Record<string, string> = { new: "جديد", preparing: "قيد التجهيز", ready: "جاهز للتوصيل", out_for_delivery: "خرج للتوصيل", delivered: "تم التسليم", cancelled: "ملغي" };
type Section = "overview" | "products" | "categories" | "banners" | "offers" | "orders" | "chats" | "users" | "staff" | "settings";
const sections: Array<{ id: Section; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "نظرة عامة", icon: LayoutDashboard },
  { id: "products", label: "المنتجات", icon: Package },
  { id: "categories", label: "الأقسام", icon: SlidersHorizontal },
  { id: "banners", label: "الإعلانات", icon: Megaphone },
  { id: "offers", label: "العروض والخصومات", icon: BadgePercent },
  { id: "orders", label: "الطلبات", icon: ClipboardList },
  { id: "chats", label: "محادثات الزبائن", icon: Sparkles },
  { id: "users", label: "العملاء", icon: Users },
  { id: "staff", label: "المديرون والصلاحيات", icon: ShieldCheck },
  { id: "settings", label: "إعدادات المتجر", icon: Settings2 },
];

function ImageField({ value, onChange, kind, aspect, title }: { value: string; onChange: (value: string) => void; kind: "product" | "category" | "banner" | "icon"; aspect: number; title: string }) {
  const [open, setOpen] = useState(false);
  const latestValRef = useRef(value);
  latestValRef.current = value;
  const upload = trpc.commerce.admin.uploadImage.useMutation({
    onSuccess: (result, vars) => {
      if (latestValRef.current === vars.dataUrl && result?.imageUrl) {
        onChange(result.imageUrl);
      }
    },
    onError: () => {},
  });
  const handleCropSave = (dataUrl: string) => {
    latestValRef.current = dataUrl;
    onChange(dataUrl);
    setOpen(false);
    toast.success("تم اعتماد قص الصورة وتجهيزها للحفظ");
    upload.mutate({ dataUrl, kind });
  };
  return (
    <div className="admin-image-field">
      <div className="admin-image-preview">
        {value ? <img src={value} alt="معاينة الصورة" /> : <span><ImagePlus size={22} /><small>لم تُرفع صورة</small></span>}
      </div>
      <div className="admin-image-buttons">
        <button type="button" className="small-button" onClick={e => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}>
          <ImagePlus size={15} />{value ? "قص / تغيير الصورة" : "رفع وقص صورة"}
        </button>
        {value && (
          <button type="button" className="small-button danger-soft" onClick={e => { e.preventDefault(); e.stopPropagation(); latestValRef.current = ""; onChange(""); }}>
            <X size={14} />إزالة
          </button>
        )}
      </div>
      {open && (
        <ImageEditor
          title={title}
          aspect={aspect}
          format="webp"
          initialSource={value || undefined}
          onCancel={() => setOpen(false)}
          onSave={handleCropSave}
        />
      )}
      {upload.isPending && <small className="upload-status"><LoaderCircle size={14} className="spin" /> جارٍ حفظ الصورة...</small>}
    </div>
  );
}

function AdminLoginGate({ reason, onLogout, onSuccess }: { reason: "login" | "forbidden" | "suspended"; onLogout?: () => void | Promise<void>; onSuccess?: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || busy) return;
    setBusy(true);
    setErrMsg("");
    const res = await submitAdminCredentials(username, password);
    setBusy(false);
    if (!res.ok) {
      setErrMsg(res.error || "بيانات الدخول غير صحيحة.");
      return;
    }
    toast.success("تم تسجيل الدخول بنجاح");
    setPassword("");
    if (onSuccess) onSuccess();
    else window.location.reload();
  };

  if (reason !== "login") {
    const message = reason === "suspended"
      ? "تم إيقاف هذا الحساب الإداري. تواصل مع مالك المتجر."
      : "تم تسجيل دخولك، لكن هذا الحساب غير مخول بصلاحيات الإدارة حالياً.";
    return (
      <main className="admin-gate" dir="rtl">
        <div className="admin-gate-card">
          <span className="admin-gate-mark"><ShieldCheck size={26} /></span>
          <span className="eyebrow">حماية لوحة الإدارة</span>
          <h1>{reason === "suspended" ? "الحساب معطل" : "غير مصرح بالدخول"}</h1>
          <p>{message}</p>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", justifyContent: "center" }}>
            <Link className="button button-outline" href="/">العودة للمتجر</Link>
            {onLogout && <button className="button button-quiet" onClick={() => void onLogout()}>تسجيل الخروج</button>}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="admin-gate" dir="rtl">
      <div className="admin-gate-card" style={{ maxWidth: "430px", textAlign: "right", alignItems: "stretch" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "10px" }}>
          <span className="admin-gate-mark" style={{ margin: 0, width: "46px", height: "46px" }}><ShieldCheck size={24} /></span>
          <div>
            <span className="eyebrow">بوابة الإدارة المحمية</span>
            <h1 style={{ margin: "2px 0 0", fontSize: "20px" }}>تسجيل دخول الإدارة</h1>
          </div>
        </div>
        <p style={{ margin: "0 0 14px", fontSize: "11px" }}>للمالك: اترك اسم المستخدم فارغاً (أو اكتب owner) وأدخل كلمة مرور المالك. للمديرين والموظفين: أدخل اسم المستخدم وكلمة المرور المخصصة لك.</p>
        {errMsg && (
          <div className="admin-error" style={{ marginBottom: "12px", padding: "10px 12px" }}>
            <AlertTriangle size={16} />
            <div><strong>تعذر تسجيل الدخول</strong><small>{errMsg}</small></div>
          </div>
        )}
        <form onSubmit={handleLogin} className="form-stack">
          <label>
            اسم المستخدم أو البريد (اختياري للمالك)
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="owner أو اسم مستخدم الموظف..."
              disabled={busy}
            />
          </label>
          <label>
            كلمة المرور
            <input
              required
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="أدخل كلمة المرور السرية"
              disabled={busy}
            />
          </label>
          <button type="submit" className="button button-primary full-button" disabled={busy || !password}>
            {busy ? <LoaderCircle size={16} className="spin" /> : <ShieldCheck size={16} />}
            {busy ? "جارٍ التحقق..." : "دخول آمن للوحة الإدارة"}
          </button>
        </form>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "14px", paddingTop: "12px", borderTop: "1px solid #ebefe8" }}>
          <Link className="text-link" href="/">العودة لواجهة المتجر</Link>
          <small className="secure-caption" style={{ margin: 0 }}><ShieldCheck size={13} /> محمي بتشفير الخادم</small>
        </div>
      </div>
    </main>
  );
}

function ForcePasswordChangeGate({ displayName, onSuccess, onLogout }: { displayName: string; onSuccess: () => void; onLogout: () => void }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const changeMut = trpc.commerce.admin.staff.changeOwnPassword.useMutation({
    onSuccess: () => {
      toast.success("تم تحديث كلمة المرور بنجاح! مرحباً بك.");
      onSuccess();
    },
    onError: err => toast.error(err.message),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) { toast.error("كلمة المرور الجديدة يجب ألا تقل عن 6 أحرف."); return; }
    if (newPassword !== confirmPassword) { toast.error("كلمتا المرور غير متطابقتين."); return; }
    if (newPassword === currentPassword) { toast.error("يرجى اختيار كلمة مرور جديدة مختلفة عن المؤقتة."); return; }
    changeMut.mutate({ currentPassword, newPassword });
  };

  return (
    <main className="admin-gate" dir="rtl">
      <div className="admin-gate-card" style={{ maxWidth: "430px", textAlign: "right", alignItems: "stretch" }}>
        <span className="eyebrow">إجراء أمني إلزامي</span>
        <h1 style={{ fontSize: "20px", margin: "4px 0 8px" }}>تغيير كلمة المرور المؤقتة</h1>
        <p style={{ margin: "0 0 14px", fontSize: "11px" }}>مرحباً {displayName}، لحماية حسابك الإداري يجب تعيين كلمة مرور خاصة بك قبل المتابعة إلى لوحة الإدارة.</p>
        <form onSubmit={submit} className="form-stack">
          <label>كلمة المرور المؤقتة (الحالية)<input required type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} /></label>
          <label>كلمة المرور الجديدة (6 أحرف على الأقل)<input required type="password" minLength={6} value={newPassword} onChange={e => setNewPassword(e.target.value)} /></label>
          <label>تأكيد كلمة المرور الجديدة<input required type="password" minLength={6} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} /></label>
          <button type="submit" className="button button-primary full-button" disabled={changeMut.isPending}>
            {changeMut.isPending ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
            حفظ كلمة المرور الجديدة والمتابعة
          </button>
          <button type="button" className="button button-quiet full-button" onClick={onLogout}>تسجيل الخروج</button>
        </form>
      </div>
    </main>
  );
}

function Overview() {
  const query = trpc.commerce.admin.overview.useQuery(undefined, { retry: 1, refetchOnWindowFocus: false });
  if (query.isLoading) return <AdminLoading />;
  if (query.error) return <AdminError message={query.error.message} retry={() => void query.refetch()} />;
  const data = query.data!;
  return <div className="admin-content"><div className="admin-page-heading"><div><span className="eyebrow">لوحة المالك</span><h1>أهلاً بك في أوريجنال</h1><p>ابدأ بإعداد متجرك، وأضف محتواه عندما تكون جاهزًا.</p></div><span className="admin-heading-mark"><Leaf size={27} /></span></div><div className="admin-stat-grid">{[
    { label: "المنتجات", value: data.products, icon: Package }, { label: "الأقسام", value: data.categories, icon: Box }, { label: "كل الطلبات", value: data.orders, icon: ClipboardList }, { label: "العملاء", value: data.customers, icon: Users }, { label: "طلبات قيد المتابعة", value: data.openOrders, icon: Truck }, { label: "قيمة الطلبات غير الملغاة", value: data.orderValue, display: money(data.orderValue), icon: BadgePercent },
  ].map(item => { const Icon = item.icon; return <div className="admin-stat" key={item.label}><span><Icon size={18} /></span><small>{item.label}</small><strong>{"display" in item ? item.display : item.value.toLocaleString("en-US")}</strong><em>من بيانات المتجر</em></div>; })}</div>
    <div className="admin-welcome-panel"><div className="welcome-ornament"><span>O</span><i /></div><div><span className="eyebrow">الخطوة الأولى</span><h2>متجرك يبدأ من اختياراتك</h2><p>تحكم بمنتجاتك وأقسامك وطلبات العملاء بسهولة.</p><Link href="/admin/products" className="button button-primary">إضافة أول منتج<ArrowLeft size={16} /></Link></div></div>
    <div className="admin-section-heading"><div><h2>آخر الطلبات</h2><p>تظهر الطلبات هنا بعد أن يرسلها العملاء.</p></div><Link href="/admin/orders" className="small-button">إدارة الطلبات<ArrowLeft size={15} /></Link></div>
    {!data.recentOrders.length ? <div className="admin-empty"><ClipboardList size={22} /><strong>لا توجد طلبات بعد</strong><span>تأكد من إعداد التوصيل قبل فتح الطلبات.</span></div> : <div className="admin-order-table">{data.recentOrders.map(order => <div className="admin-order-row" key={order.id}><span className="order-number">{order.orderNumber}</span><span>{order.recipientName}</span><span>{new Date(order.createdAt).toLocaleDateString("ar-YE")}</span><b>{money(order.total)}</b><span className={`status-pill status-${order.status}`}>{labels[order.status]}</span></div>)}</div>}
  </div>;
}

type ProductFormState = { name: string; description: string; imageUrl: string; categoryId: number | null; price: string; unit: string; stock: string; minQuantity: string; quantityStep: string; isPublished: boolean; isAvailable: boolean; sortOrder: string };
const blankProduct: ProductFormState = { name: "", description: "", imageUrl: "", categoryId: null, price: "", unit: "حبة", stock: "", minQuantity: "1", quantityStep: "1", isPublished: true, isAvailable: true, sortOrder: "0" };

function ProductsPanel() {
  const utils = trpc.useUtils();
  const [form, setForm] = useState(blankProduct);
  const [editing, setEditing] = useState<number | null>(null);
  const [recommended, setRecommended] = useState<number | null>(null);
  const [recommendedIds, setRecommendedIds] = useState<number[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [catFilter, setCatFilter] = useState<string>("all");
  const [pubFilter, setPubFilter] = useState<"all" | "published" | "hidden">("all");

  const refreshCatalog = async () => Promise.all([
    utils.commerce.catalog.home.invalidate(),
    utils.commerce.catalog.listProducts.invalidate(),
    utils.commerce.catalog.listCategories.invalidate(),
    utils.commerce.catalog.product.invalidate(),
  ]);

  const query = trpc.commerce.admin.products.list.useQuery(undefined, { retry: 1 });
  const cats = trpc.commerce.admin.categories.list.useQuery(undefined, { retry: 1 });

  const create = trpc.commerce.admin.products.create.useMutation({
    onSuccess: async () => {
      toast.success("تمت إضافة المنتج بنجاح");
      setForm(blankProduct);
      await Promise.all([utils.commerce.admin.products.list.invalidate(), utils.commerce.admin.overview.invalidate(), refreshCatalog()]);
    },
    onError: error => toast.error(error.message),
  });

  const update = trpc.commerce.admin.products.update.useMutation({
    onSuccess: async () => {
      toast.success("تم حفظ تعديلات المنتج بنجاح");
      setEditing(null);
      setForm(blankProduct);
      await Promise.all([utils.commerce.admin.products.list.invalidate(), refreshCatalog()]);
    },
    onError: error => toast.error(error.message),
  });

  const toggleVisibility = trpc.commerce.admin.products.update.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success(vars.values.isPublished ? "تم إظهار ونشر المنتج في المتجر" : "تم إخفاء المنتج عن الواجهة");
      await Promise.all([utils.commerce.admin.products.list.invalidate(), refreshCatalog()]);
    },
    onError: error => toast.error(error.message),
  });

  const deleteProduct = trpc.commerce.admin.products.delete.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success("تم حذف المنتج نهائياً");
      if (editing === vars.id) { setEditing(null); setForm(blankProduct); }
      await Promise.all([utils.commerce.admin.products.list.invalidate(), utils.commerce.admin.overview.invalidate(), refreshCatalog()]);
    },
    onError: error => toast.error(error.message),
  });

  const saveRecommendations = trpc.commerce.admin.products.setRecommendations.useMutation({
    onSuccess: async () => {
      toast.success("تم تحديث المنتجات المشابهة المقترحة");
      setRecommended(null);
      await utils.commerce.catalog.product.invalidate();
    },
    onError: error => toast.error(error.message),
  });

  const setField = <K extends keyof ProductFormState>(key: K, value: ProductFormState[K]) => setForm(current => ({ ...current, [key]: value }));

  const selectEdit = (item: NonNullable<typeof query.data>[number]) => {
    setEditing(item.id);
    setForm({
      name: item.name,
      description: item.description ?? "",
      imageUrl: item.imageUrl ?? "",
      categoryId: item.categoryId,
      price: String(item.price),
      unit: item.unit,
      stock: item.stock === null ? "" : String(item.stock),
      minQuantity: String(item.minQuantity),
      quantityStep: String(item.quantityStep),
      isPublished: item.isPublished,
      isAvailable: item.isAvailable,
      sortOrder: String(item.sortOrder),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const values = {
      name: form.name,
      description: form.description || null,
      imageUrl: form.imageUrl || null,
      categoryId: form.categoryId,
      price: Number(form.price),
      unit: form.unit,
      stock: form.stock === "" ? null : Number(form.stock),
      minQuantity: Number(form.minQuantity),
      quantityStep: Number(form.quantityStep),
      isPublished: form.isPublished,
      isAvailable: form.isAvailable,
      sortOrder: Number(form.sortOrder),
    };
    if (editing) update.mutate({ id: editing, values });
    else create.mutate(values);
  };

  const filteredProducts = (query.data ?? []).filter(item => {
    if (catFilter === "none" && item.categoryId !== null) return false;
    if (catFilter !== "all" && catFilter !== "none" && String(item.categoryId) !== catFilter) return false;
    if (pubFilter === "published" && !item.isPublished) return false;
    if (pubFilter === "hidden" && item.isPublished) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      if (!item.name.toLowerCase().includes(q) && !(item.description || "").toLowerCase().includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="admin-content">
      <div className="admin-page-heading">
        <div><span className="eyebrow">كتالوج متجرك</span><h1>إدارة المنتجات</h1><p>أضف وعدّل واحذف منتجاتك بحرية كاملة مع قص احترافي للصور.</p></div>
        <span className="admin-heading-mark"><Package size={25} /></span>
      </div>
      <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">{editing ? "✳" : "01"}</span>
          <div><h2>{editing ? "تعديل المنتج: " + form.name : "إضافة منتج جديد"}</h2><p>بعد قص الصورة ستظهر هنا فوراً ولن يُحفظ المنتج إلا عند ضغطك على زر الحفظ بالأسفل.</p></div>
          {editing && <button type="button" className="small-button" onClick={() => { setEditing(null); setForm(blankProduct); }}>إلغاء التعديل<X size={14} /></button>}
        </div>
        <form onSubmit={submit} className="admin-form">
          <div className="product-form-layout">
            <div className="form-fields-grid">
              <label className="field-wide">اسم المنتج<input required maxLength={180} value={form.name} onChange={e => setField("name", e.target.value)} placeholder="اكتب اسم المنتج" /></label>
              <label className="field-wide">الوصف<textarea rows={3} value={form.description} onChange={e => setField("description", e.target.value)} placeholder="وصف واضح للمنتج" /></label>
              <label>السعر بالريال اليمني<input required type="number" min="0" value={form.price} onChange={e => setField("price", e.target.value)} placeholder="0" /></label>
              <label>وحدة البيع<input required value={form.unit} onChange={e => setField("unit", e.target.value)} placeholder="حبة، كيلو، عبوة..." /></label>
              <label>القسم<select value={form.categoryId ?? ""} onChange={e => setField("categoryId", e.target.value ? Number(e.target.value) : null)}><option value="">بلا قسم</option>{cats.data?.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
              <label>الكمية المتوفرة<input type="number" min="0" value={form.stock} onChange={e => setField("stock", e.target.value)} placeholder="اتركه فارغًا إذا غير محدد" /></label>
              <label>الحد الأدنى للكمية<input required type="number" min="1" value={form.minQuantity} onChange={e => setField("minQuantity", e.target.value)} /></label>
              <label>خطوة الزيادة<input required type="number" min="1" value={form.quantityStep} onChange={e => setField("quantityStep", e.target.value)} /></label>
              <label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setField("sortOrder", e.target.value)} /></label>
              <label className="toggle-field"><input type="checkbox" checked={form.isPublished} onChange={e => setField("isPublished", e.target.checked)} /> نشر المنتج في المتجر</label>
              <label className="toggle-field"><input type="checkbox" checked={form.isAvailable} onChange={e => setField("isAvailable", e.target.checked)} /> متاح للشراء</label>
            </div>
            <ImageField title="قص وتجهيز صورة المنتج" value={form.imageUrl} onChange={imageUrl => setField("imageUrl", imageUrl)} kind="product" aspect={1} />
          </div>
          <div className="form-submit-row" style={{ gap: "8px" }}>
            <button type="submit" className="button button-primary" disabled={create.isPending || update.isPending}>
              {create.isPending || update.isPending ? <LoaderCircle size={16} className="spin" /> : editing ? <Save size={16} /> : <Plus size={17} />}
              {editing ? "حفظ التعديلات" : "إضافة المنتج"}
            </button>
            {editing && (
              <button type="button" className="button button-quiet" onClick={() => { setEditing(null); setForm(blankProduct); }}>
                إلغاء
              </button>
            )}
          </div>
        </form>
      </section>

      <div className="admin-section-heading">
        <div><h2>كل المنتجات</h2><p>تعديل، إخفاء/نشر، أو حذف نهائي لأي منتج.</p></div>
        <span className="count-chip">{filteredProducts.length} / {query.data?.length ?? 0}</span>
      </div>

      <div className="filter-bar" style={{ marginBottom: "14px" }}>
        <label className="filter-search"><input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="ابحث باسم المنتج..." /></label>
        <label className="filter-select">
          <select value={catFilter} onChange={e => setCatFilter(e.target.value)}>
            <option value="all">كل الأقسام</option>
            <option value="none">بلا قسم</option>
            {cats.data?.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}
          </select>
        </label>
        <label className="filter-select">
          <select value={pubFilter} onChange={e => setPubFilter(e.target.value as any)}>
            <option value="all">كل الحالات</option>
            <option value="published">منشور في المتجر</option>
            <option value="hidden">مخفي / مسودة</option>
          </select>
        </label>
      </div>

      {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !filteredProducts.length ? <AdminEmpty title="لا توجد منتجات مطابقة" text="أضف منتجاً جديداً أو غيّر خيارات البحث والفلترة." /> : (
        <div className="entity-list">
          {filteredProducts.map(item => (
            <article className="entity-row" key={item.id}>
              <div className="entity-image">{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Leaf size={19} />}</div>
              <div className="entity-main">
                <strong>{item.name}</strong>
                <small>{cats.data?.find(cat => cat.id === item.categoryId)?.name || "بلا قسم"} · {item.unit} · {item.stock === null ? "المخزون مفتوح" : "المخزون " + item.stock}</small>
              </div>
              <div className="entity-price">{money(item.price)}</div>
              <span className={"visibility-tag " + (item.isPublished ? "visible" : "hidden")}>{item.isPublished ? "منشور" : "مخفي"}</span>
              <div className="entity-actions">
                <button type="button" className="small-button" onClick={() => selectEdit(item)}>تعديل</button>
                <button
                  type="button"
                  className={"small-button " + (item.isPublished ? "" : "selected")}
                  onClick={() => toggleVisibility.mutate({ id: item.id, values: { isPublished: !item.isPublished, isAvailable: !item.isPublished ? true : item.isAvailable } })}
                >
                  {item.isPublished ? "إخفاء" : "نشر الآن"}
                </button>
                <button type="button" className="small-button" onClick={() => { setRecommended(recommended === item.id ? null : item.id); setRecommendedIds([]); }}>شبيه</button>
                <button
                  type="button"
                  className="small-button danger-soft"
                  onClick={() => {
                    if (window.confirm("هل أنت متأكد من حذف المنتج «" + item.name + "» نهائياً من المتجر؟")) {
                      deleteProduct.mutate({ id: item.id });
                    }
                  }}
                >
                  <Trash2 size={14} /> حذف
                </button>
              </div>
              {recommended === item.id && (
                <div className="recommendation-editor">
                  <strong>اختر منتجات مقترحة تظهر مع «{item.name}»</strong>
                  <div className="recommendation-options">
                    {(query.data ?? []).filter(other => other.id !== item.id).map(other => (
                      <label key={other.id}>
                        <input type="checkbox" checked={recommendedIds.includes(other.id)} onChange={e => setRecommendedIds(current => e.target.checked ? [...current, other.id] : current.filter(id => id !== other.id))} />
                        {other.name}
                      </label>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button type="button" className="small-button selected" onClick={() => saveRecommendations.mutate({ productId: item.id, recommendedIds })}>حفظ التوصيات</button>
                    <button type="button" className="small-button" onClick={() => setRecommended(null)}>إغلاق</button>
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function CategoriesPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.categories.list.useQuery(undefined, { retry: 1 });
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState({ name: "", description: "", imageUrl: "", color: "#397a54", isActive: true, sortOrder: "0" });

  const reset = () => { setEditing(null); setForm({ name: "", description: "", imageUrl: "", color: "#397a54", isActive: true, sortOrder: "0" }); };
  const refreshAll = async () => {
    await Promise.all([
      utils.commerce.admin.categories.list.invalidate(),
      utils.commerce.catalog.home.invalidate(),
      utils.commerce.catalog.listCategories.invalidate(),
      utils.commerce.admin.overview.invalidate(),
    ]);
  };

  const create = trpc.commerce.admin.categories.create.useMutation({
    onSuccess: async () => { toast.success("تم إنشاء القسم بنجاح"); reset(); await refreshAll(); },
    onError: error => toast.error(error.message),
  });
  const update = trpc.commerce.admin.categories.update.useMutation({
    onSuccess: async () => { toast.success("تم تحديث القسم بنجاح"); reset(); await refreshAll(); },
    onError: error => toast.error(error.message),
  });
  const toggleActive = trpc.commerce.admin.categories.update.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success(vars.values.isActive ? "تم تفعيل القسم" : "تم إيقاف القسم مؤقتاً");
      await refreshAll();
    },
    onError: error => toast.error(error.message),
  });
  const deleteCategory = trpc.commerce.admin.categories.delete.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success("تم حذف القسم نهائياً");
      if (editing === vars.id) reset();
      await Promise.all([refreshAll(), utils.commerce.admin.products.list.invalidate()]);
    },
    onError: error => toast.error(error.message),
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const values = { ...form, description: form.description || null, imageUrl: form.imageUrl || null, sortOrder: Number(form.sortOrder) };
    if (editing) update.mutate({ id: editing, values });
    else create.mutate(values);
  };

  return (
    <div className="admin-content">
      <AdminHeading eyebrow="تنظيم المتجر" title="إدارة الأقسام" text="أضف وعدّل واحذف أقسام المتجر وصورها وألوانها وترتيبها بمرونة كاملة." icon={SlidersHorizontal} />
      <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">{editing ? "✳" : "01"}</span>
          <div><h2>{editing ? "تعديل القسم: " + form.name : "إضافة قسم جديد"}</h2><p>أضف الأقسام التي يحتاجها متجرك، ويمكنك تعديلها أو حذفها في أي وقت.</p></div>
          {editing && <button type="button" className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}
        </div>
        <form className="admin-form" onSubmit={submit}>
          <div className="product-form-layout">
            <div className="form-fields-grid">
              <label>اسم القسم<input required maxLength={120} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label>
              <label>لون تعبيري<input type="color" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} /></label>
              <label className="field-wide">وصف (اختياري)<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
              <label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: e.target.value })} /></label>
              <label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> القسم مفعّل في الواجهة</label>
            </div>
            <ImageField title="قص وتجهيز صورة القسم" value={form.imageUrl} onChange={imageUrl => setForm(curr => ({ ...curr, imageUrl }))} kind="category" aspect={4 / 5} />
          </div>
          <div className="form-submit-row" style={{ gap: "8px" }}>
            <button type="submit" className="button button-primary" disabled={create.isPending || update.isPending}>
              {create.isPending || update.isPending ? <LoaderCircle size={16} className="spin" /> : editing ? <Save size={16} /> : <Plus size={16} />}
              {editing ? "حفظ تعديلات القسم" : "إنشاء القسم"}
            </button>
            {editing && <button type="button" className="button button-quiet" onClick={reset}>إلغاء</button>}
          </div>
        </form>
      </section>
      <div className="admin-section-heading">
        <div><h2>أقسام المتجر الحالية</h2><p>يمكنك التعديل أو الإيقاف المؤقت أو الحذف النهائي لأي قسم.</p></div>
        <span className="count-chip">{query.data?.length ?? 0}</span>
      </div>
      {query.isLoading ? <AdminLoading /> : !query.data?.length ? <AdminEmpty title="ابدأ بأول قسم" text="لم تُنشأ أقسام حتى الآن." /> : (
        <div className="entity-list">
          {query.data.map(item => (
            <article className="entity-row" key={item.id}>
              <div className="entity-image" style={{ backgroundColor: item.color + "16", color: item.color }}>{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Leaf size={20} />}</div>
              <div className="entity-main">
                <strong>{item.name}</strong>
                <small>{item.description || "لا يوجد وصف"} · الترتيب {item.sortOrder}</small>
              </div>
              <span className={"visibility-tag " + (item.isActive ? "visible" : "hidden")}>{item.isActive ? "نشط" : "متوقف"}</span>
              <div className="entity-actions">
                <button
                  type="button"
                  className="small-button"
                  onClick={() => {
                    setEditing(item.id);
                    setForm({ name: item.name, description: item.description ?? "", imageUrl: item.imageUrl ?? "", color: item.color, isActive: item.isActive, sortOrder: String(item.sortOrder) });
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  تعديل
                </button>
                <button
                  type="button"
                  className={"small-button " + (item.isActive ? "" : "selected")}
                  onClick={() => toggleActive.mutate({ id: item.id, values: { isActive: !item.isActive } })}
                >
                  {item.isActive ? "إيقاف" : "تفعيل"}
                </button>
                <button
                  type="button"
                  className="small-button danger-soft"
                  onClick={() => {
                    if (window.confirm("هل أنت متأكد من حذف القسم «" + item.name + "» نهائياً؟ (ستبقى المنتجات في المتجر دون حذف).")) {
                      deleteCategory.mutate({ id: item.id });
                    }
                  }}
                >
                  <Trash2 size={14} /> حذف
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

type AdminBannerCfg = {
  placement: "top" | "middle" | "bottom" | "popup";
  size: "auto" | "small" | "medium" | "large";
  clickMode: "full" | "hotspot" | "none";
  hx: number;
  hy: number;
  hw: number;
  hh: number;
  shade: boolean;
  showTitle: boolean;
  showBtn: boolean;
  popupOnce: boolean;
};

const blankBannerCfg: AdminBannerCfg = {
  placement: "top",
  size: "auto",
  clickMode: "full",
  hx: 8,
  hy: 44,
  hw: 34,
  hh: 24,
  shade: false,
  showTitle: false,
  showBtn: false,
  popupOnce: true,
};

function unpackAdminBannerUrl(rawActionUrl?: string | null): { targetUrl: string; cfg: AdminBannerCfg } {
  const raw = String(rawActionUrl || "").trim();
  const marker = "#bcfg=";
  const idx = raw.indexOf(marker);
  if (idx === -1) {
    return { targetUrl: raw, cfg: { ...blankBannerCfg, clickMode: raw ? "full" : "full" } };
  }
  const targetUrl = raw.slice(0, idx).trim();
  try {
    const parsed = JSON.parse(decodeURIComponent(raw.slice(idx + marker.length)));
    return {
      targetUrl,
      cfg: {
        placement: ["top", "middle", "bottom", "popup"].includes(parsed.placement) ? parsed.placement : "top",
        size: ["auto", "small", "medium", "large"].includes(parsed.size) ? parsed.size : "auto",
        clickMode: ["full", "hotspot", "none"].includes(parsed.clickMode) ? parsed.clickMode : "full",
        hx: typeof parsed.hx === "number" ? Math.max(0, Math.min(95, parsed.hx)) : 8,
        hy: typeof parsed.hy === "number" ? Math.max(0, Math.min(95, parsed.hy)) : 44,
        hw: typeof parsed.hw === "number" ? Math.max(5, Math.min(100, parsed.hw)) : 34,
        hh: typeof parsed.hh === "number" ? Math.max(5, Math.min(100, parsed.hh)) : 24,
        shade: Boolean(parsed.shade),
        showTitle: Boolean(parsed.showTitle),
        showBtn: Boolean(parsed.showBtn),
        popupOnce: parsed.popupOnce !== false,
      },
    };
  } catch {
    return { targetUrl, cfg: { ...blankBannerCfg } };
  }
}

function packAdminBannerUrl(targetUrl: string, cfg: AdminBannerCfg): string {
  const cleanTarget = targetUrl.trim();
  return cleanTarget + "#bcfg=" + encodeURIComponent(JSON.stringify(cfg));
}

function BannersPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.banners.list.useQuery(undefined, { retry: 1 });
  const cats = trpc.commerce.admin.categories.list.useQuery(undefined, { retry: 1 });
  const prods = trpc.commerce.admin.products.list.useQuery(undefined, { retry: 1 });

  const blank = { title: "", body: "", imageUrl: "", actionText: "", targetUrl: "/products", isActive: true, sortOrder: "0" };
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState(blank);
  const [cfg, setCfg] = useState<AdminBannerCfg>(blankBannerCfg);
  const [destType, setDestType] = useState<"category" | "product" | "all_products" | "assistant" | "custom">("all_products");

  const stageRef = useRef<HTMLDivElement | null>(null);
  const dragHotRef = useRef<{ mode: "move" | "resize"; startX: number; startY: number; startCfg: AdminBannerCfg; rectW: number; rectH: number } | null>(null);

  const reset = () => {
    setEditing(null);
    setForm(blank);
    setCfg(blankBannerCfg);
    setDestType("all_products");
  };

  const refresh = async () => {
    await Promise.all([utils.commerce.admin.banners.list.invalidate(), utils.commerce.catalog.home.invalidate()]);
  };

  const create = trpc.commerce.admin.banners.create.useMutation({
    onSuccess: async () => { toast.success("تم حفظ الإعلان بنجاح"); reset(); await refresh(); },
    onError: error => toast.error(error.message),
  });
  const update = trpc.commerce.admin.banners.update.useMutation({
    onSuccess: async () => { toast.success("تم تحديث إعدادات الإعلان بنجاح"); reset(); await refresh(); },
    onError: error => toast.error(error.message),
  });
  const remove = trpc.commerce.admin.banners.delete.useMutation({
    onSuccess: () => {
      toast.success("حُذف الإعلان نهائياً");
      void utils.commerce.admin.banners.list.invalidate();
      void utils.commerce.catalog.home.invalidate();
    },
  });

  const startHotspotDrag = (mode: "move" | "resize", e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!stageRef.current) return;
    const r = stageRef.current.getBoundingClientRect();
    if (!r.width || !r.height) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragHotRef.current = { mode, startX: e.clientX, startY: e.clientY, startCfg: { ...cfg }, rectW: r.width, rectH: r.height };
  };

  const moveHotspotDrag = (e: React.PointerEvent) => {
    const d = dragHotRef.current;
    if (!d) return;
    e.preventDefault();
    e.stopPropagation();
    const dx = ((e.clientX - d.startX) / d.rectW) * 100;
    const dy = ((e.clientY - d.startY) / d.rectH) * 100;
    if (d.mode === "move") {
      const nx = Math.round(Math.max(0, Math.min(100 - d.startCfg.hw, d.startCfg.hx + dx)));
      const ny = Math.round(Math.max(0, Math.min(100 - d.startCfg.hh, d.startCfg.hy + dy)));
      setCfg(c => ({ ...c, hx: nx, hy: ny }));
    } else {
      const nw = Math.round(Math.max(8, Math.min(100 - d.startCfg.hx, d.startCfg.hw + dx)));
      const nh = Math.round(Math.max(8, Math.min(100 - d.startCfg.hy, d.startCfg.hh + dy)));
      setCfg(c => ({ ...c, hw: nw, hh: nh }));
    }
  };

  const endHotspotDrag = () => { dragHotRef.current = null; };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const finalTitle = form.title.trim() || "إعلان المتجر";
    const packedActionUrl = packAdminBannerUrl(cfg.clickMode === "none" ? "" : form.targetUrl, cfg);
    const values = {
      title: finalTitle,
      body: form.body || null,
      imageUrl: form.imageUrl || null,
      actionText: form.actionText || null,
      actionUrl: packedActionUrl,
      isActive: form.isActive,
      sortOrder: Number(form.sortOrder),
    };
    if (editing) update.mutate({ id: editing, values });
    else create.mutate({ title: finalTitle, imageUrl: form.imageUrl || undefined, body: form.body || undefined, actionText: form.actionText || undefined, actionUrl: packedActionUrl, isActive: form.isActive, sortOrder: Number(form.sortOrder) });
  };

  const edit = (item: NonNullable<typeof query.data>[number]) => {
    setEditing(item.id);
    const unpacked = unpackAdminBannerUrl(item.actionUrl);
    setForm({
      title: item.title,
      body: item.body ?? "",
      imageUrl: item.imageUrl ?? "",
      actionText: item.actionText ?? "",
      targetUrl: unpacked.targetUrl || "/products",
      isActive: item.isActive,
      sortOrder: String(item.sortOrder),
    });
    setCfg(unpacked.cfg);
    if (unpacked.targetUrl.startsWith("/products?category=")) setDestType("category");
    else if (unpacked.targetUrl.startsWith("/product/")) setDestType("product");
    else if (unpacked.targetUrl === "/assistant") setDestType("assistant");
    else if (!unpacked.targetUrl || unpacked.targetUrl === "/products") setDestType("all_products");
    else setDestType("custom");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const placementLabels: Record<AdminBannerCfg["placement"], string> = {
    top: "أعلى الصفحة الرئيسية",
    middle: "وسط الصفحة (بين الأقسام والمنتجات)",
    bottom: "أسفل الصفحة (بعد المنتجات)",
    popup: "إعلان منبثق عند فتح الموقع (Popup)",
  };

  const sizeLabels: Record<AdminBannerCfg["size"], string> = {
    auto: "المقاس الكامل الطبيعي للصورة (بدون قص)",
    small: "صغير مدمج",
    medium: "متوسط متناسق",
    large: "كبير سينمائي",
  };

  return (
    <div className="admin-content">
      <AdminHeading
        eyebrow="استوديو الإعلانات الاحترافي"
        title="الإعلانات والنوافذ الترويجية"
        text="تحكم كامل في صفاء الصورة بدون ضبابية أو نصوص مزعجة، مع تحديد مكان الزر المرسوم داخل الصورة باليد واختيار القسم وحجم ومكان الإعلان."
        icon={Megaphone}
      />
      <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">{editing ? "✳" : "01"}</span>
          <div>
            <h2>{editing ? "تعديل الإعلان وإعداداته" : "إضافة إعلان احترافي جديد"}</h2>
            <p>الصورة تظهر صافية 100% بدون ضبابية ولا كلام يغطي عليها، ويمكنك تحديد الزر المرسوم داخل صورتك مباشرة.</p>
          </div>
          {editing && <button type="button" className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}
        </div>

        <form className="admin-form" onSubmit={submit}>
          <div className="product-form-layout">
            <div className="form-fields-grid">
              <label>
                اسم الإعلان (مرجع لك في الإدارة)
                <input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="مثال: إعلان الخضار الطازجة" />
              </label>
              <label>
                مكان ظهور الإعلان في الموقع
                <select value={cfg.placement} onChange={e => setCfg({ ...cfg, placement: e.target.value as AdminBannerCfg["placement"] })}>
                  <option value="top">أعلى الصفحة الرئيسية (السلايدر الرئيسي)</option>
                  <option value="middle">وسط الصفحة (بين الأقسام والمنتجات)</option>
                  <option value="bottom">أسفل الصفحة (بعد المنتجات)</option>
                  <option value="popup">نافذة منبثقة أول ما يفتح الزبون الموقع (Popup)</option>
                </select>
              </label>
              <label>
                حجم الإعلان على الشاشة
                <select value={cfg.size} onChange={e => setCfg({ ...cfg, size: e.target.value as AdminBannerCfg["size"] })}>
                  <option value="auto">المقاس الكامل الطبيعي للصورة (بدون قص أي جزء)</option>
                  <option value="medium">متوسط متناسق (القياسي)</option>
                  <option value="large">كبير وبارز</option>
                  <option value="small">صغير مدمج (شريط إعلاني)</option>
                </select>
              </label>
              <label>
                طريقة تفاعل الزبون عند لمس الإعلان
                <select value={cfg.clickMode} onChange={e => setCfg({ ...cfg, clickMode: e.target.value as AdminBannerCfg["clickMode"] })}>
                  <option value="full">الضغط على أي مكان في صورة الإعلان بالكامل</option>
                  <option value="hotspot">تحديد مكان الزر المرسوم داخل الصورة فقط (مثل: تسوق الخضار)</option>
                  <option value="none">بدون ضغط (عرض الصورة فقط)</option>
                </select>
              </label>

              {cfg.clickMode !== "none" && (
                <>
                  <label>
                    عند الضغط يتوجه الزبون إلى:
                    <select
                      value={destType}
                      onChange={e => {
                        const next = e.target.value as typeof destType;
                        setDestType(next);
                        if (next === "all_products") setForm(f => ({ ...f, targetUrl: "/products" }));
                        else if (next === "assistant") setForm(f => ({ ...f, targetUrl: "/assistant" }));
                        else if (next === "category" && cats.data?.[0]) setForm(f => ({ ...f, targetUrl: "/products?category=" + cats.data![0].id }));
                        else if (next === "product" && prods.data?.[0]) setForm(f => ({ ...f, targetUrl: "/product/" + prods.data![0].id }));
                      }}
                    >
                      <option value="category">قسم معين من أقسام المتجر</option>
                      <option value="product">منتج معين في المتجر</option>
                      <option value="all_products">صفحة جميع المنتجات</option>
                      <option value="assistant">المساعد الذكي والشيف</option>
                      <option value="custom">رابط مخصص</option>
                    </select>
                  </label>

                  {destType === "category" && (
                    <label>
                      اختر القسم الذي يفتحه الإعلان
                      <select
                        value={form.targetUrl.replace("/products?category=", "")}
                        onChange={e => setForm({ ...form, targetUrl: e.target.value ? "/products?category=" + e.target.value : "/products" })}
                      >
                        <option value="">-- اختر القسم --</option>
                        {cats.data?.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}
                      </select>
                    </label>
                  )}

                  {destType === "product" && (
                    <label>
                      اختر المنتج الذي يفتحه الإعلان
                      <select
                        value={form.targetUrl.replace("/product/", "")}
                        onChange={e => setForm({ ...form, targetUrl: e.target.value ? "/product/" + e.target.value : "/products" })}
                      >
                        <option value="">-- اختر المنتج --</option>
                        {prods.data?.map(p => <option key={p.id} value={String(p.id)}>{p.name} ({money(p.price)})</option>)}
                      </select>
                    </label>
                  )}

                  {destType === "custom" && (
                    <label>
                      الرابط المخصص
                      <input value={form.targetUrl} onChange={e => setForm({ ...form, targetUrl: e.target.value })} placeholder="/products?category=1" dir="ltr" />
                    </label>
                  )}
                </>
              )}

              <label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: e.target.value })} /></label>
              <label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> تفعيل ونشر الإعلان في المتجر</label>

              {cfg.placement === "popup" && (
                <label className="toggle-field field-wide">
                  <input type="checkbox" checked={cfg.popupOnce} onChange={e => setCfg({ ...cfg, popupOnce: e.target.checked })} />
                  إظهار الإعلان المنبثق مرة واحدة فقط لكل زيارة (حتى لا يتكرر إزعاج الزبون)
                </label>
              )}

              <div className="field-wide" style={{ padding: "12px", borderRadius: "12px", background: "#f6f9f6", border: "1px solid #e1ebe3", display: "grid", gap: "8px" }}>
                <strong style={{ fontSize: "11px", color: "#174b36" }}>خيارات النصوص والتظليل فوق الصورة (مطفأة افتراضياً لتبقى صورتك صافية 100%):</strong>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "14px" }}>
                  <label className="toggle-field"><input type="checkbox" checked={cfg.showTitle} onChange={e => setCfg({ ...cfg, showTitle: e.target.checked })} /> إظهار عنوان ونص فوق الصورة</label>
                  <label className="toggle-field"><input type="checkbox" checked={cfg.shade} onChange={e => setCfg({ ...cfg, shade: e.target.checked })} /> إضافة ضبابية / تظليل داكن</label>
                  <label className="toggle-field"><input type="checkbox" checked={cfg.showBtn} onChange={e => setCfg({ ...cfg, showBtn: e.target.checked })} /> إظهار زر نظام إضافي فوق الصورة</label>
                </div>
                {(cfg.showTitle || cfg.showBtn) && (
                  <div className="form-fields-grid" style={{ marginTop: "6px" }}>
                    {cfg.showTitle && <label className="field-wide">النص الإضافي فوق الصورة<textarea rows={2} value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} /></label>}
                    {cfg.showBtn && <label>نص الزر الإضافي<input value={form.actionText} onChange={e => setForm({ ...form, actionText: e.target.value })} placeholder="اطلب الآن" /></label>}
                  </div>
                )}
              </div>
            </div>

            <ImageField title="رفع وقص صورة الإعلان" value={form.imageUrl} onChange={imageUrl => setForm(curr => ({ ...curr, imageUrl }))} kind="banner" aspect={2.2} />
          </div>

          {form.imageUrl && cfg.clickMode === "hotspot" && (
            <div style={{ padding: "14px", borderRadius: "16px", background: "#12221a", color: "#fff", display: "grid", gap: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <div>
                  <strong style={{ fontSize: "12px", color: "#f1d897", display: "block" }}>تحديد مكان الزر المرسوم داخل الصورة (منطقة ضغط الزبون):</strong>
                  <small style={{ fontSize: "10px", color: "#cfe0d5" }}>اسحب المستطيل الذهبي وضعه فوق الزر المرسوم في صورتك (مثل: تسوق الخضار أو اطلب الآن)، واسحب الدائرة الصفراء لتغيير حجمه.</small>
                </div>
              </div>
              <div
                ref={stageRef}
                onPointerMove={moveHotspotDrag}
                onPointerUp={endHotspotDrag}
                onPointerCancel={endHotspotDrag}
                style={{ position: "relative", width: "100%", maxWidth: "620px", margin: "0 auto", borderRadius: "14px", overflow: "hidden", userSelect: "none", touchAction: "none", lineHeight: 0 }}
              >
                <img src={form.imageUrl} alt="معاينة الإعلان" draggable={false} style={{ width: "100%", height: "auto", display: "block", pointerEvents: "none" }} />
                <div
                  onPointerDown={e => startHotspotDrag("move", e)}
                  style={{
                    position: "absolute",
                    left: cfg.hx + "%",
                    top: cfg.hy + "%",
                    width: cfg.hw + "%",
                    height: cfg.hh + "%",
                    border: "2.5px dashed #f1d897",
                    background: "rgba(241, 216, 151, 0.28)",
                    borderRadius: "12px",
                    cursor: "move",
                    touchAction: "none",
                    display: "grid",
                    placeItems: "center",
                    boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.32)",
                  }}
                >
                  <span style={{ background: "rgba(15, 45, 30, 0.88)", color: "#f1d897", padding: "3px 8px", borderRadius: "99px", fontSize: "10px", fontWeight: 700, pointerEvents: "none", whiteSpace: "nowrap" }}>
                    👆 منطقة ضغط الزبون
                  </span>
                  <span
                    onPointerDown={e => startHotspotDrag("resize", e)}
                    style={{
                      position: "absolute",
                      bottom: "-12px",
                      right: "-12px",
                      width: "26px",
                      height: "26px",
                      borderRadius: "50%",
                      background: "#f1d897",
                      border: "2.5px solid #0f5c3a",
                      cursor: "nwse-resize",
                      touchAction: "none",
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          <div className="form-submit-row" style={{ gap: "8px" }}>
            <button type="submit" className="button button-primary" disabled={create.isPending || update.isPending}>
              {create.isPending || update.isPending ? <LoaderCircle className="spin" size={16} /> : editing ? <Save size={16} /> : <Plus size={16} />}
              {editing ? "حفظ تعديلات الإعلان" : "حفظ الإعلان ونشره"}
            </button>
            {editing && <button type="button" className="button button-quiet" onClick={reset}>إلغاء</button>}
          </div>
        </form>
      </section>

      <div className="admin-section-heading">
        <div><h2>الإعلانات المحفوظة</h2><p>تحكم في مكان وحجم وحالة كل إعلان بضغطة واحدة.</p></div>
      </div>
      {!query.data?.length ? <AdminEmpty title="لا توجد إعلانات" text="ستبقى واجهة المتجر نظيفة حتى ترفع إعلانك الأول." /> : (
        <div className="entity-list">
          {query.data.map(item => {
            const meta = unpackAdminBannerUrl(item.actionUrl);
            return (
              <article className="entity-row" key={item.id}>
                <div className="entity-image">{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Megaphone size={19} />}</div>
                <div className="entity-main">
                  <strong>{item.title}</strong>
                  <small>
                    {placementLabels[meta.cfg.placement]} · {sizeLabels[meta.cfg.size]} · {meta.cfg.clickMode === "hotspot" ? "زر محدد داخل الصورة" : meta.cfg.clickMode === "full" ? "كامل الصورة قابلة للضغط" : "عرض فقط"}
                  </small>
                </div>
                <label className="toggle-field compact-toggle">
                  <input type="checkbox" checked={item.isActive} onChange={e => update.mutate({ id: item.id, values: { isActive: e.target.checked } })} /> نشط
                </label>
                <div className="entity-actions">
                  <button type="button" className="small-button" onClick={() => edit(item)}>تعديل الإعدادات</button>
                  <button type="button" className="small-button danger-soft" onClick={() => { if (window.confirm("هل أنت متأكد من حذف الإعلان «" + item.title + "» نهائياً؟")) remove.mutate({ id: item.id }); }}><Trash2 size={14} /> حذف</button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function OffersPanel() {
  const utils = trpc.useUtils(); const query = trpc.commerce.admin.offers.list.useQuery(undefined, { retry: 1 });
  const blank = { title: "", description: "", code: "", discountType: "percent" as "percent" | "fixed", discountValue: "", minimumOrder: "0", startsAt: "", endsAt: "", isActive: true };
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState(blank);
  const reset = () => { setEditing(null); setForm(blank); };
  const refresh = async () => { await utils.commerce.admin.offers.list.invalidate(); await utils.commerce.catalog.home.invalidate(); };
  const create = trpc.commerce.admin.offers.create.useMutation({ onSuccess: async () => { toast.success("تم حفظ العرض"); reset(); await refresh(); }, onError: error => toast.error(error.message) });
  const update = trpc.commerce.admin.offers.update.useMutation({ onSuccess: async (_result, variables) => { toast.success("تم تحديث العرض"); if (editing === variables.id) reset(); await refresh(); }, onError: error => toast.error(error.message) });
  const remove = trpc.commerce.admin.offers.delete.useMutation({ onSuccess: () => { toast.success("تم حذف العرض نهائياً"); void utils.commerce.admin.offers.list.invalidate(); void utils.commerce.catalog.home.invalidate(); } });
  const toLocal = (date: Date | string | null) => date ? new Date(date).toISOString().slice(0, 16) : "";
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (form.startsAt && form.endsAt && new Date(form.startsAt) > new Date(form.endsAt)) { toast.error("تاريخ نهاية العرض يجب أن يكون بعد تاريخ بدايته."); return; }
    const values = { title: form.title, description: form.description || null, code: form.code.trim().toUpperCase(), discountType: form.discountType, discountValue: Number(form.discountValue), minimumOrder: Number(form.minimumOrder), startsAt: form.startsAt ? new Date(form.startsAt).toISOString() : null, endsAt: form.endsAt ? new Date(form.endsAt).toISOString() : null, isActive: form.isActive };
    if (editing) update.mutate({ id: editing, values }); else create.mutate({ ...values, description: form.description || undefined });
  };
  const edit = (item: NonNullable<typeof query.data>[number]) => { setEditing(item.id); setForm({ title: item.title, description: item.description ?? "", code: item.code, discountType: item.discountType, discountValue: String(item.discountValue), minimumOrder: String(item.minimumOrder), startsAt: toLocal(item.startsAt), endsAt: toLocal(item.endsAt), isActive: item.isActive }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  return <div className="admin-content"><AdminHeading eyebrow="تحفيز الشراء" title="العروض والخصومات" text="الخصم يطبّق ويُعاد حسابه على الخادم عند تقديم الطلب." icon={BadgePercent} /><section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">{editing ? "✳" : "01"}</span><div><h2>{editing ? "تعديل العرض" : "إنشاء عرض"}</h2><p>أضف شروط العرض ورمز الكوبون.</p></div>{editing && <button type="button" className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}</div><form className="admin-form" onSubmit={submit}><div className="form-fields-grid"><label>اسم العرض<input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label><label>رمز الخصم<input required value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} /></label><label className="field-wide">وصف العرض<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label><label>نوع الخصم<select value={form.discountType} onChange={e => setForm({ ...form, discountType: e.target.value as "percent" | "fixed" })}><option value="percent">نسبة مئوية</option><option value="fixed">قيمة ثابتة</option></select></label><label>{form.discountType === "percent" ? "النسبة %" : "قيمة الخصم ر.ي"}<input type="number" min="1" max={form.discountType === "percent" ? "100" : undefined} required value={form.discountValue} onChange={e => setForm({ ...form, discountValue: e.target.value })} /></label><label>الحد الأدنى للطلب ر.ي<input type="number" min="0" step="1" value={form.minimumOrder} onChange={e => setForm({ ...form, minimumOrder: e.target.value })} /></label><label>يبدأ العرض<input type="datetime-local" value={form.startsAt} onChange={e => setForm({ ...form, startsAt: e.target.value })} /></label><label>ينتهي العرض<input type="datetime-local" value={form.endsAt} onChange={e => setForm({ ...form, endsAt: e.target.value })} /></label><label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> العرض فعّال</label></div><div className="form-submit-row"><button type="submit" className="button button-primary" disabled={create.isPending || update.isPending}>{create.isPending || update.isPending ? <LoaderCircle className="spin" size={16} /> : editing ? <Save size={16} /> : <Plus size={16} />}{editing ? "حفظ تعديل العرض" : "إنشاء العرض"}</button></div></form></section><div className="admin-section-heading"><div><h2>العروض الحالية</h2><p>رموز العرض تُفحص عند إرسال الطلب.</p></div></div>{!query.data?.length ? <AdminEmpty title="لا توجد عروض مضافة" text="يمكنك إضافة رمز خصم متى أردت." /> : <div className="entity-list">{query.data.map(item => <article className="entity-row" key={item.id}><div className="entity-image offer-art"><BadgePercent size={20} /></div><div className="entity-main"><strong>{item.title}</strong><small>{item.code} · {item.discountType === "percent" ? item.discountValue + "%" : money(item.discountValue)} · حد أدنى {money(item.minimumOrder)} · {item.startsAt ? new Date(item.startsAt).toLocaleDateString("ar-YE") : "دون بداية محددة"} — {item.endsAt ? new Date(item.endsAt).toLocaleDateString("ar-YE") : "دون انتهاء محدد"}</small></div><label className="toggle-field compact-toggle"><input type="checkbox" checked={item.isActive} onChange={e => update.mutate({ id: item.id, values: { isActive: e.target.checked } })} /> فعّال</label><div className="entity-actions"><button type="button" className="small-button" onClick={() => edit(item)}>تعديل</button><button type="button" className="small-button danger-soft" onClick={() => { if (window.confirm("هل أنت متأكد من حذف العرض «" + item.title + "» نهائياً؟")) remove.mutate({ id: item.id }); }}><Trash2 size={14} /> حذف</button></div></article>)}</div>}</div>;
}

function OrdersPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.orders.list.useQuery(undefined, { retry: 1 });
  const nextStates: Record<string, string[]> = { new: ["preparing", "cancelled"], preparing: ["ready", "cancelled"], ready: ["out_for_delivery", "cancelled"], out_for_delivery: ["delivered"], delivered: [], cancelled: [] };
  const [deliveryNotes, setDeliveryNotes] = useState<Record<number, string>>({});
  const change = trpc.commerce.admin.orders.setStatus.useMutation({ onSuccess: async () => { toast.success("تم تحديث حالة الطلب"); await Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate(), utils.commerce.orders.mine.invalidate(), utils.commerce.catalog.home.invalidate(), utils.commerce.catalog.listProducts.invalidate()]); }, onError: error => toast.error(error.message) });
  const deleteOrder = trpc.commerce.admin.orders.delete.useMutation({ onSuccess: async () => { toast.success("تم حذف الطلب نهائياً"); await Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate()]); }, onError: error => toast.error(error.message) });
  const exportOrders = () => {
    if (!query.data?.length) return;
    const quote = (value: string | number | null | undefined) => "\"" + String(value ?? "").replace(/"/g, "\"\"") + "\"";
    const rows: Array<Array<string | number | null | undefined>> = [
      ["رقم الطلب", "التاريخ", "المستلم", "الهاتف", "المدينة", "الحي", "الحالة", "المجموع الفرعي", "التوصيل", "الخصم", "الإجمالي", "طريقة الدفع", "الأصناف"],
      ...query.data.map(order => [order.orderNumber, new Date(order.createdAt).toLocaleString("ar-YE"), order.recipientName, order.phone, order.city, order.district, labels[order.status], order.subtotal, order.deliveryFee, order.discount, order.total, "نقدًا عند الاستلام", order.items.map(item => item.productName + " × " + item.quantity).join("; ")]),
    ];
    const blob = new Blob(["\uFEFF", rows.map(row => row.map(quote).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = "original-orders-" + new Date().toISOString().slice(0, 10) + ".csv"; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="admin-content">
    <AdminHeading eyebrow="من لحظة الطلب حتى التسليم" title="إدارة الطلبات" text="حدّث الحالة بالتسلسل، أو احذف الطلبات التجريبية والتنبيهات المنتهية." icon={ClipboardList} />
    <OwnerNotificationControl />
    {query.data?.length ? <div className="admin-actions-row admin-export-row"><span className="subtle-note">{query.data.length} طلبًا · التصدير يشمل البيانات التي حمّلتها اللوحة</span><button type="button" className="small-button" onClick={exportOrders}><Download size={15} />تصدير CSV</button></div> : null}
    {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !query.data?.length ? <AdminEmpty title="لا توجد طلبات" text="ستظهر الطلبات الجديدة هنا بعد تفعيل إعدادات التوصيل." /> : <div className="admin-orders">{query.data.map(order => {
      const allowedStatuses = [order.status, ...(nextStates[order.status] ?? [])];
      return <article className="admin-order-card" key={order.id}>
        <div className="admin-order-top"><div><strong className="order-number">{order.orderNumber}</strong><small>{new Date(order.createdAt).toLocaleString("ar-YE")}</small></div><div style={{ display: "flex", gap: "6px", alignItems: "center" }}><span className={"status-pill status-" + order.status}>{labels[order.status]}</span><button type="button" className="small-button danger-soft" onClick={() => { if (window.confirm("هل أنت متأكد من حذف الطلب «" + order.orderNumber + "» نهائياً؟")) deleteOrder.mutate({ id: order.id }); }}><Trash2 size={14} /> حذف</button></div></div>
        <div className="admin-order-customer"><strong>{order.recipientName}</strong><span>{order.phone}</span><span>{order.city}، {order.district}</span>{order.addressDetails && <small>{order.addressDetails}</small>}{order.customerNote && <small>ملاحظة العميل: {order.customerNote}</small>}</div>
        <div className="admin-order-lines">{order.items.map(item => <span key={item.id}>{item.productName} × {item.quantity} · {money(item.lineTotal)}</span>)}</div>
        <div className="admin-order-total"><span>فرعي {money(order.subtotal)} · توصيل {money(order.deliveryFee)}{order.discount ? " · خصم " + money(order.discount) : ""}</span><strong>{money(order.total)}</strong></div>
        <div className="admin-order-controls"><label>حالة الطلب<select value={order.status} disabled={order.status === "delivered" || order.status === "cancelled" || change.isPending} onChange={e => change.mutate({ id: order.id, status: e.target.value as "new" | "preparing" | "ready" | "out_for_delivery" | "delivered" | "cancelled", note: deliveryNotes[order.id]?.trim() || undefined }, { onSuccess: () => setDeliveryNotes(current => ({ ...current, [order.id]: "" })) })}>{Object.entries(labels).filter(([value]) => allowedStatuses.includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><span className="cod-note small"><Truck size={15} /> نقدًا عند الاستلام</span></div>
        <label className="admin-order-delivery-note"><span>ملاحظة للعميل (اختياري)</span><input maxLength={500} value={deliveryNotes[order.id] ?? ""} onChange={e => setDeliveryNotes(current => ({ ...current, [order.id]: e.target.value }))} placeholder="مثال: خرج للتوصيل باتجاه الحي..." disabled={order.status === "delivered" || order.status === "cancelled"} /><small>تُرسل مع إشعار تغيير الحالة وتظهر في سجل طلباتي.</small></label>
        {order.events.length ? <details className="order-history"><summary>سجل تغييرات الحالة</summary><ol>{order.events.map(event => <li key={event.id}><span className={"status-pill status-" + event.status}>{labels[event.status]}</span><time>{new Date(event.createdAt).toLocaleString("ar-YE")}</time>{event.note && <small>{event.note}</small>}</li>)}</ol></details> : null}
      </article>;
    })}</div>}
  </div>;
}

function UsersPanel() {
  const query = trpc.commerce.admin.customers.list.useQuery(undefined, { retry: 1 });
  return <div className="admin-content">
    <AdminHeading eyebrow="مجتمع المتجر" title="سجل العملاء" text="تُجمع أرقام العملاء من الطلبات التي أتموها. لا يحتاج العميل إلى إنشاء حساب؛ اتصل به لتأكيد الطلب والتوصيل." icon={Users} />
    <div className="privacy-note"><ShieldCheck size={17} /><span></span></div>
    {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !query.data?.length ? <AdminEmpty title="لا يوجد عملاء بعد" text="ستظهر أرقام العملاء هنا بعد استلام أول طلب." /> : <div className="user-list">{query.data.map(customer => <article className="user-row" key={customer.phone}>
      <span className="user-avatar"><CircleUserRound size={20} /></span>
      <div className="user-main"><strong dir="ltr">{customer.phone}</strong><small>آخر طلب: {new Date(customer.lastOrderAt).toLocaleString("ar-YE")}</small></div>
      <span className="visibility-tag visible">{customer.orderCount} {customer.orderCount === 1 ? "طلب" : "طلبات"}</span>
      <a className="small-button" href={`tel:${customer.phone}`}>اتصال بالعميل</a>
      <details className="user-details"><summary>ملخص مشتريات العميل</summary><div className="user-detail-grid"><span>عدد الطلبات: <strong>{customer.orderCount}</strong></span><span>قيمة الطلبات غير الملغاة: <strong>{money(customer.totalSpent)}</strong></span><span>آخر طلب: <strong>{new Date(customer.lastOrderAt).toLocaleString("ar-YE")}</strong></span></div><small className="subtle-note">لعرض الاسم والعنوان وتفاصيل التحقق، افتح الطلب الأخير من قائمة الطلبات.</small></details>
    </article>)}</div>}
  </div>;
}

function SettingsPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.settings.get.useQuery(undefined, { retry: 1 });
  const [ready, setReady] = useState(false);
  const [values, setValues] = useState({ storeName: "ORIGINAL – أوريجنال", storeDescription: "", contactPhone: "", currency: "ر.ي", storeIconUrl: "", deliveryEnabled: true, deliveryFee: "0", minOrderAmount: "0", deliveryZones: [] as Array<{ name: string; fee: number; enabled: boolean }>, orderPaused: false, pausedMessage: "", rewardEnabled: false, rewardsThreshold: "", rewardType: "free_delivery" as "free_delivery" | "discount_percent", rewardValue: "0", rewardsMessage: "" });
  useEffect(() => {
    if (!query.data || ready) return;
    const raw = query.data;
    let zones: Array<{ name: string; fee: number; enabled: boolean }> = [];
    try { const parsed = JSON.parse(raw.deliveryZones || "[]"); if (Array.isArray(parsed)) zones = parsed; } catch { /* malformed saved settings can be replaced in the editor */ }
    setValues({ storeName: raw.storeName || "ORIGINAL – أوريجنال", storeDescription: raw.storeDescription || "", contactPhone: raw.contactPhone || "", currency: raw.currency || "ر.ي", storeIconUrl: raw.storeIconUrl || "", deliveryEnabled: raw.deliveryEnabled !== "false", deliveryFee: raw.deliveryFee ?? "0", minOrderAmount: raw.minOrderAmount ?? "0", deliveryZones: zones, orderPaused: raw.orderPaused === "true", pausedMessage: raw.pausedMessage || "", rewardEnabled: raw.rewardEnabled === "true", rewardsThreshold: raw.rewardsThreshold || "", rewardType: raw.rewardType === "discount_percent" ? "discount_percent" : "free_delivery", rewardValue: raw.rewardValue || "0", rewardsMessage: raw.rewardsMessage || "" });
    setReady(true);
  }, [query.data, ready]);
  const save = trpc.commerce.admin.settings.save.useMutation({ onSuccess: async () => { toast.success("تم حفظ إعدادات المتجر"); await utils.commerce.admin.settings.get.invalidate(); await utils.commerce.catalog.home.invalidate(); }, onError: error => toast.error(error.message) });
  const update = <K extends keyof typeof values>(key: K, value: (typeof values)[K]) => setValues(current => ({ ...current, [key]: value }));
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (values.deliveryZones.some(zone => !zone.name.trim() || !Number.isInteger(zone.fee) || zone.fee < 0)) { toast.error("أكمل اسم كل منطقة وتأكد أن رسومها رقم صحيح غير سالب."); return; }
    /* allow 0 default delivery fee */
    if (values.deliveryFee !== "" && (!Number.isInteger(Number(values.deliveryFee)) || Number(values.deliveryFee) < 0)) { toast.error("الرسوم الأساسية يجب أن تكون عددًا صحيحًا غير سالب."); return; }
    save.mutate({ storeName: values.storeName, storeDescription: values.storeDescription, contactPhone: values.contactPhone, currency: values.currency, storeIconUrl: values.storeIconUrl || null, deliveryEnabled: values.deliveryEnabled, deliveryFee: values.deliveryFee === "" ? null : Number(values.deliveryFee), minOrderAmount: values.minOrderAmount === "" ? 0 : Math.max(0, Math.floor(Number(values.minOrderAmount) || 0)), deliveryZones: values.deliveryZones, orderPaused: values.orderPaused, pausedMessage: values.pausedMessage, rewardEnabled: values.rewardEnabled, rewardsThreshold: values.rewardsThreshold === "" ? null : Number(values.rewardsThreshold), rewardType: values.rewardType, rewardValue: Number(values.rewardValue), rewardsMessage: values.rewardsMessage });
  };
  const addZone = () => update("deliveryZones", [...values.deliveryZones, { name: "", fee: 0, enabled: true }]);
  const patchZone = (index: number, patch: Partial<(typeof values.deliveryZones)[number]>) => update("deliveryZones", values.deliveryZones.map((zone, i) => i === index ? { ...zone, ...patch } : zone));
  return <div className="admin-content"><AdminHeading eyebrow="مركز التحكم" title="إعدادات المتجر" text="اضبط هوية المتجر ورسومه ومناطق التوصيل دون إدخال بيانات افتراضية." icon={Settings2} />{query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : <form className="settings-form" onSubmit={submit}>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">01</span><div><h2>بيانات المتجر وهويته</h2><p>المعلومات والشعار الذي تختاره بنفسك.</p></div></div><div className="settings-brand-layout"><div className="form-fields-grid"><label>اسم المتجر<input required maxLength={100} value={values.storeName} onChange={e => update("storeName", e.target.value)} /></label><label>هاتف التواصل<input type="tel" value={values.contactPhone} onChange={e => update("contactPhone", e.target.value)} placeholder="أضف رقم المتجر" /></label><label>رمز العملة<input maxLength={20} value={values.currency} onChange={e => update("currency", e.target.value)} /></label><label className="field-wide">وصف المتجر<textarea rows={2} value={values.storeDescription} onChange={e => update("storeDescription", e.target.value)} /></label></div><ImageField title="قص شعار وأيقونة أوريجنال" value={values.storeIconUrl} onChange={value => update("storeIconUrl", value)} kind="icon" aspect={1} /></div></section>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">02</span><div><h2>التوصيل واستقبال الطلبات</h2><p>لا يُفتح الشراء حتى تحدد منطقة أو رسومًا قابلة للتطبيق.</p></div></div><div className="form-fields-grid"><label className="toggle-field"><input type="checkbox" checked={values.deliveryEnabled} onChange={e => update("deliveryEnabled", e.target.checked)} /> تفعيل استقبال طلبات التوصيل</label><label>رسوم أساسية (ر.ي)<input type="number" min="0" step="1" value={values.deliveryFee} onChange={e => update("deliveryFee", e.target.value)} placeholder="0" /></label><label>الحد الأدنى للطلب من المتجر (ر.ي)<input type="number" min="0" step="1" value={values.minOrderAmount} onChange={e => update("minOrderAmount", e.target.value)} placeholder="مثال: 1000 (0 = بدون حد أدنى)" /></label><div className="field-wide settings-zone-editor"><div className="admin-section-heading"><div><h3>مناطق التوصيل</h3><p>يمكن وضع رسوم مختلفة لكل مدينة أو منطقة.</p></div><button type="button" className="small-button" onClick={addZone}><Plus size={14} /> إضافة منطقة</button></div>{!values.deliveryZones.length ? <p className="subtle-note">لم تُضف مناطق بعد؛ سيُستخدم الرسم الأساسي إذا حُدد.</p> : values.deliveryZones.map((zone, index) => <div className="delivery-zone-row" key={index}><label>الاسم<input value={zone.name} onChange={e => patchZone(index, { name: e.target.value })} placeholder="اسم المنطقة" /></label><label>الرسم (ر.ي)<input type="number" min="0" step="1" value={zone.fee} onChange={e => patchZone(index, { fee: Number(e.target.value) })} /></label><label className="toggle-field"><input type="checkbox" checked={zone.enabled} onChange={e => patchZone(index, { enabled: e.target.checked })} /> مفعّلة</label><button type="button" className="small-button danger-soft" onClick={() => update("deliveryZones", values.deliveryZones.filter((_, i) => i !== index))}>حذف</button></div>)}</div><label className="toggle-field"><input type="checkbox" checked={values.orderPaused} onChange={e => update("orderPaused", e.target.checked)} /> إيقاف استقبال الطلبات مؤقتًا</label><label className="field-wide">رسالة الإيقاف<textarea value={values.pausedMessage} onChange={e => update("pausedMessage", e.target.value)} placeholder="اكتب الرسالة التي يراها العميل" /></label></div></section>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">03</span><div><h2>المكافآت</h2><p>تُحسب القاعدة على الخادم بعد مطابقة المجموع.</p></div></div><div className="form-fields-grid"><label className="toggle-field"><input type="checkbox" checked={values.rewardEnabled} onChange={e => update("rewardEnabled", e.target.checked)} /> تفعيل المكافأة</label><label>حد السلة (ر.ي)<input type="number" min="0" value={values.rewardsThreshold} onChange={e => update("rewardsThreshold", e.target.value)} /></label><label>نوع المكافأة<select value={values.rewardType} onChange={e => update("rewardType", e.target.value as typeof values.rewardType)}><option value="free_delivery">توصيل مجاني</option><option value="discount_percent">خصم بنسبة</option></select></label><label>قيمة الخصم %<input type="number" min="0" max="100" value={values.rewardValue} onChange={e => update("rewardValue", e.target.value)} /></label><label className="field-wide">رسالة المكافأة<textarea value={values.rewardsMessage} onChange={e => update("rewardsMessage", e.target.value)} /></label></div></section>
    <button className="button button-primary settings-save" disabled={save.isPending}>{save.isPending ? <LoaderCircle className="spin" size={16} /> : <Save size={17} />}{save.isPending ? "جارٍ الحفظ..." : "حفظ كل الإعدادات"}</button>
  </form>}</div>;
}

function AdminHeading({ eyebrow, title, text, icon: Icon }: { eyebrow: string; title: string; text: string; icon: typeof Package }) { return <div className="admin-page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p></div><span className="admin-heading-mark"><Icon size={25} /></span></div>; }
function AdminEmpty({ title, text }: { title: string; text: string }) { return <div className="admin-empty"><span><Box size={22} /></span><strong>{title}</strong><small>{text}</small></div>; }
function AdminLoading() { return <div className="admin-loading"><LoaderCircle className="spin" size={20} /> جارٍ تحميل بيانات المتجر...</div>; }
function AdminError({ message, retry }: { message: string; retry: () => void }) { return <div className="admin-error"><AlertTriangle size={18} /><div><strong>تعذر تحميل بيانات الإدارة</strong><small>{message}</small></div><button className="small-button" onClick={retry}>إعادة المحاولة</button></div>; }

const OWNER_ORDER_CURSOR_KEY = "original-owner-order-notification-cursor-v1";
function readOwnerOrderCursor() {
  try {
    if (typeof window === "undefined") return 0;
    const value = Number(window.localStorage.getItem(OWNER_ORDER_CURSOR_KEY));
    return Number.isSafeInteger(value) && value > 0 ? value : 0;
  } catch { return 0; }
}

function playOrderAlertSound() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    [587.33, 880].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.16);
      gain.gain.setValueAtTime(0.25, ctx.currentTime + idx * 0.16);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.16 + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.16);
      osc.stop(ctx.currentTime + idx * 0.16 + 0.36);
    });
  } catch {}
}

async function showPhoneOrderNotification(title: string, body: string, tag: string) {
  try {
    if ("serviceWorker" in navigator && Notification.permission === "granted") {
      const reg = await navigator.serviceWorker.ready;
      await reg.showNotification(title, {
        body,
        icon: "/app-icon-192-v2.png",
        badge: "/app-icon-192-v2.png",
        tag,
        dir: "rtl",
        lang: "ar",
        vibrate: [250, 120, 250, 120, 350],
        requireInteraction: true,
        renotify: true,
        data: { url: "/admin/orders" },
      } as any);
      return;
    }
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "/app-icon-192-v2.png", tag, dir: "rtl", lang: "ar" });
    }
  } catch {}
}

function OwnerNotificationControl() {
  const utils = trpc.useUtils();
  const [permission, setPermission] = useState(getPushPermissionState);
  const [enabled, setEnabled] = useState(() => getPushPermissionState() === "granted");
  const [pending, setPending] = useState(false);
  const [cursor, setCursor] = useState(readOwnerOrderCursor);
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.admin.notifications.subscribe.useMutation();
  const newOrders = trpc.commerce.admin.orders.createdAfter.useQuery({ afterId: cursor }, { retry: 1, staleTime: 0, refetchInterval: 4000, refetchIntervalInBackground: true, refetchOnWindowFocus: true });

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.ready.then(reg => {
        reg.active?.postMessage({ type: "SYNC_SW_STATE", isAdmin: true, afterId: cursor });
        if ("periodicSync" in reg) {
          void (reg as any).periodicSync.register("original-order-sync", { minInterval: 60000 }).catch(() => {});
        }
      }).catch(() => {});
    }
    if (getPushPermissionState() !== "granted") return;
    setEnabled(true);
    let active = true;
    void (async () => {
      try {
        const key = publicKey.data ?? (await publicKey.refetch()).data;
        if (key && active) {
          const sub = await ensureBrowserPushSubscription(key);
          await subscribe.mutateAsync(sub);
        }
      } catch {}
    })();
    return () => { active = false; };
  }, [cursor]);

  useEffect(() => {
    const data = newOrders.data;
    if (!data) return;
    const saveCursor = (next: number) => {
      setCursor(next);
      try { window.localStorage.setItem(OWNER_ORDER_CURSOR_KEY, String(next)); } catch {}
    };
    if (cursor === 0) {
      if (data.latestId > 0) saveCursor(data.latestId);
      return;
    }
    const incoming = data.orders.filter(order => order.id > cursor);
    if (incoming.length) {
      playOrderAlertSound();
      incoming.forEach(order => {
        toast.success(`🔔 وصل طلب جديد رقم ${order.orderNumber}`);
        void showPhoneOrderNotification(
          "طلب جديد في أوريجنال 🔔",
          `وصل الطلب رقم ${order.orderNumber} الآن — اضغط لفتحه في لوحة الطلبات.`,
          `original-new-order-${order.id}`
        );
      });
      void Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate()]);
    }
    if (data.latestId > cursor) saveCursor(data.latestId);
  }, [newOrders.data, cursor, enabled, utils]);

  const enableNotifications = async () => {
    setPending(true);
    try {
      const requestedPermission = await requestPushPermission();
      setPermission(requestedPermission);
      if (requestedPermission === "unsupported") throw new Error("متصفحك لا يدعم إشعارات الهاتف لهذا التطبيق.");
      if (requestedPermission !== "granted") throw new Error("يرجى السماح بالإشعارات من نافذة المتصفح لتصلك تنبيهات الطلبات.");
      setEnabled(true);
      playOrderAlertSound();
      await showPhoneOrderNotification(
        "تم تفعيل إشعارات الطلبات 🔔",
        "سيصلك إشعار فوري في شريط الهاتف مع كل طلب جديد حتى وأنت خارج المتصفح!",
        "original-admin-push-test"
      );
      toast.success("تم تفعيل إشعارات الهاتف بنجاح! أرسلنا لك إشعاراً تجريبياً في أعلى الشاشة.");
      try {
        const key = publicKey.data ?? (await publicKey.refetch()).data;
        if (key) {
          const subscription = await ensureBrowserPushSubscription(key);
          await subscribe.mutateAsync(subscription);
        }
      } catch {}
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "تعذر تفعيل الإشعارات الآن.");
    } finally {
      setPending(false);
    }
  };

  return <section className="owner-push-control" style={{ margin: "14px 20px 0", padding: "12px 16px", background: "#eaf3e9", border: "1px solid #c8dcc5", borderRadius: "14px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", flexWrap: "wrap" }}><div><strong style={{ color: "#174b36", fontSize: "12px", display: "block" }}>🔔 إشعارات الهاتف الفورية للطلبات الجديدة</strong><small style={{ color: "#4d6b57", fontSize: "10px" }}>{permission === "denied" ? "الإشعارات محظورة من إعدادات المتصفح (اضغط القفل بجانب الرابط لتفعيلها)." : enabled ? "مفعّلة على هاتفك — سيصلك إشعار خارجي وصوت فور وصول أي طلب جديد." : "اضغط زر التفعيل ليصلك إشعار في هاتفك فور قيام أي عميل بالطلب."}</small></div><button type="button" className="small-button selected" onClick={() => void enableNotifications()} disabled={pending || permission === "unsupported"}><BellRing size={15} />{pending ? "جارٍ التفعيل..." : enabled ? "إرسال إشعار تجريبي للهاتف" : "تفعيل إشعارات الهاتف الآن"}</button></section>;
}

// --- CHATS_PANEL_START ---
function ChatsPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.chats.list.useQuery(undefined, { refetchInterval: 3000 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const replyMutation = trpc.commerce.admin.chats.reply.useMutation({
    onSuccess: async () => {
      setReplyText("");
      toast.success("تم إرسال ردك للزبون في المحادثة مباشرة!");
      await utils.commerce.admin.chats.list.invalidate();
    },
    onError: err => toast.error(err.message),
  });
  const toggleAiMutation = trpc.commerce.admin.chats.toggleAi.useMutation({
    onSuccess: async () => {
      await utils.commerce.admin.chats.list.invalidate();
    },
  });
  const deleteMutation = trpc.commerce.admin.chats.delete.useMutation({
    onSuccess: async () => {
      toast.success("حُذفت المحادثة");
      setSelectedId(null);
      await utils.commerce.admin.chats.list.invalidate();
    },
  });

  const sessions = query.data ?? [];
  const activeSession = sessions.find(s => s.sessionId === selectedId) ?? sessions[0] ?? null;

  const sendOwnerReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSession || !replyText.trim() || replyMutation.isPending) return;
    replyMutation.mutate({ sessionId: activeSession.sessionId, text: replyText.trim() });
  };

  return (
    <div className="admin-content">
      <AdminHeading eyebrow="متابعة حية ومباشرة" title="محادثات الزبائن مع المساعد الذكي" text="شاهد جميع رسائل الزبائن مع الذكاء الاصطناعي لحظة بلحظة، وأرسل أي رد ليظهر للزبون فوراً داخل نفس المحادثة." icon={Sparkles} />
      {query.isLoading ? <AdminLoading /> : !sessions.length ? (
        <AdminEmpty title="لا توجد محادثات نشطة بعد" text="بمجرد أن يراسل أي زبون المساعد الذكي في المتجر، ستظهر محادثته هنا فوراً." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: "16px", alignItems: "start" }}>
          <section className="admin-form-card" style={{ padding: "14px", maxHeight: "70vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <strong>قائمة المحادثات ({sessions.length})</strong>
              <small style={{ color: "#0f5c3a" }}>تحديث تلقائي كل 3 ثوانٍ</small>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {sessions.map(s => {
                const isSel = activeSession?.sessionId === s.sessionId;
                const lastMsg = s.messages[s.messages.length - 1];
                return (
                  <button
                    key={s.sessionId}
                    type="button"
                    onClick={() => setSelectedId(s.sessionId)}
                    style={{
                      textAlign: "right",
                      padding: "12px",
                      borderRadius: "12px",
                      border: isSel ? "2px solid #0f5c3a" : "1px solid #e2ebe5",
                      background: isSel ? "#f1f8f4" : "#ffffff",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ color: "#12261c", fontSize: "0.92rem" }}>{s.customerName || "زبون المتجر"}</strong>
                      <span style={{ fontSize: "0.72rem", padding: "2px 8px", borderRadius: "99px", background: s.aiPaused ? "#fff3cd" : "#e3f5ec", color: s.aiPaused ? "#856404" : "#0f5c3a", fontWeight: 700 }}>
                        {s.aiPaused ? "✋ تدخل مباشر" : "🤖 الذكاء نشط"}
                      </span>
                    </div>
                    <small style={{ color: "#0f5c3a", fontWeight: 600 }} dir="ltr">{s.customerPhone}</small>
                    {lastMsg && <p style={{ margin: 0, fontSize: "0.8rem", color: "#556b5f", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{lastMsg.sender}: {lastMsg.text}</p>}
                    <small style={{ fontSize: "0.7rem", color: "#889990" }}>{new Date(s.updatedAt).toLocaleTimeString("ar-YE")}</small>
                  </button>
                );
              })}
            </div>
          </section>

          {activeSession && (
            <section className="admin-form-card" style={{ padding: "16px", display: "flex", flexDirection: "column", height: "70vh" }}>
              <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "8px", paddingBottom: "12px", borderBottom: "1px solid #e2ebe5" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1rem" }}>{activeSession.customerName}</h3>
                  <small style={{ color: "#0f5c3a", fontWeight: 700 }} dir="ltr">{activeSession.customerPhone}</small>
                  {activeSession.customerPhone && activeSession.customerPhone !== "غير مسجل بالموقع" && (
                    <a href={"tel:" + activeSession.customerPhone} className="small-button" style={{ marginRight: "8px", padding: "2px 8px", fontSize: "0.75rem" }}>📞 اتصال</a>
                  )}
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="small-button"
                    onClick={() => toggleAiMutation.mutate({ sessionId: activeSession.sessionId, aiPaused: !activeSession.aiPaused })}
                    style={{ background: activeSession.aiPaused ? "#0f5c3a" : "#fff3cd", color: activeSession.aiPaused ? "#fff" : "#856404" }}
                  >
                    {activeSession.aiPaused ? "🤖 إعادة تفعيل الذكاء" : "✋ إيقاف الذكاء والرد بنفسي"}
                  </button>
                  <button
                    type="button"
                    className="small-button danger-soft"
                    onClick={() => deleteMutation.mutate({ sessionId: activeSession.sessionId })}
                  >
                    حذف
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: "auto", padding: "12px 4px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {activeSession.messages.map(msg => {
                  const isUser = msg.role === "user";
                  const isOwner = msg.role === "owner";
                  return (
                    <div
                      key={msg.id}
                      style={{
                        alignSelf: isUser ? "flex-start" : "flex-end",
                        maxWidth: "85%",
                        padding: "10px 14px",
                        borderRadius: "14px",
                        background: isUser ? "#0f5c3a" : isOwner ? "#fff8e6" : "#f3f7f4",
                        color: isUser ? "#ffffff" : "#12261c",
                        border: isOwner ? "1.5px solid #e0a800" : isUser ? "none" : "1px solid #d5e6dc",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", marginBottom: "4px", fontSize: "0.72rem", opacity: 0.85, fontWeight: 700 }}>
                        <span>{isUser ? "🧑 " + msg.sender : isOwner ? "👨‍💼 أنت (إدارة المتجر)" : "🤖 المساعد الذكي"}</span>
                        <span>{new Date(msg.createdAt).toLocaleTimeString("ar-YE")}</span>
                      </div>
                      <p style={{ margin: 0, whiteSpace: "pre-line", fontSize: "0.88rem", lineHeight: 1.5 }}>{msg.text}</p>
                    </div>
                  );
                })}
              </div>

              <form onSubmit={sendOwnerReply} style={{ display: "flex", gap: "8px", paddingTop: "10px", borderTop: "1px solid #e2ebe5" }}>
                <input
                  value={replyText}
                  onChange={e => setReplyText(e.target.value)}
                  placeholder="اكتب رسالتك لتصل للزبون فوراً في نفس محادثة المساعد..."
                  style={{ flex: 1, padding: "10px 12px", borderRadius: "10px", border: "1px solid #cddbd2" }}
                />
                <button type="submit" className="button button-primary" disabled={!replyText.trim() || replyMutation.isPending}>
                  إرسال للزبون
                </button>
              </form>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
// --- CHATS_PANEL_END ---
// --- STAFF_PANEL_START ---
function StaffManagementPanel({ actorIsOwner, actorPermissions, actorStaffId }: { actorIsOwner: boolean; actorPermissions: PermissionKey[]; actorStaffId: number | null }) {
  const utils = trpc.useUtils();
  const staffQuery = trpc.commerce.admin.staff.list.useQuery(undefined, { retry: 1 });
  const logsQuery = trpc.commerce.admin.staff.auditLogs.useQuery(undefined, { retry: 1 });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [roleKey, setRoleKey] = useState<"general_manager" | "product_manager" | "order_manager" | "content_manager" | "staff">("product_manager");
  const [permissions, setPermissions] = useState<PermissionKey[]>(ROLE_DEFINITIONS.product_manager.defaultPermissions);
  const [mustChangePassword, setMustChangePassword] = useState(true);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "disabled">("all");

  const [resetTarget, setResetTarget] = useState<{ id: number; name: string } | null>(null);
  const [resetNewPass, setResetNewPass] = useState("");
  const [resetMustChange, setResetMustChange] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; name: string } | null>(null);

  const refreshAll = async () => {
    await Promise.all([
      utils.commerce.admin.staff.list.invalidate(),
      utils.commerce.admin.staff.auditLogs.invalidate(),
    ]);
  };

  const resetForm = () => {
    setEditingId(null);
    setDisplayName("");
    setUsername("");
    setPassword("");
    setRoleKey("product_manager");
    setPermissions([...ROLE_DEFINITIONS.product_manager.defaultPermissions]);
    setMustChangePassword(true);
  };

  const createMut = trpc.commerce.admin.staff.create.useMutation({
    onSuccess: async () => {
      toast.success("تم إنشاء الحساب الإداري وحفظ صلاحياته بنجاح");
      resetForm();
      await refreshAll();
    },
    onError: err => toast.error(err.message),
  });

  const updateMut = trpc.commerce.admin.staff.update.useMutation({
    onSuccess: async () => {
      toast.success("تم تحديث بيانات وصلاحيات المدير بنجاح");
      resetForm();
      await refreshAll();
    },
    onError: err => toast.error(err.message),
  });

  const statusMut = trpc.commerce.admin.staff.setStatus.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success(vars.isActive ? "تم تفعيل الحساب الإداري" : "تم تعطيل الحساب وإبطال جلسته");
      await refreshAll();
    },
    onError: err => toast.error(err.message),
  });

  const resetPassMut = trpc.commerce.admin.staff.resetPassword.useMutation({
    onSuccess: async () => {
      toast.success("تم إعادة تعيين كلمة المرور بنجاح");
      setResetTarget(null);
      setResetNewPass("");
      await refreshAll();
    },
    onError: err => toast.error(err.message),
  });

  const deleteMut = trpc.commerce.admin.staff.delete.useMutation({
    onSuccess: async () => {
      toast.success("تم حذف الحساب الإداري بأمان");
      setDeleteTarget(null);
      await refreshAll();
    },
    onError: err => toast.error(err.message),
  });

  const handleRoleChange = (nextRole: "general_manager" | "product_manager" | "order_manager" | "content_manager" | "staff") => {
    setRoleKey(nextRole);
    const defaults = ROLE_DEFINITIONS[nextRole]?.defaultPermissions ?? [];
    const allowedDefaults = actorIsOwner ? defaults : defaults.filter(p => actorPermissions.includes(p));
    setPermissions([...allowedDefaults]);
  };

  const togglePermission = (perm: PermissionKey) => {
    if (!actorIsOwner && !actorPermissions.includes(perm)) {
      toast.error("لا يمكنك منح صلاحية لا تملكها في حسابك.");
      return;
    }
    setPermissions(curr => curr.includes(perm) ? curr.filter(p => p !== perm) : [...curr, perm]);
  };

  const generateStrongPass = (setter: (val: string) => void) => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$";
    let out = "";
    for (let i = 0; i < 10; i++) out += chars[Math.floor(Math.random() * chars.length)];
    setter(out);
    navigator.clipboard?.writeText(out).catch(() => {});
    toast.success("تم توليد ونسخ كلمة مرور قوية: " + out);
  };

  const submitForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!permissions.length) {
      toast.error("اختر صلاحية واحدة على الأقل لهذا الحساب.");
      return;
    }
    if (editingId) {
      updateMut.mutate({ id: editingId, displayName, username, roleKey, permissions });
    } else {
      if (password.length < 6) {
        toast.error("كلمة المرور يجب ألا تقل عن 6 أحرف.");
        return;
      }
      createMut.mutate({ displayName, username, password, roleKey, permissions, mustChangePassword });
    }
  };

  const startEdit = (item: NonNullable<typeof staffQuery.data>["items"][number]) => {
    setEditingId(item.id);
    setDisplayName(item.displayName);
    setUsername(item.username);
    setPassword("");
    const r = (["general_manager", "product_manager", "order_manager", "content_manager", "staff"].includes(item.roleKey) ? item.roleKey : "staff") as "general_manager" | "product_manager" | "order_manager" | "content_manager" | "staff";
    setRoleKey(r);
    setPermissions([...item.permissions]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const items = staffQuery.data?.items ?? [];
  const summary = staffQuery.data?.summary ?? { total: 0, active: 0, disabled: 0 };
  const filteredItems = items.filter(item => {
    if (roleFilter !== "all" && item.roleKey !== roleFilter) return false;
    if (statusFilter === "active" && !item.isActive) return false;
    if (statusFilter === "disabled" && item.isActive) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      if (!item.displayName.toLowerCase().includes(q) && !item.username.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="admin-content">
      <AdminHeading
        eyebrow="الأمن والحوكمة متعددة المستويات"
        title="إدارة المديرين والمشرفين والصلاحيات"
        text="تحكم كامل في حسابات الطاقم الإداري، وحدد لكل مدير أو موظف الصلاحيات الدقيقة المسموح له بها في الخادم."
        icon={ShieldCheck}
      />

      <div className="admin-stat-grid">
        <div className="admin-stat"><span><Users size={18} /></span><small>إجمالي الطاقم الإداري</small><strong>{summary.total}</strong><em>بخلاف حساب المالك الرئيسي</em></div>
        <div className="admin-stat"><span><Check size={18} /></span><small>الحسابات النشطة</small><strong style={{ color: "#174b36" }}>{summary.active}</strong><em>يمكنهم الدخول حسب صلاحياتهم</em></div>
        <div className="admin-stat"><span><AlertTriangle size={18} /></span><small>الحسابات المعطلة</small><strong style={{ color: "#9b5346" }}>{summary.disabled}</strong><em>ممنوعون من الدخول فوراً</em></div>
        <div className="admin-stat"><span><ClipboardList size={18} /></span><small>عمليات مسجلة في التدقيق</small><strong>{logsQuery.data?.length ?? 0}</strong><em>أحدث السجلات الأمنية</em></div>
      </div>

      <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">{editingId ? "✳" : "01"}</span>
          <div>
            <h2>{editingId ? "تعديل بيانات وصلاحيات المدير" : "إضافة مدير أو مشرف جديد"}</h2>
            <p>تُحفظ كلمات المرور مشفرة بخوارزمية scrypt في قاعدة البيانات ولا تُخزن كنص صريح أبداً.</p>
          </div>
          {editingId && <button type="button" className="small-button" onClick={resetForm}>إلغاء التعديل <X size={14} /></button>}
        </div>

        <form onSubmit={submitForm} className="admin-form">
          <div className="form-fields-grid">
            <label>
              الاسم الكامل للمدير / الموظف
              <input required minLength={2} maxLength={160} value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="مثال: أحمد محمد - مدير الطلبات" />
            </label>
            <label>
              اسم المستخدم أو البريد الإلكتروني للدخول
              <input required minLength={3} maxLength={120} value={username} onChange={e => setUsername(e.target.value)} placeholder="مثال: ahmed_orders أو ahmed@store.com" dir="ltr" />
            </label>
            {!editingId && (
              <label>
                <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>كلمة المرور المؤقتة (6 أحرف فأكثر)</span>
                  <button type="button" className="text-link" style={{ fontSize: "10px", padding: 0 }} onClick={() => generateStrongPass(setPassword)}>توليد ونسخ كلمة قوية</button>
                </span>
                <input required minLength={6} maxLength={128} type="text" value={password} onChange={e => setPassword(e.target.value)} placeholder="أدخل كلمة مرور أو اضغط توليد" dir="ltr" />
              </label>
            )}
            <label>
              الدور الوظيفي الأساسي
              <select value={roleKey} onChange={e => handleRoleChange(e.target.value as any)}>
                <option value="general_manager">مدير عام — {ROLE_DEFINITIONS.general_manager.description}</option>
                <option value="product_manager">مدير منتجات — {ROLE_DEFINITIONS.product_manager.description}</option>
                <option value="order_manager">مدير طلبات — {ROLE_DEFINITIONS.order_manager.description}</option>
                <option value="content_manager">مدير محتوى وعروض — {ROLE_DEFINITIONS.content_manager.description}</option>
                <option value="staff">موظف / مشرف — {ROLE_DEFINITIONS.staff.description}</option>
              </select>
            </label>
            {!editingId && (
              <label className="toggle-field field-wide">
                <input type="checkbox" checked={mustChangePassword} onChange={e => setMustChangePassword(e.target.checked)} />
                إلزام هذا المدير بتغيير كلمة المرور المؤقتة فور أول تسجيل دخول له
              </label>
            )}
          </div>

          <div style={{ padding: "14px", borderRadius: "14px", border: "1px solid #e2ebe4", background: "#f9fbf8" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" }}>
              <strong style={{ fontSize: "12px", color: "#174b36" }}>تخصيص الصلاحيات الدقيقة ({permissions.length} محددة)</strong>
              <div style={{ display: "flex", gap: "6px" }}>
                <button type="button" className="small-button" onClick={() => setPermissions(actorIsOwner ? [...PERMISSION_KEYS] : [...actorPermissions])}>تحديد الكل المسموح</button>
                <button type="button" className="small-button" onClick={() => handleRoleChange(roleKey)}>إعادة الافتراضي للدور</button>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "8px" }}>
              {PERMISSION_KEYS.map(perm => {
                const meta = PERMISSION_LABELS[perm];
                const checked = permissions.includes(perm);
                const disabled = !actorIsOwner && !actorPermissions.includes(perm);
                return (
                  <label
                    key={perm}
                    style={{
                      display: "flex",
                      flexDirection: "row",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px 10px",
                      borderRadius: "10px",
                      border: checked ? "1.5px solid #174b36" : "1px solid #e1e8e2",
                      background: checked ? "#eef6f0" : "#ffffff",
                      opacity: disabled ? 0.5 : 1,
                      cursor: disabled ? "not-allowed" : "pointer",
                    }}
                  >
                    <input type="checkbox" checked={checked} disabled={disabled} onChange={() => togglePermission(perm)} style={{ width: "15px", minHeight: "15px", accentColor: "#174b36" }} />
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#1c3b2b" }}>{meta.label}</span>
                      <small style={{ fontSize: "9px", color: meta.sensitive ? "#9b5346" : "#78847b" }}>{meta.group}{meta.sensitive ? " · صلاحية حساسة" : ""}</small>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="form-submit-row">
            <button type="submit" className="button button-primary" disabled={createMut.isPending || updateMut.isPending}>
              {createMut.isPending || updateMut.isPending ? <LoaderCircle size={16} className="spin" /> : editingId ? <Save size={16} /> : <Plus size={16} />}
              {editingId ? "حفظ تعديلات المدير والصلاحيات" : "إضافة المدير وتفعيل صلاحياته"}
            </button>
          </div>
        </form>
      </section>

      <div className="admin-section-heading">
        <div><h2>قائمة المديرين والمشرفين</h2><p>ابحث أو صفِّ حسب الدور والحالة، أو تحكم في الحسابات النشطة.</p></div>
        <span className="count-chip">{filteredItems.length}</span>
      </div>

      <div className="filter-bar" style={{ marginBottom: "14px" }}>
        <label className="filter-search"><input value={search} onChange={e => setSearch(e.target.value)} placeholder="ابحث بالاسم أو اسم المستخدم..." /></label>
        <label className="filter-select">
          <select value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
            <option value="all">كل الأدوار</option>
            <option value="general_manager">مدير عام</option>
            <option value="product_manager">مدير منتجات</option>
            <option value="order_manager">مدير طلبات</option>
            <option value="content_manager">مدير محتوى وعروض</option>
            <option value="staff">موظف / مشرف</option>
          </select>
        </label>
        <label className="filter-select">
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as any)}>
            <option value="all">كل الحالات</option>
            <option value="active">نشط فقط</option>
            <option value="disabled">معطل فقط</option>
          </select>
        </label>
      </div>

      {staffQuery.isLoading ? <AdminLoading /> : staffQuery.error ? <AdminError message={staffQuery.error.message} retry={() => void staffQuery.refetch()} /> : !filteredItems.length ? (
        <AdminEmpty title="لا توجد حسابات إدارية مطابقة" text="أضف أول مدير أو موظف من النموذج أعلاه ليظهر هنا." />
      ) : (
        <div className="entity-list">
          {filteredItems.map(item => {
            const isSelf = Boolean(actorStaffId && actorStaffId === item.id);
            return (
              <article className="admin-order-card" key={item.id} style={{ borderLeft: item.isActive ? "4px solid #174b36" : "4px solid #b95653" }}>
                <div className="admin-order-top">
                  <div>
                    <strong style={{ fontSize: "14px", color: "#173c2a" }}>{item.displayName} {isSelf && <span className="default-tag">حسابك</span>}</strong>
                    <small dir="ltr" style={{ fontWeight: 700, color: "#397a54" }}>@{item.username}</small>
                  </div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
                    <span className="status-pill status-ready">{item.roleLabel}</span>
                    <span className={"visibility-tag " + (item.isActive ? "visible" : "hidden")}>{item.isActive ? "نشط" : "معطل"}</span>
                    {item.mustChangePassword && <span className="status-pill status-new">تغيير كلمة المرور مطلوب</span>}
                  </div>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", margin: "10px 0" }}>
                  {item.permissions.map(p => (
                    <span key={p} style={{ padding: "3px 8px", borderRadius: "6px", background: "#f1f6f2", color: "#29523c", fontSize: "10px", fontWeight: 600 }}>
                      {PERMISSION_LABELS[p]?.label || p}
                    </span>
                  ))}
                </div>
                <div className="admin-order-customer" style={{ marginTop: "6px", paddingBottom: "8px" }}>
                  <span>تاريخ الإنشاء: {new Date(item.createdAt).toLocaleDateString("ar-YE")}</span>
                  <span>آخر دخول: {item.lastLoginAt ? new Date(item.lastLoginAt).toLocaleString("ar-YE") : "لم يسجل الدخول بعد"}</span>
                  {item.createdBy && <span>أُنشئ بواسطة: {item.createdBy}</span>}
                </div>
                {!isSelf && (
                  <div className="entity-actions" style={{ justifyContent: "flex-start", paddingTop: "8px", borderTop: "1px solid #eef1ec" }}>
                    <button type="button" className="small-button" onClick={() => startEdit(item)}>تعديل الصلاحيات</button>
                    <button type="button" className="small-button" onClick={() => { setResetTarget({ id: item.id, name: item.displayName }); setResetNewPass(""); setResetMustChange(true); }}>إعادة تعيين كلمة المرور</button>
                    <button
                      type="button"
                      className={"small-button " + (item.isActive ? "danger-soft" : "selected")}
                      onClick={() => {
                        if (item.isActive && !window.confirm("هل أنت متأكد من تعطيل حساب «" + item.displayName + "» وإخراجه فوراً من النظام؟")) return;
                        statusMut.mutate({ id: item.id, isActive: !item.isActive });
                      }}
                    >
                      {item.isActive ? "تعطيل الحساب" : "تفعيل الحساب"}
                    </button>
                    {actorIsOwner && (
                      <button type="button" className="small-button danger-soft" onClick={() => setDeleteTarget({ id: item.id, name: item.displayName })}>
                        حذف نهائي
                      </button>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {resetTarget && (
        <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setResetTarget(null); }}>
          <section className="checkout-modal" style={{ maxWidth: "440px" }}>
            <div className="modal-heading">
              <div><span className="eyebrow">أمان الحساب</span><h2>إعادة تعيين كلمة مرور: {resetTarget.name}</h2></div>
              <button type="button" className="icon-button" onClick={() => setResetTarget(null)}><X size={18} /></button>
            </div>
            <form
              className="form-stack"
              onSubmit={e => {
                e.preventDefault();
                if (resetNewPass.length < 6) { toast.error("كلمة المرور يجب ألا تقل عن 6 أحرف."); return; }
                resetPassMut.mutate({ id: resetTarget.id, newPassword: resetNewPass, mustChangePassword: resetMustChange });
              }}
            >
              <label>
                <span style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>كلمة المرور الجديدة</span>
                  <button type="button" className="text-link" style={{ fontSize: "10px", padding: 0 }} onClick={() => generateStrongPass(setResetNewPass)}>توليد ونسخ كلمة قوية</button>
                </span>
                <input required minLength={6} type="text" value={resetNewPass} onChange={e => setResetNewPass(e.target.value)} placeholder="أدخل كلمة المرور الجديدة" dir="ltr" />
              </label>
              <label className="toggle-field">
                <input type="checkbox" checked={resetMustChange} onChange={e => setResetMustChange(e.target.checked)} />
                إلزام المدير بتغييرها عند أول دخول قادم
              </label>
              <div className="modal-footer">
                <button type="button" className="button button-quiet" onClick={() => setResetTarget(null)}>إلغاء</button>
                <button type="submit" className="button button-primary" disabled={resetPassMut.isPending}>حفظ كلمة المرور</button>
              </div>
            </form>
          </section>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setDeleteTarget(null); }}>
          <section className="checkout-modal" style={{ maxWidth: "420px" }}>
            <div className="modal-heading">
              <div><span className="eyebrow">تأكيد عملية حساسة</span><h2>حذف الحساب الإداري</h2></div>
              <button type="button" className="icon-button" onClick={() => setDeleteTarget(null)}><X size={18} /></button>
            </div>
            <p style={{ fontSize: "12px", lineHeight: 1.8, color: "#4e5e53" }}>
              هل أنت متأكد من حذف حساب <strong>«{deleteTarget.name}»</strong> نهائياً؟ سيتم إبطال جلسته فوراً مع الحفاظ الكامل على سجلات الطلبات والعمليات السابقة المرتبطة به.
            </p>
            <div className="modal-footer">
              <button type="button" className="button button-quiet" onClick={() => setDeleteTarget(null)}>تراجع</button>
              <button type="button" className="button button-primary" style={{ background: "#9b5346" }} disabled={deleteMut.isPending} onClick={() => deleteMut.mutate({ id: deleteTarget.id })}>
                تأكيد الحذف النهائي
              </button>
            </div>
          </section>
        </div>
      )}

      <div className="admin-section-heading" style={{ marginTop: "32px" }}>
        <div><h2>سجل التدقيق والنشاط الإداري (Audit Log)</h2><p>توثيق زمني لجميع عمليات الدخول وإدارة الحسابات والصلاحيات.</p></div>
      </div>
      {!logsQuery.data?.length ? (
        <AdminEmpty title="لا توجد سجلات تدقيق بعد" text="ستظهر هنا جميع العمليات الإدارية الحساسة فور حدوثها." />
      ) : (
        <div className="admin-order-table" style={{ maxHeight: "380px", overflowY: "auto" }}>
          {logsQuery.data.map(log => (
            <div className="admin-order-row" key={log.id} style={{ gridTemplateColumns: "1fr 1fr 1.5fr auto" }}>
              <span><strong>{log.actorName}</strong> <small>({log.actorRole})</small></span>
              <span className="order-number">{log.action}</span>
              <span>{log.targetName ? log.targetName + " — " : ""}{log.details || ""}</span>
              <small dir="ltr">{new Date(log.createdAt).toLocaleString("ar-YE")}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
// --- STAFF_PANEL_END ---

function canAccessSection(section: Section, isOwner: boolean, perms: PermissionKey[]): boolean {
  if (isOwner) return true;
  const has = (p: PermissionKey) => perms.includes(p);
  if (section === "overview") return has("overview.view");
  if (section === "products") return has("products.view") || has("products.manage") || has("inventory.manage");
  if (section === "categories") return has("categories.manage");
  if (section === "banners") return has("banners.manage");
  if (section === "offers") return has("offers.manage");
  if (section === "orders") return has("orders.view") || has("orders.manage");
  if (section === "chats") return has("chats.manage");
  if (section === "users") return has("customers.view");
  if (section === "staff") return has("staff.manage");
  if (section === "settings") return has("settings.manage");
  return false;
}

function AdminPanel({ section, isOwner, permissions, staffId }: { section: Section; isOwner: boolean; permissions: PermissionKey[]; staffId: number | null }) {
  if (section === "chats") return <ChatsPanel />;
  if (section === "products") return <ProductsPanel />;
  if (section === "categories") return <CategoriesPanel />;
  if (section === "banners") return <BannersPanel />;
  if (section === "offers") return <OffersPanel />;
  if (section === "orders") return <OrdersPanel />;
  if (section === "users") return <UsersPanel />;
  if (section === "staff") return <StaffManagementPanel actorIsOwner={isOwner} actorPermissions={permissions} actorStaffId={staffId} />;
  if (section === "settings") return <SettingsPanel />;
  return <Overview />;
}

export default function Admin() {
  const [location, navigate] = useLocation();
  const auth = useAuth();
  const utils = trpc.useUtils();
  const access = trpc.commerce.access.useQuery(undefined, { retry: 1, refetchOnWindowFocus: false });
  const logout = async () => { try { await auth.logout(); } finally { await utils.commerce.access.invalidate(); navigate("/admin"); } };
  const onLoginSuccess = async () => {
    await Promise.all([auth.refresh(), utils.commerce.access.invalidate()]);
  };

  if (auth.loading || access.isLoading) return <main className="admin-gate" dir="rtl"><AdminLoading /></main>;
  if (auth.error && !auth.user) return <AdminLoginGate reason="login" onSuccess={() => void onLoginSuccess()} />;
  if (!auth.user) return <AdminLoginGate reason="login" onSuccess={() => void onLoginSuccess()} />;
  if (auth.user.suspended || access.data?.isSuspended) return <AdminLoginGate reason="suspended" onLogout={logout} />;
  if (!access.data?.isAdmin) return <AdminLoginGate reason="forbidden" onLogout={logout} />;

  const isOwner = Boolean(access.data.isOwner);
  const permissions = (access.data.permissions ?? []) as PermissionKey[];
  const staffId = access.data.staffId ?? null;
  const roleLabel = isOwner ? "مالك المتجر" : (ROLE_DEFINITIONS[access.data.adminRole as AdminRoleKey]?.label || "مدير");

  if (access.data.mustChangePassword) {
    return <ForcePasswordChangeGate displayName={auth.user.name || "المدير"} onSuccess={() => void onLoginSuccess()} onLogout={() => void logout()} />;
  }

  const allowedSections = sections.filter(item => canAccessSection(item.id, isOwner, permissions));
  const requestedSection = location.split("/")[2] as Section | undefined;
  const activeSection = allowedSections.some(item => item.id === requestedSection)
    ? requestedSection!
    : (allowedSections[0]?.id ?? "overview");

  return (
    <div className="admin-app" dir="rtl">
      <aside className="admin-sidebar">
        <Link href="/" className="admin-brand"><span className="brand-mark"><Leaf size={20} /></span><span><strong>ORIGINAL</strong><small>لوحة الإدارة</small></span></Link>
        <div className="admin-profile">
          <span className="profile-initial">{(auth.user.name || "O").slice(0, 1)}</span>
          <span><strong>{auth.user.name || "مالك المتجر"}</strong><small>{roleLabel}</small></span>
          <span className="online-dot" />
        </div>
        <nav className="admin-nav">
          {allowedSections.map(item => {
            const Icon = item.icon;
            return (
              <button key={item.id} className={activeSection === item.id ? "active" : ""} onClick={() => { document.body.classList.remove("admin-menu-open"); navigate(item.id === "overview" ? "/admin" : "/admin/" + item.id); }}>
                <Icon size={18} /><span>{item.label}</span>{activeSection === item.id && <i />}
              </button>
            );
          })}
        </nav>
        <div className="admin-sidebar-bottom">
          <Link href="/" className="back-store"><ShoppingBag size={16} />عرض المتجر<ArrowLeft size={14} /></Link>
          <button className="logout-admin" onClick={() => void logout()}><LogOut size={16} />تسجيل الخروج</button>
          <small>نظام صلاحيات متعدد المستويات</small>
        </div>
      </aside>
      <main className="admin-main">
        <header className="admin-topbar">
          <button className="admin-menu-button" onClick={() => document.body.classList.toggle("admin-menu-open")}><ChevronDown size={18} />القائمة</button>
          <span className="admin-breadcrumb">أوريجنال <span>/</span> {allowedSections.find(item => item.id === activeSection)?.label}</span>
          <Link className="small-button" href="/">فتح المتجر<ArrowLeft size={14} /></Link>
        </header>
        <AdminPanel section={activeSection} isOwner={isOwner} permissions={permissions} staffId={staffId} />
      </main>
      <div className="admin-mobile-backdrop" onClick={() => document.body.classList.remove("admin-menu-open")} />
    </div>
  );
}
