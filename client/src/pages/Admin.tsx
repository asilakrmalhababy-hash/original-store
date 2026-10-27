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

async function quickCompressImageFile(file: File, kind: "product" | "category" | "banner" | "icon"): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      try {
        URL.revokeObjectURL(url);
        const maxDim = kind === "banner" ? 1080 : kind === "icon" ? 384 : 680;
        let w = img.naturalWidth || img.width || 600;
        let h = img.naturalHeight || img.height || 600;
        if (w > maxDim || h > maxDim) {
          const ratio = Math.min(maxDim / w, maxDim / h);
          w = Math.max(1, Math.round(w * ratio));
          h = Math.max(1, Math.round(h * ratio));
        }
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) { reject(new Error("تعذر معالجة الصورة")); return; }
        ctx.drawImage(img, 0, 0, w, h);
        const out = canvas.toDataURL("image/webp", 0.78);
        resolve(out);
      } catch (e) {
        reject(e);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("تعذر قراءة ملف الصورة"));
    };
    img.src = url;
  });
}

function ImageField({ value, onChange, kind, aspect, title }: { value: string; onChange: (value: string) => void; kind: "product" | "category" | "banner" | "icon"; aspect: number; title: string }) {
  const [open, setOpen] = useState(false);
  const [compressing, setCompressing] = useState(false);
  const quickInputRef = useRef<HTMLInputElement>(null);

  const handleQuickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setCompressing(true);
    try {
      const compressed = await quickCompressImageFile(file, kind);
      onChange(compressed);
      toast.success("تم تجهيز وضغط الصورة فوراً بنجاح ⚡");
    } catch {
      toast.error("تعذر قراءة الصورة، جرب صورة أخرى.");
    } finally {
      setCompressing(false);
    }
  };

  const handleCropSave = (dataUrl: string) => {
    onChange(dataUrl);
    setOpen(false);
    toast.success("تم اعتماد قص الصورة فوراً ⚡");
  };

  return (
    <div className="admin-image-field">
      <input ref={quickInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={e => void handleQuickFile(e)} />
      <div className="admin-image-preview" onClick={() => quickInputRef.current?.click()} style={{ cursor: "pointer" }} title="اضغط لاختيار صورة سريعة">
        {value ? <img src={value} alt="معاينة الصورة" /> : <span><ImagePlus size={22} /><small>{compressing ? "جارٍ الضغط السريع..." : "اضغط لاختيار صورة فوراً"}</small></span>}
      </div>
      <div className="admin-image-buttons" style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        <button type="button" className="small-button selected" disabled={compressing} onClick={e => { e.preventDefault(); e.stopPropagation(); quickInputRef.current?.click(); }}>
          <ImagePlus size={15} />{compressing ? "جارٍ التجهيز..." : value ? "تغيير سريع ⚡" : "رفع صورة سريع ⚡"}
        </button>
        <button type="button" className="small-button" onClick={e => { e.preventDefault(); e.stopPropagation(); setOpen(true); }}>
          ✂️ قص وتعديل
        </button>
        {value && (
          <button type="button" className="small-button danger-soft" onClick={e => { e.preventDefault(); e.stopPropagation(); onChange(""); }}>
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
  return <div className="admin-content"><div className="admin-page-heading"><div><span className="eyebrow">لوحة المالك</span><h1>أهلاً بك في أورجنال</h1><p>ابدأ بإعداد متجرك، وأضف محتواه عندما تكون جاهزًا.</p></div><span className="admin-heading-mark"><Leaf size={27} /></span></div><div className="admin-stat-grid">{[
    { label: "المنتجات", value: data.products, icon: Package }, { label: "الأقسام", value: data.categories, icon: Box }, { label: "كل الطلبات", value: data.orders, icon: ClipboardList }, { label: "العملاء", value: data.customers, icon: Users }, { label: "طلبات قيد المتابعة", value: data.openOrders, icon: Truck }, { label: "قيمة الطلبات غير الملغاة", value: data.orderValue, display: money(data.orderValue), icon: BadgePercent },
  ].map(item => { const Icon = item.icon; return <div className="admin-stat" key={item.label}><span><Icon size={18} /></span><small>{item.label}</small><strong>{"display" in item ? item.display : item.value.toLocaleString("en-US")}</strong><em>من بيانات المتجر</em></div>; })}</div>
    <div className="admin-welcome-panel"><div className="welcome-ornament"><span>O</span><i /></div><div><span className="eyebrow">الخطوة الأولى</span><h2>متجرك يبدأ من اختياراتك</h2><p>تحكم بمنتجاتك وأقسامك وطلبات العملاء بسهولة.</p><Link href="/admin/products" className="button button-primary">إضافة أول منتج<ArrowLeft size={16} /></Link></div></div>
    <div className="admin-section-heading"><div><h2>آخر الطلبات</h2><p>تظهر الطلبات هنا بعد أن يرسلها العملاء.</p></div><Link href="/admin/orders" className="small-button">إدارة الطلبات<ArrowLeft size={15} /></Link></div>
    {!data.recentOrders.length ? <div className="admin-empty"><ClipboardList size={22} /><strong>لا توجد طلبات بعد</strong><span>تأكد من إعداد التوصيل قبل فتح الطلبات.</span></div> : <div className="admin-order-table">{data.recentOrders.map(order => <div className="admin-order-row" key={order.id}><span className="order-number">{order.orderNumber}</span><span>{order.recipientName}</span><span>{new Date(order.createdAt).toLocaleDateString("ar-YE")}</span><b>{money(order.total)}</b><span className={`status-pill status-${order.status}`}>{labels[order.status]}</span></div>)}</div>}
  </div>;
}

function unpackProductVariants(rawDescription?: string | null): { cleanDescription: string; variants: string[]; weightEnabled: boolean; minWeightAmount: number } {
  let raw = String(rawDescription || "");
  let variants: string[] = [];
  let weightEnabled = false;
  let minWeightAmount = 100;
  const vm = raw.match(/\[\[variants:(\[[\s\S]*?\])\]\]/);
  if (vm) {
    raw = (raw.slice(0, vm.index) + raw.slice((vm.index || 0) + vm[0].length)).trim();
    try {
      const parsed = JSON.parse(vm[1]);
      if (Array.isArray(parsed)) variants = parsed.map(x => String(x || "").trim()).filter(Boolean).slice(0, 25);
    } catch {}
  }
  const wm = raw.match(/\[\[wcfg:(\{[\s\S]*?\})\]\]/);
  if (wm) {
    raw = (raw.slice(0, wm.index) + raw.slice((wm.index || 0) + wm[0].length)).trim();
    try {
      const parsed = JSON.parse(wm[1]);
      weightEnabled = Boolean(parsed.enabled);
      if (Number.isFinite(Number(parsed.minAmount)) && Number(parsed.minAmount) > 0) {
        minWeightAmount = Math.floor(Number(parsed.minAmount));
      }
    } catch {}
  }
  return { cleanDescription: raw.trim(), variants, weightEnabled, minWeightAmount };
}

function packProductVariants(cleanDescription: string, variants: string[], weightEnabled = false, minWeightAmount = 100): string | null {
  let out = cleanDescription.trim();
  const valid = [...new Set(variants.map(v => v.trim()).filter(Boolean))].slice(0, 25);
  if (valid.length > 0) {
    out = (out ? out + "\n" : "") + "[[variants:" + JSON.stringify(valid) + "]]";
  }
  if (weightEnabled) {
    out = (out ? out + "\n" : "") + "[[wcfg:" + JSON.stringify({ enabled: true, minAmount: Math.max(50, Number(minWeightAmount) || 100) }) + "]]";
  }
  return out || null;
}

type ProductFormState = {
  name: string;
  description: string;
  variants: string[];
  variantDraft: string;
  weightEnabled: boolean;
  minWeightAmount: string;
  imageUrl: string;
  categoryId: number | null;
  price: string;
  unit: string;
  stock: string;
  minQuantity: string;
  quantityStep: string;
  isPublished: boolean;
  isAvailable: boolean;
  sortOrder: string;
};

const blankProduct: ProductFormState = {
  name: "",
  description: "",
  variants: [],
  variantDraft: "",
  weightEnabled: false,
  minWeightAmount: "100",
  imageUrl: "",
  categoryId: null,
  price: "",
  unit: "حبة",
  stock: "",
  minQuantity: "1",
  quantityStep: "1",
  isPublished: true,
  isAvailable: true,
  sortOrder: "0",
};

function ProductsPanel() {
  const utils = trpc.useUtils();
  const [form, setForm] = useState(blankProduct);
  const [editing, setEditing] = useState<number | null>(null);
  const [showVariantsModal, setShowVariantsModal] = useState(false);
  const [showWeightModal, setShowWeightModal] = useState(false);
  const [showAdvancedFields, setShowAdvancedFields] = useState(false);
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
      toast.success("تمت إضافة المنتج بنجاح ⚡");
      setForm(blankProduct);
      setShowVariantsModal(false);
      setShowWeightModal(false);
      setShowAdvancedFields(false);
      await Promise.all([utils.commerce.admin.products.list.invalidate(), utils.commerce.admin.overview.invalidate(), refreshCatalog()]);
    },
    onError: error => toast.error(error.message),
  });

  const update = trpc.commerce.admin.products.update.useMutation({
    onSuccess: async () => {
      toast.success("تم حفظ تعديلات المنتج بنجاح ⚡");
      setEditing(null);
      setForm(blankProduct);
      setShowVariantsModal(false);
      setShowWeightModal(false);
      setShowAdvancedFields(false);
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
    const unpacked = unpackProductVariants(item.description);
    setEditing(item.id);
    setForm({
      name: item.name,
      description: unpacked.cleanDescription,
      variants: unpacked.variants,
      variantDraft: "",
      weightEnabled: unpacked.weightEnabled,
      minWeightAmount: String(unpacked.minWeightAmount || 100),
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

  const addDraftVariants = () => {
    const parts = form.variantDraft.split(/[,،\n]+/).map(s => s.trim()).filter(Boolean);
    if (!parts.length) return;
    setForm(curr => ({ ...curr, variants: [...new Set([...curr.variants, ...parts])], variantDraft: "" }));
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const extraParts = form.variantDraft.split(/[,،\n]+/).map(s => s.trim()).filter(Boolean);
    const allVariants = [...new Set([...form.variants, ...extraParts])];
    const packedDesc = packProductVariants(form.description, allVariants, form.weightEnabled, Number(form.minWeightAmount) || 100);
    const effectiveUnit = form.weightEnabled && (form.unit === "حبة" || !form.unit.trim()) ? "كيلو" : (form.unit.trim() || "حبة");
    const values = {
      name: form.name,
      description: packedDesc,
      imageUrl: form.imageUrl || null,
      categoryId: form.categoryId,
      price: Number(form.price),
      unit: effectiveUnit,
      stock: form.stock === "" ? null : Number(form.stock),
      minQuantity: Number(form.minQuantity) || 1,
      quantityStep: Number(form.quantityStep) || 1,
      isPublished: form.isPublished,
      isAvailable: form.isAvailable,
      sortOrder: Number(form.sortOrder) || 0,
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

  const samplePricePerKg = Number(form.price) || 4000;

  return (
    <div className="admin-content">
      <div className="admin-page-heading">
        <div><span className="eyebrow">كتالوج متجرك السريع</span><h1>إدارة المنتجات</h1><p>واجهة مبسطة وسريعة جداً لرفع المنتجات بالقطعة أو بالوزن والمبلغ (بهارات، حلاوة، خضروات).</p></div>
        <span className="admin-heading-mark"><Package size={25} /></span>
      </div>
      <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">{editing ? "✳" : "01"}</span>
          <div><h2>{editing ? "تعديل المنتج: " + form.name : "إضافة منتج جديد"}</h2><p>أدخل الاسم والسعر والقسم والصورة فقط، واستخدم الأزرار السفلية عند الحاجة لإضافة خيارات أو بيع بالوزن.</p></div>
          {editing && <button type="button" className="small-button" onClick={() => { setEditing(null); setForm(blankProduct); }}>إلغاء التعديل<X size={14} /></button>}
        </div>
        <form onSubmit={submit} className="admin-form">
          <div className="product-form-layout">
            <div className="form-fields-grid">
              <label className="field-wide">اسم المنتج *<input required maxLength={180} value={form.name} onChange={e => setField("name", e.target.value)} placeholder="مثلاً: كمون بلدي، حلاوة طحينية، زبادي..." /></label>
              <label>{form.weightEnabled ? "سعر الكيلو الواحد (1000 جرام) بالريال *" : "السعر بالريال اليمني *"}<input required type="number" min="0" value={form.price} onChange={e => setField("price", e.target.value)} placeholder={form.weightEnabled ? "مثلاً: 4000 (سعر الكيلو)" : "0"} /></label>
              <label>القسم<select value={form.categoryId ?? ""} onChange={e => setField("categoryId", e.target.value ? Number(e.target.value) : null)}><option value="">اختر القسم...</option>{cats.data?.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
              <label className="field-wide">الوصف (اختياري)<textarea rows={2} value={form.description} onChange={e => setField("description", e.target.value)} placeholder="وصف مختصر للمنتج..." /></label>

              <div className="field-wide" style={{ display: "flex", flexWrap: "wrap", gap: "8px", paddingTop: "4px" }}>
                <button
                  type="button"
                  className={"small-button" + (form.weightEnabled ? " selected" : "")}
                  onClick={() => setShowWeightModal(true)}
                  style={{ padding: "8px 13px", borderRadius: "12px", fontWeight: 800, border: form.weightEnabled ? "1.5px solid #174b36" : "1px solid #cbd8cf" }}
                >
                  ⚖️ {form.weightEnabled ? "البيع بالوزن والمبلغ: مفعّل ✅" : "تفعيل البيع بالوزن والمبلغ (بهارات / حلاوة / خضروات)"}
                </button>

                <button
                  type="button"
                  className={"small-button" + (form.variants.length > 0 ? " selected" : "")}
                  onClick={() => setShowVariantsModal(true)}
                  style={{ padding: "8px 13px", borderRadius: "12px", fontWeight: 800, border: form.variants.length > 0 ? "1.5px solid #174b36" : "1px solid #cbd8cf" }}
                >
                  🔀 {form.variants.length > 0 ? ("الأنواع المضافة (" + form.variants.length + "): " + form.variants.slice(0, 3).join("، ")) : "إضافة أنواع / خيارات للمنتج"}
                </button>

                <button
                  type="button"
                  className={"small-button" + (showAdvancedFields ? " selected" : "")}
                  onClick={() => setShowAdvancedFields(v => !v)}
                  style={{ padding: "8px 13px", borderRadius: "12px" }}
                >
                  ⚙️ {showAdvancedFields ? "إخفاء الخيارات الإضافية" : "خيارات إضافية (الوحدة / المخزون)"}
                </button>
              </div>

              {showAdvancedFields && (
                <div className="field-wide form-fields-grid" style={{ padding: "12px", borderRadius: "14px", background: "#f7faf8", border: "1px solid #dce6df" }}>
                  <label>وحدة البيع<input required value={form.unit} onChange={e => setField("unit", e.target.value)} placeholder="حبة، كيلو، عبوة..." /></label>
                  <label>الكمية المتوفرة بالمخزون<input type="number" min="0" value={form.stock} onChange={e => setField("stock", e.target.value)} placeholder="اتركه فارغًا إذا مفتوح" /></label>
                  <label>الحد الأدنى للكمية<input required type="number" min="1" value={form.minQuantity} onChange={e => setField("minQuantity", e.target.value)} /></label>
                  <label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setField("sortOrder", e.target.value)} /></label>
                  <label className="toggle-field"><input type="checkbox" checked={form.isPublished} onChange={e => setField("isPublished", e.target.checked)} /> نشر المنتج في المتجر</label>
                  <label className="toggle-field"><input type="checkbox" checked={form.isAvailable} onChange={e => setField("isAvailable", e.target.checked)} /> متاح للشراء</label>
                </div>
              )}
            </div>
            <ImageField title="قص وتجهيز صورة المنتج" value={form.imageUrl} onChange={imageUrl => setField("imageUrl", imageUrl)} kind="product" aspect={1} />
          </div>

          {showWeightModal && (
            <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setShowWeightModal(false)} style={{ zIndex: 180 }}>
              <section className="checkout-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: "460px", padding: "20px" }}>
                <div className="modal-heading" style={{ marginBottom: "12px" }}>
                  <div>
                    <span className="eyebrow">للبهارات والحلاوة الطحينية والخضروات</span>
                    <h2 style={{ fontSize: "18px", margin: "2px 0" }}>⚖️ إعداد البيع بالوزن والمبلغ</h2>
                  </div>
                  <button type="button" className="icon-button" onClick={() => setShowWeightModal(false)}><X size={18} /></button>
                </div>
                <div style={{ display: "grid", gap: "12px" }}>
                  <label className="toggle-field" style={{ padding: "12px", borderRadius: "12px", background: form.weightEnabled ? "#eaf6ee" : "#f5f5f2", border: form.weightEnabled ? "1.5px solid #174b36" : "1px solid #dcdcd4", fontWeight: 800 }}>
                    <input
                      type="checkbox"
                      checked={form.weightEnabled}
                      onChange={e => {
                        const checked = e.target.checked;
                        setForm(curr => ({ ...curr, weightEnabled: checked, unit: checked && curr.unit === "حبة" ? "كيلو" : curr.unit }));
                      }}
                    />
                    <span>تفعيل شراء هذا المنتج بالمبلغ والوزن (يكتب الزبون المبلغ ويظهر له الوزن تلقائياً)</span>
                  </label>

                  <label style={{ display: "grid", gap: "6px", fontSize: "12px", fontWeight: 700, color: "#174b36" }}>
                    <span>سعر الكيلو الواحد (1000 جرام) بالريال اليمني:</span>
                    <input type="number" min="100" step="50" value={form.price} onChange={e => setField("price", e.target.value)} placeholder="مثلاً: 4000" />
                  </label>

                  <label style={{ display: "grid", gap: "6px", fontSize: "12px", fontWeight: 700, color: "#174b36" }}>
                    <span>أقل مبلغ مسموح للزبون أن يشتري به (ر.ي):</span>
                    <input type="number" min="50" step="50" value={form.minWeightAmount} onChange={e => setField("minWeightAmount", e.target.value)} placeholder="مثلاً: 100 أو 200" />
                  </label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {[100, 200, 300, 500, 1000].map(mAmt => (
                      <button key={mAmt} type="button" className={"small-button" + (Number(form.minWeightAmount) === mAmt ? " selected" : "")} onClick={() => setField("minWeightAmount", String(mAmt))}>
                        أقل مبلغ: {mAmt} ر.ي
                      </button>
                    ))}
                  </div>

                  <div style={{ padding: "12px", borderRadius: "12px", background: "#f2f8f4", border: "1px solid #cbe0d2", fontSize: "12px", lineHeight: 1.6, color: "#174b36" }}>
                    <strong>كيف يظهر للزبون في المتجر؟</strong>
                    <div>• إذا كتب الزبون <b>{Math.round(samplePricePerKg * 0.125).toLocaleString("en-US")} ر.ي</b> ← يظهر له الوزن: <b>125 جرام (ثمن كيلو)</b></div>
                    <div>• إذا كتب الزبون <b>{Math.round(samplePricePerKg * 0.25).toLocaleString("en-US")} ر.ي</b> ← يظهر له الوزن: <b>250 جرام (ربع كيلو)</b></div>
                    <div>• إذا كتب الزبون <b>{Math.round(samplePricePerKg * 0.5).toLocaleString("en-US")} ر.ي</b> ← يظهر له الوزن: <b>500 جرام (نصف كيلو)</b></div>
                  </div>

                  <button type="button" className="button button-primary full-button" onClick={() => setShowWeightModal(false)}>
                    <Check size={16} /> اعتماد إعدادات الوزن والمبلغ
                  </button>
                </div>
              </section>
            </div>
          )}

          {showVariantsModal && (
            <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setShowVariantsModal(false)} style={{ zIndex: 180 }}>
              <section className="checkout-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: "460px", padding: "20px" }}>
                <div className="modal-heading" style={{ marginBottom: "12px" }}>
                  <div>
                    <span className="eyebrow">خيارات المنتج المتعددة</span>
                    <h2 style={{ fontSize: "18px", margin: "2px 0" }}>🔀 إضافة أنواع أو نكهات للمنتج</h2>
                    <small style={{ color: "#5e7165" }}>مثل: الهناء، الرعوي، نعناع، حار، عادي، بالمكسرات...</small>
                  </div>
                  <button type="button" className="icon-button" onClick={() => setShowVariantsModal(false)}><X size={18} /></button>
                </div>
                <div style={{ display: "grid", gap: "12px" }}>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <input
                      value={form.variantDraft}
                      onChange={e => setField("variantDraft", e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addDraftVariants(); } }}
                      placeholder="اكتب النوع (أو عدة أنواع بفاصلة) ثم اضغط إضافة"
                      style={{ flex: 1 }}
                    />
                    <button type="button" className="small-button selected" onClick={addDraftVariants}><Plus size={14} /> إضافة</button>
                  </div>
                  {form.variants.length > 0 ? (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", padding: "10px", borderRadius: "12px", background: "#f4f8f5" }}>
                      {form.variants.map(v => (
                        <span key={v} style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "5px 11px", borderRadius: "99px", background: "#174b36", color: "#ffffff", fontSize: "12px", fontWeight: 700 }}>
                          {v}
                          <button type="button" onClick={() => setField("variants", form.variants.filter(x => x !== v))} style={{ border: 0, background: "transparent", color: "#f1d897", cursor: "pointer", padding: 0, display: "grid", placeItems: "center" }}><X size={13} /></button>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="subtle-note">لم تُضف أنواع بعد لهذا المنتج.</p>
                  )}
                  <button type="button" className="button button-primary full-button" onClick={() => { addDraftVariants(); setShowVariantsModal(false); }}>
                    <Check size={16} /> اعتماد الأنواع وإغلاق النافذة
                  </button>
                </div>
              </section>
            </div>
          )}

          <div className="form-submit-row" style={{ gap: "8px" }}>
            <button type="submit" className="button button-primary" disabled={create.isPending || update.isPending}>
              {create.isPending || update.isPending ? <LoaderCircle size={16} className="spin" /> : editing ? <Save size={16} /> : <Plus size={17} />}
              {editing ? "حفظ التعديلات" : "إضافة المنتج الآن"}
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
          {filteredProducts.map(item => {
            const meta = unpackProductVariants(item.description);
            return (
              <article className="entity-row" key={item.id}>
                <div className="entity-image">{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Leaf size={19} />}</div>
                <div className="entity-main">
                  <strong>{item.name}</strong>
                  <small>
                    {cats.data?.find(cat => cat.id === item.categoryId)?.name || "بلا قسم"} · {meta.weightEnabled ? "⚖️ يباع بالوزن والمبلغ (سعر الكيلو)" : item.unit} · {item.stock === null ? "المخزون مفتوح" : "المخزون " + item.stock}
                    {meta.variants.length > 0 ? " · الأنواع: " + meta.variants.join(" / ") : ""}
                  </small>
                </div>
                <div className="entity-price">{money(item.price)}{meta.weightEnabled ? <small style={{ display: "block", fontSize: "10px", color: "#174b36" }}>لكل كيلو</small> : null}</div>
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
            );
          })}
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
              <label>لون زر القسم
  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginTop: "4px" }}>
    <input type="color" value={form.color || "#174b36"} onChange={e => setForm({ ...form, color: e.target.value })} style={{ width: "42px", height: "36px", padding: "2px", borderRadius: "10px", cursor: "pointer" }} />
    {["#174b36", "#b45309", "#be123c", "#1d4ed8", "#6d28d9", "#0f766e", "#374151"].map(preset => (
      <button key={preset} type="button" onClick={() => setForm({ ...form, color: preset })} style={{ width: "24px", height: "24px", borderRadius: "999px", background: preset, border: form.color === preset ? "2.5px solid #111827" : "1px solid #cbd5e1", cursor: "pointer" }} title={preset} />
    ))}
  </div>
</label>
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
  const query = trpc.commerce.admin.orders.list.useQuery(undefined, { retry: 1, refetchInterval: 10_000 });
  const nextStates: Record<string, string[]> = { new: ["preparing", "cancelled"], preparing: ["ready", "cancelled"], ready: ["out_for_delivery", "cancelled"], out_for_delivery: ["delivered"], delivered: [], cancelled: [] };
  const [deliveryNotes, setDeliveryNotes] = useState<Record<number, string>>({});
  const focusedOrderNo = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("order") : null;
  const change = trpc.commerce.admin.orders.setStatus.useMutation({
    onSuccess: async () => {
      toast.success("تم تحديث حالة الطلب وإرسال إشعار فوري واحد للعميل");
      await Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate(), utils.commerce.orders.mine.invalidate(), utils.commerce.catalog.home.invalidate(), utils.commerce.catalog.listProducts.invalidate()]);
    },
    onError: error => toast.error(error.message),
  });
  const sendNoteMut = trpc.commerce.admin.orders.sendNote.useMutation({
    onSuccess: async (_res, vars) => {
      toast.success("تم إرسال رسالتك كإشعار فوري أنيق لجوال العميل");
      setDeliveryNotes(current => ({ ...current, [vars.id]: "" }));
      await utils.commerce.admin.orders.list.invalidate();
    },
    onError: error => toast.error(error.message),
  });
  const deleteOrder = trpc.commerce.admin.orders.delete.useMutation({
    onSuccess: async () => {
      toast.success("تم حذف الطلب نهائياً");
      await Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate()]);
    },
    onError: error => toast.error(error.message),
  });
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
  const quickNotes = ["طلبك قيد التجهيز الآن 👨‍🍳", "طلبك جاهز للتوصيل ✨", "طلبك خرج للتوصيل 🛵", "المندوب قريب من موقعك 📍"];
  return <div className="admin-content">
    <AdminHeading eyebrow="من لحظة الطلب حتى التسليم" title="إدارة الطلبات وإشعارات العملاء" text="حدّث الحالة أو أرسل رسالة إشعار مخصصة تصل فوراً لشاشة جوال العميل." icon={ClipboardList} />
    <OwnerNotificationControl />
    {query.data?.length ? <div className="admin-actions-row admin-export-row"><span className="subtle-note">{query.data.length} طلبًا · التصدير يشمل البيانات التي حمّلتها اللوحة</span><button type="button" className="small-button" onClick={exportOrders}><Download size={15} />تصدير CSV</button></div> : null}
    {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !query.data?.length ? <AdminEmpty title="لا توجد طلبات" text="ستظهر الطلبات الجديدة هنا بعد تفعيل إعدادات التوصيل." /> : <div className="admin-orders">{query.data.map(order => {
      const allowedStatuses = [order.status, ...(nextStates[order.status] ?? [])];
      const noteVal = deliveryNotes[order.id] ?? "";
      const isFocused = focusedOrderNo === order.orderNumber;
      return <article className="admin-order-card" key={order.id} style={isFocused ? { border: "2px solid #174b36", boxShadow: "0 12px 28px rgba(23, 75, 54, 0.14)" } : undefined}>
        <div className="admin-order-top"><div><strong className="order-number">{order.orderNumber}</strong><small>{new Date(order.createdAt).toLocaleString("ar-YE")}</small></div><div style={{ display: "flex", gap: "6px", alignItems: "center" }}><span className={"status-pill status-" + order.status}>{labels[order.status]}</span><button type="button" className="small-button danger-soft" onClick={() => { if (window.confirm("هل أنت متأكد من حذف الطلب «" + order.orderNumber + "» نهائياً؟")) deleteOrder.mutate({ id: order.id }); }}><Trash2 size={14} /> حذف</button></div></div>
        <div className="admin-order-customer"><strong>{order.recipientName}</strong><span dir="ltr">{order.phone}</span><span>{order.city}، {order.district}</span>{order.addressDetails && <small>{order.addressDetails}</small>}{order.customerNote && <small>ملاحظة العميل: {order.customerNote}</small>}</div>
        <div className="admin-order-lines">{order.items.map(item => <span key={item.id}>{item.productName} × {item.quantity} · {money(item.lineTotal)}</span>)}</div>
        <div className="admin-order-total"><span>فرعي {money(order.subtotal)} · توصيل {money(order.deliveryFee)}{order.discount ? " · خصم " + money(order.discount) : ""}</span><strong>{money(order.total)}</strong></div>
        <div className="admin-order-controls"><label>حالة الطلب<select value={order.status} disabled={order.status === "delivered" || order.status === "cancelled" || change.isPending} onChange={e => change.mutate({ id: order.id, status: e.target.value as "new" | "preparing" | "ready" | "out_for_delivery" | "delivered" | "cancelled", note: noteVal.trim() || undefined }, { onSuccess: () => setDeliveryNotes(current => ({ ...current, [order.id]: "" })) })}>{Object.entries(labels).filter(([value]) => allowedStatuses.includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><span className="cod-note small"><Truck size={15} /> نقدًا عند الاستلام</span></div>
        <div className="admin-order-delivery-note" style={{ display: "grid", gap: "6px", marginTop: "8px" }}>
          <span style={{ fontSize: "11px", fontWeight: 700, color: "#174b36" }}>رسالة الإشعار للعميل (يصل النص الذي تكتبه هنا فقط بإشعار واحد أنيق):</span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <input maxLength={500} value={noteVal} onChange={e => setDeliveryNotes(current => ({ ...current, [order.id]: e.target.value }))} placeholder="اكتب رسالتك للعميل (مثلاً: طلبك خرج للتوصيل)..." style={{ flex: "1 1 200px" }} />
            <button type="button" className="small-button selected" disabled={!noteVal.trim() || sendNoteMut.isPending} onClick={() => sendNoteMut.mutate({ id: order.id, note: noteVal.trim() })}><BellRing size={14} /> إرسال إشعار فوري</button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {quickNotes.map(qn => (
              <button key={qn} type="button" className="small-button" style={{ fontSize: "10px", minHeight: "26px", padding: "0 8px" }} onClick={() => setDeliveryNotes(current => ({ ...current, [order.id]: qn }))}>{qn}</button>
            ))}
          </div>
        </div>
        {order.events.length ? <details className="order-history" open={isFocused}><summary>سجل تغييرات الحالة والإشعارات</summary><ol>{order.events.map(event => <li key={event.id}><span className={"status-pill status-" + event.status}>{labels[event.status]}</span><time>{new Date(event.createdAt).toLocaleString("ar-YE")}</time>{event.note && <small>{event.note}</small>}</li>)}</ol></details> : null}
      </article>;
    })}</div>}
  </div>;
}

const OWNER_ORDER_CURSOR_KEY = "original-owner-order-notification-cursor-v1";
function readOwnerOrderCursor() {
  try {
    if (typeof window === "undefined") return 0;
    const value = Number(window.localStorage.getItem(OWNER_ORDER_CURSOR_KEY));
    return Number.isSafeInteger(value) && value > 0 ? value : 0;
  } catch { return 0; }
}

function useAdminGlobalPushSync(isAdmin: boolean) {
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.admin.notifications.subscribe.useMutation();
  useEffect(() => {
    if (!isAdmin || getPushPermissionState() !== "granted") return;
    let active = true;
    void (async () => {
      try {
        let subscription = await getExistingBrowserPushSubscription();
        if (!subscription) {
          const key = publicKey.data ?? (await publicKey.refetch()).data;
          if (key) subscription = await ensureBrowserPushSubscription(key);
        }
        if (!subscription || !active) return;
        await subscribe.mutateAsync(subscription);
      } catch {}
    })();
    return () => { active = false; };
  }, [isAdmin]);
}

function OwnerNotificationControl() {
  const utils = trpc.useUtils();
  const [permission, setPermission] = useState(getPushPermissionState);
  const [enabled, setEnabled] = useState(() => getPushPermissionState() === "granted");
  const [pending, setPending] = useState(false);
  const [cursor, setCursor] = useState(readOwnerOrderCursor);
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.admin.notifications.subscribe.useMutation();
  const testPush = trpc.commerce.admin.notifications.testPush.useMutation({
    onSuccess: () => toast.success("أُرسل إشعار تجريبي لشريط جوالك الآن!"),
    onError: err => toast.error(err.message),
  });
  const newOrders = trpc.commerce.admin.orders.createdAfter.useQuery({ afterId: cursor }, { retry: 1, staleTime: 0, refetchInterval: 10_000, refetchOnWindowFocus: true });

  useEffect(() => {
    if (getPushPermissionState() !== "granted") return;
    let active = true;
    void (async () => {
      try {
        let subscription = await getExistingBrowserPushSubscription();
        if (!subscription) {
          const key = publicKey.data ?? (await publicKey.refetch()).data;
          if (key) subscription = await ensureBrowserPushSubscription(key);
        }
        if (!subscription || !active) return;
        await subscribe.mutateAsync(subscription);
        if (active) setEnabled(true);
      } catch {}
    })();
    return () => { active = false; };
  }, []);

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
      incoming.forEach(order => toast.success("🛍️ وصل طلب جديد " + order.orderNumber));
      void Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate()]);
    }
    if (data.latestId > cursor) saveCursor(data.latestId);
  }, [newOrders.data, cursor, utils]);

  const enableNotifications = async () => {
    setPending(true);
    try {
      const requestedPermission = await requestPushPermission();
      setPermission(requestedPermission);
      if (requestedPermission === "unsupported") throw new Error("متصفحك لا يدعم إشعارات Push لهذا التطبيق.");
      if (requestedPermission !== "granted") throw new Error("يرجى السماح بالإشعارات من إعدادات الموقع في المتصفح.");
      const key = publicKey.data ?? (await publicKey.refetch()).data;
      if (!key) throw new Error("تعذر الاتصال بخدمة الإشعارات. أعد المحاولة بعد قليل.");
      const subscription = await ensureBrowserPushSubscription(key);
      await subscribe.mutateAsync(subscription);
      setEnabled(true);
      toast.success("تم ربط هذا الجهاز بإشعارات الإدارة الفورية بنجاح!");
      void testPush.mutateAsync().catch(() => {});
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "تعذر تفعيل إشعارات الطلبات.");
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="owner-push-control" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "10px", padding: "14px 16px", borderRadius: "16px", background: enabled ? "#edf7f0" : "#fff9e8", border: enabled ? "1.5px solid #b8dec6" : "1.5px solid #f0dc9c" }}>
      <div>
        <strong style={{ display: "block", color: "#174b36", fontSize: "13px" }}>{enabled ? "🔔 إشعارات الإدارة الفورية نشطة على هذا الجهاز" : "🔔 تفعيل إشعارات الطلبات الفورية للإدارة"}</strong>
        <small style={{ color: "#4e6258", fontSize: "11px" }}>{permission === "denied" ? "الإذن محظور من إعدادات المتصفح؛ يرجى السماح به من أيقونة القفل أعلى المتصفح." : enabled ? "يصلك إشعار فوري مع كل طلب جديد لجميع الصلاحيات حتى لو كان الموقع مغلقاً لساعات." : "فعّل الإشعارات مرة واحدة ليصلك تنبيه فوري بشعار المتجر عند تأكيد أي طلب جديد."}</small>
      </div>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button type="button" className="small-button selected" onClick={() => void enableNotifications()} disabled={pending || permission === "denied" || permission === "unsupported"}>
          <BellRing size={15} />{pending ? "جارٍ الربط..." : enabled ? "تحديث ربط الإشعارات" : "تفعيل الإشعارات الآن"}
        </button>
        {enabled && (
          <button type="button" className="small-button" onClick={() => testPush.mutate()} disabled={testPush.isPending}>
            {testPush.isPending ? "جارٍ الإرسال..." : "🔔 تجربة الإشعار"}
          </button>
        )}
      </div>
    </section>
  );
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

type AdminRewardCfg = {
  rewardMode: "custom_gift" | "free_delivery" | "discount_percent" | "discount_fixed";
  giftName: string;
  fixedDiscount: number;
  endsAt: string;
  audience: "all" | "new_customers" | "returning_customers" | "vip_customers" | "specific_phones";
  allowedPhones: string;
  placement: "everywhere" | "home_and_cart" | "cart_only";
};

function unpackAdminRewardCfg(rawMsg?: string | null, fallbackType?: string): { cleanMessage: string; cfg: AdminRewardCfg } {
  const defaultCfg: AdminRewardCfg = {
    rewardMode: fallbackType === "discount_percent" ? "discount_percent" : "custom_gift",
    giftName: "",
    fixedDiscount: 0,
    endsAt: "",
    audience: "all",
    allowedPhones: "",
    placement: "everywhere",
  };
  const raw = String(rawMsg || "");
  const match = raw.match(/\[\[rcfg:(\{[\s\S]*?\})\]\]/);
  if (!match) return { cleanMessage: raw.trim(), cfg: defaultCfg };
  try {
    const parsed = JSON.parse(match[1]);
    const cleanMessage = (raw.slice(0, match.index) + raw.slice((match.index || 0) + match[0].length)).trim();
    return {
      cleanMessage,
      cfg: {
        rewardMode: ["custom_gift", "free_delivery", "discount_percent", "discount_fixed"].includes(parsed.rewardMode) ? parsed.rewardMode : defaultCfg.rewardMode,
        giftName: typeof parsed.giftName === "string" ? parsed.giftName.trim() : "",
        fixedDiscount: Number.isFinite(Number(parsed.fixedDiscount)) ? Math.max(0, Math.floor(Number(parsed.fixedDiscount))) : 0,
        endsAt: typeof parsed.endsAt === "string" ? parsed.endsAt.trim() : "",
        audience: ["all", "new_customers", "returning_customers", "vip_customers", "specific_phones"].includes(parsed.audience) ? parsed.audience : "all",
        allowedPhones: typeof parsed.allowedPhones === "string" ? parsed.allowedPhones.trim() : "",
        placement: ["everywhere", "home_and_cart", "cart_only"].includes(parsed.placement) ? parsed.placement : "everywhere",
      },
    };
  } catch {
    return { cleanMessage: raw.trim(), cfg: defaultCfg };
  }
}

function packAdminRewardCfg(cleanMessage: string, cfg: AdminRewardCfg): string {
  const clean = cleanMessage.trim();
  return (clean ? clean + " " : "") + "[[rcfg:" + JSON.stringify(cfg) + "]]";
}

function SettingsPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.settings.get.useQuery(undefined, { retry: 1 });
  const [ready, setReady] = useState(false);
  const [values, setValues] = useState({
    storeName: "ORIGINAL – أورجنال",
    storeDescription: "",
    contactPhone: "",
    currency: "ر.ي",
    storeIconUrl: "",
    deliveryEnabled: false,
    deliveryFee: "",
    deliveryZones: [] as Array<{ name: string; fee: number; enabled: boolean }>,
    orderPaused: false,
    pausedMessage: "",
    rewardEnabled: false,
    rewardsThreshold: "5000",
    rewardType: "free_delivery" as "free_delivery" | "discount_percent",
    rewardValue: "0",
    rewardsMessage: "",
    aiInstructions: "",
  });
  const [rcfg, setRcfg] = useState<AdminRewardCfg>({
    rewardMode: "custom_gift",
    giftName: "هدية مجانية مميزة من أورجنال 🎁",
    fixedDiscount: 500,
    endsAt: "",
    audience: "all",
    allowedPhones: "",
    placement: "everywhere",
  });

  useEffect(() => {
    if (!query.data || ready) return;
    const raw = query.data;
    let zones: Array<{ name: string; fee: number; enabled: boolean }> = [];
    try { const parsed = JSON.parse(raw.deliveryZones || "[]"); if (Array.isArray(parsed)) zones = parsed; } catch {}
    const unpacked = unpackAdminRewardCfg(raw.rewardsMessage, raw.rewardType);
    setValues({
      storeName: raw.storeName || "ORIGINAL – أورجنال",
      storeDescription: raw.storeDescription || "",
      contactPhone: raw.contactPhone || "",
      currency: raw.currency || "ر.ي",
      storeIconUrl: raw.storeIconUrl || "",
      deliveryEnabled: raw.deliveryEnabled === "true",
      deliveryFee: raw.deliveryFee || "",
      deliveryZones: zones,
      orderPaused: raw.orderPaused === "true",
      pausedMessage: raw.pausedMessage || "",
      rewardEnabled: raw.rewardEnabled === "true",
      rewardsThreshold: raw.rewardsThreshold || "5000",
      rewardType: raw.rewardType === "discount_percent" ? "discount_percent" : "free_delivery",
      rewardValue: raw.rewardValue || "0",
      rewardsMessage: unpacked.cleanMessage,
      aiInstructions: (raw as any).aiInstructions || "",
    });
    setRcfg(unpacked.cfg);
    setReady(true);
  }, [query.data, ready]);

  const save = trpc.commerce.admin.settings.save.useMutation({
    onSuccess: async () => {
      toast.success("تم حفظ إعدادات المتجر وشريط الهدايا التفاعلي بنجاح!");
      await utils.commerce.admin.settings.get.invalidate();
      await utils.commerce.catalog.home.invalidate();
    },
    onError: error => toast.error(error.message),
  });

  const update = <K extends keyof typeof values>(key: K, value: (typeof values)[K]) => setValues(current => ({ ...current, [key]: value }));
  const updateRcfg = <K extends keyof AdminRewardCfg>(key: K, value: AdminRewardCfg[K]) => setRcfg(current => ({ ...current, [key]: value }));

  const setDurationHours = (hours: number | null) => {
    if (!hours) { updateRcfg("endsAt", ""); return; }
    const d = new Date(Date.now() + hours * 3600 * 1000);
    const isoLocal = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    updateRcfg("endsAt", isoLocal);
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (values.deliveryZones.some(zone => !zone.name.trim() || !Number.isInteger(zone.fee) || zone.fee < 0)) { toast.error("أكمل اسم كل منطقة وتأكد أن رسومها رقم صحيح غير سالب."); return; }
    if (values.deliveryEnabled && values.deliveryFee === "" && !values.deliveryZones.some(zone => zone.enabled)) { toast.error("حدد رسومًا أساسية أو فعّل منطقة توصيل واحدة على الأقل قبل استقبال الطلبات."); return; }
    if (values.deliveryFee !== "" && (!Number.isInteger(Number(values.deliveryFee)) || Number(values.deliveryFee) < 0)) { toast.error("الرسوم الأساسية يجب أن تكون عددًا صحيحًا غير سالب."); return; }
    const mappedRewardType = rcfg.rewardMode === "discount_percent" ? "discount_percent" : "free_delivery";
    const packedMessage = packAdminRewardCfg(values.rewardsMessage, rcfg);
    save.mutate({
      storeName: values.storeName,
      storeDescription: values.storeDescription,
      contactPhone: values.contactPhone,
      currency: values.currency,
      storeIconUrl: values.storeIconUrl || null,
      deliveryEnabled: values.deliveryEnabled,
      deliveryFee: values.deliveryFee === "" ? null : Number(values.deliveryFee),
      deliveryZones: values.deliveryZones,
      orderPaused: values.orderPaused,
      pausedMessage: values.pausedMessage,
      rewardEnabled: values.rewardEnabled,
      rewardsThreshold: values.rewardsThreshold === "" ? null : Number(values.rewardsThreshold),
      rewardType: mappedRewardType,
      rewardValue: Math.min(100, Math.max(0, Number(values.rewardValue) || 0)),
      rewardsMessage: packedMessage,
    });
  };

  const addZone = () => update("deliveryZones", [...values.deliveryZones, { name: "", fee: 0, enabled: true }]);
  const patchZone = (index: number, patch: Partial<(typeof values.deliveryZones)[number]>) => update("deliveryZones", values.deliveryZones.map((zone, i) => i === index ? { ...zone, ...patch } : zone));

  const previewThreshold = Number(values.rewardsThreshold) || 5000;
  const previewGiftLabel = rcfg.giftName.trim() || (rcfg.rewardMode === "free_delivery" ? "توصيل مجاني بالكامل 🛵" : rcfg.rewardMode === "discount_percent" ? ("خصم فوري " + (values.rewardValue || 10) + "% 🏷️") : rcfg.rewardMode === "discount_fixed" ? ("خصم نقدي " + rcfg.fixedDiscount + " ر.ي 💸") : "هدية مجانية من أورجنال 🎁");

  return <div className="admin-content"><AdminHeading eyebrow="مركز التحكم" title="إعدادات المتجر وشريط الهدايا الحماسي" text="اضبط هوية المتجر ومناطق التوصيل وشريط المكافآت التفاعلي لرفع حماس ومشتريات الزبائن." icon={Settings2} />{query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : <form className="settings-form" onSubmit={submit}>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">01</span><div><h2>بيانات المتجر وهويته</h2><p>المعلومات والشعار الذي تختاره بنفسك.</p></div></div><div className="settings-brand-layout"><div className="form-fields-grid"><label>اسم المتجر<input required maxLength={100} value={values.storeName} onChange={e => update("storeName", e.target.value)} /></label><label>هاتف التواصل<input type="tel" value={values.contactPhone} onChange={e => update("contactPhone", e.target.value)} placeholder="أضف رقم المتجر" /></label><label>رمز العملة<input maxLength={20} value={values.currency} onChange={e => update("currency", e.target.value)} /></label><label className="field-wide">وصف المتجر<textarea rows={2} value={values.storeDescription} onChange={e => update("storeDescription", e.target.value)} /></label></div><ImageField title="قص شعار وأيقونة أورجنال" value={values.storeIconUrl} onChange={value => update("storeIconUrl", value)} kind="icon" aspect={1} /></div></section>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">02</span><div><h2>التوصيل واستقبال الطلبات</h2><p>لا يُفتح الشراء حتى تحدد منطقة أو رسومًا قابلة للتطبيق.</p></div></div><div className="form-fields-grid"><label className="toggle-field"><input type="checkbox" checked={values.deliveryEnabled} onChange={e => update("deliveryEnabled", e.target.checked)} /> تفعيل استقبال طلبات التوصيل</label><label>رسوم أساسية (ر.ي)<input type="number" min="0" step="1" value={values.deliveryFee} onChange={e => update("deliveryFee", e.target.value)} placeholder="غير محدد" /></label><div className="field-wide settings-zone-editor"><div className="admin-section-heading"><div><h3>مناطق التوصيل</h3><p>يمكن وضع رسوم مختلفة لكل مدينة أو منطقة.</p></div><button type="button" className="small-button" onClick={addZone}><Plus size={14} /> إضافة منطقة</button></div>{!values.deliveryZones.length ? <p className="subtle-note">لم تُضف مناطق بعد؛ سيُستخدم الرسم الأساسي إذا حُدد.</p> : values.deliveryZones.map((zone, index) => <div className="delivery-zone-row" key={index}><label>الاسم<input value={zone.name} onChange={e => patchZone(index, { name: e.target.value })} placeholder="اسم المنطقة" /></label><label>الرسم (ر.ي)<input type="number" min="0" step="1" value={zone.fee} onChange={e => patchZone(index, { fee: Number(e.target.value) })} /></label><label className="toggle-field"><input type="checkbox" checked={zone.enabled} onChange={e => patchZone(index, { enabled: e.target.checked })} /> مفعّلة</label><button type="button" className="small-button danger-soft" onClick={() => update("deliveryZones", values.deliveryZones.filter((_, i) => i !== index))}>حذف</button></div>)}</div><label className="toggle-field"><input type="checkbox" checked={values.orderPaused} onChange={e => update("orderPaused", e.target.checked)} /> إيقاف استقبال الطلبات مؤقتًا</label><label className="field-wide">رسالة الإيقاف<textarea value={values.pausedMessage} onChange={e => update("pausedMessage", e.target.value)} placeholder="اكتب الرسالة التي يراها العميل" /></label></div></section>

    <section className="admin-form-card" style={{ border: "2px solid #e3c472", background: "linear-gradient(180deg, #fffdf7 0%, #ffffff 100%)" }}>
      <div className="form-card-heading">
        <span className="form-card-number" style={{ background: "#174b36", color: "#f1d897" }}>03</span>
        <div>
          <h2>🎁 شريط المكافآت والهدايا التفاعلي الحماسي</h2>
          <p>شريط تفاعلي يتحرك أمام الزبون كلما أضاف منتجاً للسلة ليحفّزه على إكمال المبلغ المحدد والفوز بالهدية.</p>
        </div>
      </div>

      <div className="form-fields-grid">
        <label className="toggle-field field-wide" style={{ padding: "12px 14px", borderRadius: "12px", background: values.rewardEnabled ? "#eaf6ee" : "#f5f5f2", border: values.rewardEnabled ? "1.5px solid #2e8555" : "1px solid #dcdcd4", fontWeight: 800 }}>
          <input type="checkbox" checked={values.rewardEnabled} onChange={e => update("rewardEnabled", e.target.checked)} />
          <span>{values.rewardEnabled ? "✅ شريط الهدايا التفاعلي الحماسي مفعّل ويظهر للزبائن الآن" : "تفعيل شريط الهدايا والمكافآت التفاعلي في المتجر"}</span>
        </label>

        <div className="field-wide" style={{ display: "grid", gap: "8px" }}>
          <label>💰 المبلغ المطلوب للحصول على الهدية (ر.ي)
            <input type="number" min="100" step="100" value={values.rewardsThreshold} onChange={e => update("rewardsThreshold", e.target.value)} placeholder="مثلاً: 5000" />
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {[2000, 3000, 5000, 7500, 10000, 15000].map(amt => (
              <button key={amt} type="button" className={"small-button" + (Number(values.rewardsThreshold) === amt ? " selected" : "")} onClick={() => update("rewardsThreshold", String(amt))}>
                {amt.toLocaleString("en-US")} ر.ي
              </button>
            ))}
          </div>
        </div>

        <label>🎯 نوع المكافأة عند بلوغ المبلغ
          <select value={rcfg.rewardMode} onChange={e => updateRcfg("rewardMode", e.target.value as AdminRewardCfg["rewardMode"])}>
            <option value="custom_gift">🎁 هدية مجانية يحددها المتجر (تُضاف تلقائياً لفاتورة الطلب)</option>
            <option value="free_delivery">🛵 توصيل مجاني بالكامل (+ هدية اختيارية)</option>
            <option value="discount_percent">🏷️ خصم نسبة مئوية % من السلة (+ هدية اختيارية)</option>
            <option value="discount_fixed">💸 خصم مبلغ نقدي ثابت بالريال (+ هدية اختيارية)</option>
          </select>
        </label>

        {rcfg.rewardMode === "discount_percent" && (
          <label>نسبة الخصم %
            <input type="number" min="1" max="100" value={values.rewardValue} onChange={e => update("rewardValue", e.target.value)} placeholder="مثلاً: 10" />
          </label>
        )}

        {rcfg.rewardMode === "discount_fixed" && (
          <label>قيمة الخصم النقدي الثابت (ر.ي)
            <input type="number" min="50" step="50" value={rcfg.fixedDiscount} onChange={e => updateRcfg("fixedDiscount", Number(e.target.value) || 0)} placeholder="مثلاً: 500" />
          </label>
        )}

        <div className="field-wide" style={{ display: "grid", gap: "8px" }}>
          <label>🎁 اسم الهدية التي تظهر للزبون في الشريط وفي الطلب
            <input maxLength={140} value={rcfg.giftName} onChange={e => updateRcfg("giftName", e.target.value)} placeholder="مثلاً: علبة زبادي الهناء مجاناً 🥣 أو عصير طبيعي هدية 🧃" />
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {["علبة زبادي مجاناً 🥣", "عصير طبيعي بارد هدية 🧃", "مشروب غازي عائلي هدية 🥤", "هدية مفاجأة من أورجنال 🎁", "توصيل مجاني + هدية فورية 🚀"].map(preset => (
              <button key={preset} type="button" className={"small-button" + (rcfg.giftName === preset ? " selected" : "")} style={{ fontSize: "11px" }} onClick={() => updateRcfg("giftName", preset)}>
                {preset}
              </button>
            ))}
          </div>
        </div>

        <div className="field-wide" style={{ display: "grid", gap: "8px", padding: "12px", borderRadius: "12px", background: "#f8faf8", border: "1px solid #e1eae4" }}>
          <label style={{ margin: 0 }}>⏳ مدة العرض والعدّاد التنازلي الحماسي (اختياري)
            <input type="datetime-local" value={rcfg.endsAt} onChange={e => updateRcfg("endsAt", e.target.value)} />
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            <button type="button" className={"small-button" + (!rcfg.endsAt ? " selected" : "")} onClick={() => setDurationHours(null)}>♾️ مفتوح بدون انتهاء</button>
            <button type="button" className="small-button" onClick={() => setDurationHours(3)}>🔥 لمدة 3 ساعات</button>
            <button type="button" className="small-button" onClick={() => setDurationHours(12)}>⚡ لمدة 12 ساعة</button>
            <button type="button" className="small-button" onClick={() => setDurationHours(24)}>⏳ لمدة 24 ساعة</button>
            <button type="button" className="small-button" onClick={() => setDurationHours(72)}>📅 لمدة 3 أيام</button>
            <button type="button" className="small-button" onClick={() => setDurationHours(168)}>🗓️ لمدة أسبوع</button>
          </div>
        </div>

        <label>👥 لمن يظهر هذا العرض؟
          <select value={rcfg.audience} onChange={e => updateRcfg("audience", e.target.value as AdminRewardCfg["audience"])}>
            <option value="all">🌟 جميع زوار المتجر (الكل)</option>
            <option value="new_customers">🆕 الزبائن الجدد فقط (من لم يطلبوا سابقاً)</option>
            <option value="returning_customers">💎 الزبائن الدائمون فقط (من لديهم طلب سابق أو أكثر)</option>
            <option value="vip_customers">👑 كبار العملاء VIP (من لديهم 3 طلبات فأكثر)</option>
            <option value="specific_phones">📱 أرقام هواتف محددة فقط</option>
          </select>
        </label>

        <label>📍 مكان ظهور الشريط التفاعلي
          <select value={rcfg.placement} onChange={e => updateRcfg("placement", e.target.value as AdminRewardCfg["placement"])}>
            <option value="everywhere">🔥 في كل مكان (أعلى المتجر + المنتجات + السلة + شريط عائم سفلي)</option>
            <option value="home_and_cart">🏠 الصفحة الرئيسية + السلة فقط</option>
            <option value="cart_only">🛒 صفحة السلة فقط</option>
          </select>
        </label>

        {rcfg.audience === "specific_phones" && (
          <label className="field-wide">📱 أرقام الهواتف المسموح لها برؤية العرض (افصل بينها بفاصلة)
            <input value={rcfg.allowedPhones} onChange={e => updateRcfg("allowedPhones", e.target.value)} placeholder="مثلاً: 770731619, 771234567" dir="ltr" />
          </label>
        )}

        <label className="field-wide">✨ عبارة تشويقية إضافية تحت الشريط (اختياري)
          <input maxLength={220} value={values.rewardsMessage} onChange={e => update("rewardsMessage", e.target.value)} placeholder="مثلاً: تسوّق الآن واستمتع بهدايا أورجنال اليومية!" />
        </label>

        <div className="field-wide" style={{ padding: "14px", borderRadius: "16px", background: "linear-gradient(135deg, #0f3826 0%, #1d5c41 100%)", color: "#ffffff", boxShadow: "0 10px 24px rgba(15, 56, 38, 0.2)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", fontSize: "12px" }}>
            <strong style={{ color: "#f5dc98" }}>👀 معاينة حية لشكل الشريط أمام الزبون:</strong>
            <span style={{ background: "rgba(241, 216, 151, 0.2)", color: "#f5dc98", padding: "2px 8px", borderRadius: "99px", fontSize: "10px", fontWeight: 800 }}>65% مكتمل</span>
          </div>
          <div style={{ fontSize: "13px", fontWeight: 800, marginBottom: "8px" }}>
            ⚡ اقتربت جداً! أضف بقيمة {Math.round(previewThreshold * 0.35).toLocaleString("en-US")} ر.ي فقط لتربح «{previewGiftLabel}»!
          </div>
          <div style={{ height: "11px", borderRadius: "99px", background: "rgba(255,255,255,0.16)", overflow: "hidden", padding: "2px" }}>
            <div style={{ width: "65%", height: "100%", borderRadius: "99px", background: "linear-gradient(90deg, #f3c65f, #ffe89e, #4ade80)" }} />
          </div>
        </div>
      </div>
    </section>
    <section className="admin-form-card">
        <div className="form-card-heading">
          <span className="form-card-number">🤖</span>
          <div><h2>توجيهات وشخصية المساعد الذكي</h2><p>اكتب أي توجيهات تريد من الذكاء الاصطناعي الالتزام بها أثناء محادثة الزبائن (مثلاً: ركز على الخضار، اسأل عن عدد العائلة، لا تذكر السجائر، إلخ).</p></div>
        </div>
        <div className="form-stack">
          <label className="field-wide">توجيهاتك الخاصة للمساعد الذكي
            <textarea rows={4} maxLength={2500} value={values.aiInstructions} onChange={e => setValues({ ...values, aiInstructions: e.target.value })} placeholder="مثلاً: كن ودوداً جداً، إذا سأل الزبون عن السلة الأسبوعية اسأله كم عدد أفراد البيت، ركز على الخضروات الطازجة، ولا تقترح السجائر نهائياً..." />
          </label>
        </div>
      </section>
      <button className="button button-primary settings-save" disabled={save.isPending}>{save.isPending ? <LoaderCircle className="spin" size={16} /> : <Save size={17} />}{save.isPending ? "جارٍ الحفظ..." : "حفظ كل الإعدادات"}</button>
  </form>}</div>;
}


function AdminHeading({ eyebrow, title, text, icon: Icon }: { eyebrow: string; title: string; text: string; icon: typeof Package }) { return <div className="admin-page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p></div><span className="admin-heading-mark"><Icon size={25} /></span></div>; }
function AdminEmpty({ title, text }: { title: string; text: string }) { return <div className="admin-empty"><span><Box size={22} /></span><strong>{title}</strong><small>{text}</small></div>; }
function AdminLoading() { return <div className="admin-loading"><LoaderCircle className="spin" size={20} /> جارٍ تحميل بيانات المتجر...</div>; }
function AdminError({ message, retry }: { message: string; retry: () => void }) { return <div className="admin-error"><AlertTriangle size={18} /><div><strong>تعذر تحميل بيانات الإدارة</strong><small>{message}</small></div><button className="small-button" onClick={retry}>إعادة المحاولة</button></div>; }

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
  useAdminGlobalPushSync(Boolean(access.data?.isAdmin));
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
          <span className="admin-breadcrumb">أورجنال <span>/</span> {allowedSections.find(item => item.id === activeSection)?.label}</span>
          <Link className="small-button" href="/">فتح المتجر<ArrowLeft size={14} /></Link>
        </header>
        <AdminPanel section={activeSection} isOwner={isOwner} permissions={permissions} staffId={staffId} />
      </main>
      <div className="admin-mobile-backdrop" onClick={() => document.body.classList.remove("admin-menu-open")} />
    </div>
  );
}
