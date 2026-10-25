import { useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import {
  AlertTriangle, ArrowLeft, BadgePercent, BellRing, Box, Check, ChevronDown, CircleUserRound, ClipboardList,
  ImagePlus, LayoutDashboard, Leaf, LoaderCircle, LogOut, Megaphone, Package, Plus, Save,
  Settings2, ShieldCheck, ShoppingBag, SlidersHorizontal, Sparkles, Truck, Users, X, Download,
} from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";
import { useAuth } from "@/_core/hooks/useAuth";
import { startLogin } from "@/const";
import ImageEditor from "@/components/ImageEditor";
import { ensureBrowserPushSubscription, getExistingBrowserPushSubscription, getPushPermissionState, requestPushPermission } from "@/lib/pushNotifications";

const money = (value: number) => `${Number(value || 0).toLocaleString("en-US")} ر.ي`;
const labels: Record<string, string> = { new: "جديد", preparing: "قيد التجهيز", ready: "جاهز للتوصيل", out_for_delivery: "خرج للتوصيل", delivered: "تم التسليم", cancelled: "ملغي" };
type Section = "overview" | "products" | "categories" | "banners" | "offers" | "orders" | "chats" | "users" | "settings";
const sections: Array<{ id: Section; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "نظرة عامة", icon: LayoutDashboard },
  { id: "products", label: "المنتجات", icon: Package },
  { id: "categories", label: "الأقسام", icon: SlidersHorizontal },
  { id: "banners", label: "الإعلانات", icon: Megaphone },
  { id: "offers", label: "العروض والخصومات", icon: BadgePercent },
  { id: "orders", label: "الطلبات", icon: ClipboardList },
  { id: "chats", label: "محادثات الزبائن", icon: Sparkles },
  { id: "users", label: "العملاء", icon: Users },
  { id: "settings", label: "إعدادات المتجر", icon: Settings2 },
];

function ImageField({ value, onChange, kind, aspect, title }: { value: string; onChange: (value: string) => void; kind: "product" | "category" | "banner" | "icon"; aspect: number; title: string }) {
  const [open, setOpen] = useState(false);
  const upload = trpc.commerce.admin.uploadImage.useMutation({ onSuccess: result => { onChange(result.imageUrl); setOpen(false); toast.success("حُفظت الصورة في تخزين المتجر"); }, onError: error => toast.error(error.message) });
  return <div className="admin-image-field"><div className="admin-image-preview">{value ? <img src={value} alt="معاينة الصورة" /> : <span><ImagePlus size={22} /><small>لم تُرفع صورة</small></span>}</div><div className="admin-image-buttons"><button type="button" className="small-button" onClick={() => setOpen(true)}><ImagePlus size={15} />{value ? "قص/استبدال الصورة" : "رفع صورة"}</button>{value && <button type="button" className="small-button danger-soft" onClick={() => onChange("")}><X size={14} />إزالة</button>}</div>{open && <ImageEditor title={title} aspect={aspect} format="webp" onCancel={() => setOpen(false)} onSave={dataUrl => upload.mutate({ dataUrl, kind })} />}{upload.isPending && <small className="upload-status"><LoaderCircle size={14} className="spin" /> جارٍ الرفع...</small>}</div>;
}

function AdminLoginGate({ reason, onLogout }: { reason: "login" | "forbidden" | "suspended"; onLogout?: () => void | Promise<void> }) {
  const message = reason === "login"
    ? "أدخل كلمة مرور الإدارة للمتابعة إلى لوحة التحكم."
    : reason === "suspended"
      ? "تم إيقاف هذا الحساب. تواصل مع مالك المتجر."
      : "تم تسجيل دخولك، لكن هذا الحساب غير مربوط حاليًا بصلاحية المالك. إذا كنت مالك المتجر، اربط بريد حساب Manus من إعداد المالك المحمي، ثم سجّل الخروج والدخول مجددًا. لا تُمنح الإدارة لأول مستخدم تلقائيًا.";
  return <main className="admin-gate" dir="rtl"><div className="admin-gate-card"><span className="admin-gate-mark"><ShieldCheck size={26} /></span><span className="eyebrow">إدارة خاصة</span><h1>{reason === "login" ? "تسجيل دخول المالك" : reason === "suspended" ? "الحساب موقوف" : "تعذّر التحقق من صلاحية المالك"}</h1><p>{message}</p>{reason === "login" ? <button className="button button-primary" onClick={startLogin}>دخول لوحة تحكم المالك<ArrowLeft size={16} /></button> : <><Link className="button button-outline" href="/">العودة للمتجر</Link>{reason === "forbidden" && onLogout && <button className="button button-quiet" onClick={() => void onLogout()}>تسجيل الخروج</button>}</>}<small className="secure-caption"><ShieldCheck size={14} /> تُفحص الصلاحيات على الخادم</small></div></main>;
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
const blankProduct: ProductFormState = { name: "", description: "", imageUrl: "", categoryId: null, price: "", unit: "حبة", stock: "", minQuantity: "1", quantityStep: "1", isPublished: false, isAvailable: true, sortOrder: "0" };

function ProductsPanel() {
  const utils = trpc.useUtils(); const [form, setForm] = useState(blankProduct); const [editing, setEditing] = useState<number | null>(null); const [recommended, setRecommended] = useState<number | null>(null); const [recommendedIds, setRecommendedIds] = useState<number[]>([]);
  const refreshCatalog = async () => Promise.all([utils.commerce.catalog.home.invalidate(), utils.commerce.catalog.listProducts.invalidate(), utils.commerce.catalog.listCategories.invalidate(), utils.commerce.catalog.product.invalidate()]);
  const query = trpc.commerce.admin.products.list.useQuery(undefined, { retry: 1 });
  const cats = trpc.commerce.admin.categories.list.useQuery(undefined, { retry: 1 });
  const create = trpc.commerce.admin.products.create.useMutation({ onSuccess: async () => { toast.success("تمت إضافة المنتج"); setForm(blankProduct); await Promise.all([utils.commerce.admin.products.list.invalidate(), utils.commerce.admin.overview.invalidate(), refreshCatalog()]); }, onError: error => toast.error(error.message) });
  const update = trpc.commerce.admin.products.update.useMutation({ onSuccess: async () => { toast.success("تم تحديث المنتج"); setEditing(null); setForm(blankProduct); await Promise.all([utils.commerce.admin.products.list.invalidate(), refreshCatalog()]); }, onError: error => toast.error(error.message) });
  const archive = trpc.commerce.admin.products.archive.useMutation({ onSuccess: async () => { toast.success("أُخفي المنتج عن المتجر"); await Promise.all([utils.commerce.admin.products.list.invalidate(), refreshCatalog()]); }, onError: error => toast.error(error.message) });
  const saveRecommendations = trpc.commerce.admin.products.setRecommendations.useMutation({ onSuccess: async () => { toast.success("تم تحديث المنتجات المقترحة"); setRecommended(null); await utils.commerce.catalog.product.invalidate(); }, onError: error => toast.error(error.message) });
  const setField = <K extends keyof ProductFormState>(key: K, value: ProductFormState[K]) => setForm(current => ({ ...current, [key]: value }));
  const selectEdit = (item: NonNullable<typeof query.data>[number]) => { setEditing(item.id); setForm({ name: item.name, description: item.description ?? "", imageUrl: item.imageUrl ?? "", categoryId: item.categoryId, price: String(item.price), unit: item.unit, stock: item.stock === null ? "" : String(item.stock), minQuantity: String(item.minQuantity), quantityStep: String(item.quantityStep), isPublished: item.isPublished, isAvailable: item.isAvailable, sortOrder: String(item.sortOrder) }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const submit = (event: React.FormEvent) => { event.preventDefault(); const values = { name: form.name, description: form.description || null, imageUrl: form.imageUrl || null, categoryId: form.categoryId, price: Number(form.price), unit: form.unit, stock: form.stock === "" ? null : Number(form.stock), minQuantity: Number(form.minQuantity), quantityStep: Number(form.quantityStep), isPublished: form.isPublished, isAvailable: form.isAvailable, sortOrder: Number(form.sortOrder) }; if (editing) update.mutate({ id: editing, values }); else create.mutate(values); };
  return <div className="admin-content"><div className="admin-page-heading"><div><span className="eyebrow">كتالوج متجرك</span><h1>إدارة المنتجات</h1><p>أضف منتجاتك الحقيقية. لا يظهر أي منتج للعميل قبل نشره.</p></div><span className="admin-heading-mark"><Package size={25} /></span></div>
    <section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">{editing ? "✳" : "01"}</span><div><h2>{editing ? "تعديل المنتج" : "إضافة منتج"}</h2><p>الاسم والسعر والوحدة حقول أساسية، والصورة اختيارية.</p></div>{editing && <button className="small-button" onClick={() => { setEditing(null); setForm(blankProduct); }}>إلغاء التعديل<X size={14} /></button>}</div>
      <form onSubmit={submit} className="admin-form"><div className="product-form-layout"><div className="form-fields-grid"><label className="field-wide">اسم المنتج<input required maxLength={180} value={form.name} onChange={e => setField("name", e.target.value)} placeholder="اكتب اسم المنتج" /></label><label className="field-wide">الوصف<textarea rows={3} value={form.description} onChange={e => setField("description", e.target.value)} placeholder="وصف واضح للمنتج" /></label><label>السعر بالريال اليمني<input required type="number" min="0" value={form.price} onChange={e => setField("price", e.target.value)} placeholder="0" /></label><label>وحدة البيع<input required value={form.unit} onChange={e => setField("unit", e.target.value)} placeholder="حبة، كيلو، عبوة..." /></label><label>القسم<select value={form.categoryId ?? ""} onChange={e => setField("categoryId", e.target.value ? Number(e.target.value) : null)}><option value="">بلا قسم</option>{cats.data?.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label>الكمية المتوفرة<input type="number" min="0" value={form.stock} onChange={e => setField("stock", e.target.value)} placeholder="اتركه فارغًا إذا غير محدد" /></label><label>الحد الأدنى للكمية<input required type="number" min="1" value={form.minQuantity} onChange={e => setField("minQuantity", e.target.value)} /></label><label>خطوة الزيادة<input required type="number" min="1" value={form.quantityStep} onChange={e => setField("quantityStep", e.target.value)} /></label><label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setField("sortOrder", e.target.value)} /></label><label className="toggle-field"><input type="checkbox" checked={form.isPublished} onChange={e => setField("isPublished", e.target.checked)} /> نشر المنتج في المتجر</label><label className="toggle-field"><input type="checkbox" checked={form.isAvailable} onChange={e => setField("isAvailable", e.target.checked)} /> متاح للشراء</label></div><ImageField title="قص صورة المنتج" value={form.imageUrl} onChange={imageUrl => setField("imageUrl", imageUrl)} kind="product" aspect={1} /></div><div className="form-submit-row"><button className="button button-primary" disabled={create.isPending || update.isPending}>{create.isPending || update.isPending ? <LoaderCircle size={16} className="spin" /> : editing ? <Save size={16} /> : <Plus size={17} />}{editing ? "حفظ التعديلات" : "إضافة المنتج"}</button></div></form>
    </section>
    <div className="admin-section-heading"><div><h2>كل المنتجات</h2><p>المسودات مخفية عن العملاء.</p></div><span className="count-chip">{query.data?.length ?? 0}</span></div>
    {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !query.data?.length ? <AdminEmpty title="لا توجد منتجات بعد" text="أضف أول منتج من النموذج أعلاه؛ لا توجد بيانات تجريبية." /> : <div className="entity-list">{query.data.map(item => <article className="entity-row" key={item.id}><div className="entity-image">{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Leaf size={19} />}</div><div className="entity-main"><strong>{item.name}</strong><small>{cats.data?.find(cat => cat.id === item.categoryId)?.name || "بلا قسم"} · {item.unit} · {item.stock === null ? "المخزون غير محدد" : `المخزون ${item.stock}`}</small></div><div className="entity-price">{money(item.price)}</div><span className={`visibility-tag ${item.isPublished ? "visible" : "hidden"}`}>{item.isPublished ? "منشور" : "مسودة"}</span><div className="entity-actions"><button className="small-button" onClick={() => selectEdit(item)}>تعديل</button><button className="small-button" onClick={() => { setRecommended(item.id); setRecommendedIds([]); }}>شبيه</button><button className="small-button danger-soft" onClick={() => archive.mutate({ id: item.id })}>إخفاء</button></div>{recommended === item.id && <div className="recommendation-editor"><strong>اختر منتجات مقترحة</strong><div className="recommendation-options">{(query.data ?? []).filter(other => other.id !== item.id).map(other => <label key={other.id}><input type="checkbox" checked={recommendedIds.includes(other.id)} onChange={e => setRecommendedIds(current => e.target.checked ? [...current, other.id] : current.filter(id => id !== other.id))} />{other.name}</label>)}</div><button className="small-button selected" onClick={() => saveRecommendations.mutate({ productId: item.id, recommendedIds })}>حفظ التوصيات</button><button className="small-button" onClick={() => setRecommended(null)}>إلغاء</button></div>}</article>)}</div>}
  </div>;
}

function CategoriesPanel() {
  const utils = trpc.useUtils(); const query = trpc.commerce.admin.categories.list.useQuery(undefined, { retry: 1 });
  const [editing, setEditing] = useState<number | null>(null); const [form, setForm] = useState({ name: "", description: "", imageUrl: "", color: "#397a54", isActive: true, sortOrder: "0" });
  const create = trpc.commerce.admin.categories.create.useMutation({ onSuccess: async () => { toast.success("تم إنشاء القسم"); reset(); await utils.commerce.admin.categories.list.invalidate(); await utils.commerce.catalog.home.invalidate(); await utils.commerce.admin.overview.invalidate(); }, onError: error => toast.error(error.message) });
  const update = trpc.commerce.admin.categories.update.useMutation({ onSuccess: async () => { toast.success("تم تحديث القسم"); reset(); await utils.commerce.admin.categories.list.invalidate(); await utils.commerce.catalog.home.invalidate(); }, onError: error => toast.error(error.message) });
  const archive = trpc.commerce.admin.categories.archive.useMutation({ onSuccess: () => { toast.success("تم إيقاف القسم"); void utils.commerce.admin.categories.list.invalidate(); void utils.commerce.catalog.home.invalidate(); }, onError: error => toast.error(error.message) });
  const reset = () => { setEditing(null); setForm({ name: "", description: "", imageUrl: "", color: "#397a54", isActive: true, sortOrder: "0" }); };
  const submit = (event: React.FormEvent) => { event.preventDefault(); const values = { ...form, description: form.description || null, imageUrl: form.imageUrl || null, sortOrder: Number(form.sortOrder) }; if (editing) update.mutate({ id: editing, values }); else create.mutate(values); };
  return <div className="admin-content"><AdminHeading eyebrow="تنظيم المتجر" title="الأقسام" text="تحكم في أسماء الأقسام وصورها وألوانها وترتيبها وحالتها." icon={SlidersHorizontal} /><section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">{editing ? "✳" : "01"}</span><div><h2>{editing ? "تعديل القسم" : "إضافة قسم"}</h2><p>أضف الأقسام التي يحتاجها متجرك فقط.</p></div>{editing && <button className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}</div><form className="admin-form" onSubmit={submit}><div className="product-form-layout"><div className="form-fields-grid"><label>اسم القسم<input required maxLength={120} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label><label>لون تعبيري<input type="color" value={form.color} onChange={e => setForm({ ...form, color: e.target.value })} /></label><label className="field-wide">وصف (اختياري)<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label><label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: e.target.value })} /></label><label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> القسم مفعّل</label></div><ImageField title="قص صورة القسم" value={form.imageUrl} onChange={imageUrl => setForm({ ...form, imageUrl })} kind="category" aspect={4 / 5} /></div><div className="form-submit-row"><button className="button button-primary"><Plus size={16} />{editing ? "حفظ التعديلات" : "إنشاء القسم"}</button></div></form></section><div className="admin-section-heading"><div><h2>أقسامك</h2><p>يمكنك الإيقاف دون حذف المنتجات المرتبطة.</p></div><span className="count-chip">{query.data?.length ?? 0}</span></div>{query.isLoading ? <AdminLoading /> : !query.data?.length ? <AdminEmpty title="ابدأ بأول قسم" text="لم تُنشأ أقسام حتى الآن." /> : <div className="entity-list">{query.data.map(item => <article className="entity-row" key={item.id}><div className="entity-image" style={{ backgroundColor: `${item.color}16`, color: item.color }}>{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Leaf size={20} />}</div><div className="entity-main"><strong>{item.name}</strong><small>{item.description || "لا يوجد وصف"}</small></div><span className={`visibility-tag ${item.isActive ? "visible" : "hidden"}`}>{item.isActive ? "نشط" : "متوقف"}</span><div className="entity-actions"><button className="small-button" onClick={() => { setEditing(item.id); setForm({ name: item.name, description: item.description ?? "", imageUrl: item.imageUrl ?? "", color: item.color, isActive: item.isActive, sortOrder: String(item.sortOrder) }); window.scrollTo({ top: 0, behavior: "smooth" }); }}>تعديل</button><button className="small-button danger-soft" onClick={() => archive.mutate({ id: item.id })}>إيقاف</button></div></article>)}</div>}</div>;
}

function BannersPanel() {
  const utils = trpc.useUtils(); const query = trpc.commerce.admin.banners.list.useQuery(undefined, { retry: 1 });
  const blank = { title: "", body: "", imageUrl: "", actionText: "", actionUrl: "", isActive: false, sortOrder: "0" };
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState(blank);
  const reset = () => { setEditing(null); setForm(blank); };
  const refresh = async () => { await utils.commerce.admin.banners.list.invalidate(); await utils.commerce.catalog.home.invalidate(); };
  const create = trpc.commerce.admin.banners.create.useMutation({ onSuccess: async () => { toast.success("تم حفظ الإعلان"); reset(); await refresh(); }, onError: error => toast.error(error.message) });
  const update = trpc.commerce.admin.banners.update.useMutation({ onSuccess: async () => { toast.success("تم تحديث الإعلان"); reset(); await refresh(); }, onError: error => toast.error(error.message) });
  const remove = trpc.commerce.admin.banners.delete.useMutation({ onSuccess: () => { toast.success("حُذف الإعلان"); void utils.commerce.admin.banners.list.invalidate(); void utils.commerce.catalog.home.invalidate(); } });
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const values = { title: form.title, body: form.body || null, imageUrl: form.imageUrl || null, actionText: form.actionText || null, actionUrl: form.actionUrl || null, isActive: form.isActive, sortOrder: Number(form.sortOrder) };
    if (editing) update.mutate({ id: editing, values });
    else create.mutate({ ...form, imageUrl: form.imageUrl || undefined, body: form.body || undefined, actionText: form.actionText || undefined, actionUrl: form.actionUrl || undefined, sortOrder: Number(form.sortOrder) });
  };
  const edit = (item: NonNullable<typeof query.data>[number]) => { setEditing(item.id); setForm({ title: item.title, body: item.body ?? "", imageUrl: item.imageUrl ?? "", actionText: item.actionText ?? "", actionUrl: item.actionUrl ?? "", isActive: item.isActive, sortOrder: String(item.sortOrder) }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  return <div className="admin-content"><AdminHeading eyebrow="واجهة المتجر" title="الإعلانات الرئيسية" text="أضف صورك بنفسك. الإعلان لا يظهر للعميل إلا إذا كانت له صورة وحالة النشر مفعّلة." icon={Megaphone} /><section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">{editing ? "✳" : "01"}</span><div><h2>{editing ? "تعديل الإعلان" : "إعلان جديد"}</h2><p>الصورة تُقص تلقائيًا داخل إطار أفقي ثابت.</p></div>{editing && <button type="button" className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}</div><form className="admin-form" onSubmit={submit}><div className="product-form-layout"><div className="form-fields-grid"><label className="field-wide">العنوان<input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label><label className="field-wide">النص فوق الصورة<textarea rows={2} value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} /></label><label>نص الزر (اختياري)<input value={form.actionText} onChange={e => setForm({ ...form, actionText: e.target.value })} /></label><label>وجهة الزر<input value={form.actionUrl} onChange={e => setForm({ ...form, actionUrl: e.target.value })} placeholder="/products" /></label><label>ترتيب العرض<input type="number" value={form.sortOrder} onChange={e => setForm({ ...form, sortOrder: e.target.value })} /></label><label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> نشر عند حفظ الصورة</label></div><ImageField title="قص صورة الإعلان المستطيلة" value={form.imageUrl} onChange={imageUrl => setForm({ ...form, imageUrl })} kind="banner" aspect={2.65} /></div><div className="form-submit-row"><button className="button button-primary" disabled={create.isPending || update.isPending}>{create.isPending || update.isPending ? <LoaderCircle className="spin" size={16} /> : editing ? <Save size={16} /> : <Plus size={16} />}{editing ? "حفظ تعديل الإعلان" : "حفظ الإعلان"}</button></div></form></section><div className="admin-section-heading"><div><h2>الإعلانات المحفوظة</h2><p>يمكن تفعيل عدة إعلانات وترتيبها.</p></div></div>{!query.data?.length ? <AdminEmpty title="لا توجد إعلانات" text="ستبقى واجهة المتجر نظيفة حتى ترفع إعلانك الأول." /> : <div className="entity-list">{query.data.map(item => <article className="entity-row" key={item.id}><div className="entity-image">{item.imageUrl ? <img src={item.imageUrl} alt="" /> : <Megaphone size={19} />}</div><div className="entity-main"><strong>{item.title}</strong><small>{item.body || "لا يوجد نص"} · ترتيب {item.sortOrder}</small></div><label className="toggle-field compact-toggle"><input type="checkbox" checked={item.isActive} onChange={e => update.mutate({ id: item.id, values: { isActive: e.target.checked } })} /> نشط</label><div className="entity-actions"><button className="small-button" onClick={() => edit(item)}>تعديل</button><button className="small-button danger-soft" onClick={() => remove.mutate({ id: item.id })}>حذف</button></div></article>)}</div>}</div>;
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
  const remove = trpc.commerce.admin.offers.delete.useMutation({ onSuccess: () => { void utils.commerce.admin.offers.list.invalidate(); void utils.commerce.catalog.home.invalidate(); } });
  const toLocal = (date: Date | string | null) => date ? new Date(date).toISOString().slice(0, 16) : "";
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (form.startsAt && form.endsAt && new Date(form.startsAt) > new Date(form.endsAt)) { toast.error("تاريخ نهاية العرض يجب أن يكون بعد تاريخ بدايته."); return; }
    const values = { title: form.title, description: form.description || null, code: form.code.trim().toUpperCase(), discountType: form.discountType, discountValue: Number(form.discountValue), minimumOrder: Number(form.minimumOrder), startsAt: form.startsAt ? new Date(form.startsAt).toISOString() : null, endsAt: form.endsAt ? new Date(form.endsAt).toISOString() : null, isActive: form.isActive };
    if (editing) update.mutate({ id: editing, values }); else create.mutate({ ...values, description: form.description || undefined });
  };
  const edit = (item: NonNullable<typeof query.data>[number]) => { setEditing(item.id); setForm({ title: item.title, description: item.description ?? "", code: item.code, discountType: item.discountType, discountValue: String(item.discountValue), minimumOrder: String(item.minimumOrder), startsAt: toLocal(item.startsAt), endsAt: toLocal(item.endsAt), isActive: item.isActive }); window.scrollTo({ top: 0, behavior: "smooth" }); };
  return <div className="admin-content"><AdminHeading eyebrow="تحفيز الشراء" title="العروض والخصومات" text="الخصم يطبّق ويُعاد حسابه على الخادم عند تقديم الطلب." icon={BadgePercent} /><section className="admin-form-card"><div className="form-card-heading"><span className="form-card-number">{editing ? "✳" : "01"}</span><div><h2>{editing ? "تعديل العرض" : "إنشاء عرض"}</h2><p>لا توجد عروض افتراضية؛ أضف شروط العرض بنفسك.</p></div>{editing && <button type="button" className="small-button" onClick={reset}>إلغاء التعديل<X size={14} /></button>}</div><form className="admin-form" onSubmit={submit}><div className="form-fields-grid"><label>اسم العرض<input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label><label>رمز الخصم<input required value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} /></label><label className="field-wide">وصف العرض<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label><label>نوع الخصم<select value={form.discountType} onChange={e => setForm({ ...form, discountType: e.target.value as "percent" | "fixed" })}><option value="percent">نسبة مئوية</option><option value="fixed">قيمة ثابتة</option></select></label><label>{form.discountType === "percent" ? "النسبة %" : "قيمة الخصم ر.ي"}<input type="number" min="1" max={form.discountType === "percent" ? "100" : undefined} required value={form.discountValue} onChange={e => setForm({ ...form, discountValue: e.target.value })} /></label><label>الحد الأدنى للطلب ر.ي<input type="number" min="0" step="1" value={form.minimumOrder} onChange={e => setForm({ ...form, minimumOrder: e.target.value })} /></label><label>يبدأ العرض<input type="datetime-local" value={form.startsAt} onChange={e => setForm({ ...form, startsAt: e.target.value })} /></label><label>ينتهي العرض<input type="datetime-local" value={form.endsAt} onChange={e => setForm({ ...form, endsAt: e.target.value })} /></label><label className="toggle-field"><input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} /> العرض فعّال</label></div><div className="form-submit-row"><button className="button button-primary" disabled={create.isPending || update.isPending}>{create.isPending || update.isPending ? <LoaderCircle className="spin" size={16} /> : editing ? <Save size={16} /> : <Plus size={16} />}{editing ? "حفظ تعديل العرض" : "إنشاء العرض"}</button></div></form></section><div className="admin-section-heading"><div><h2>العروض الحالية</h2><p>رموز العرض تُفحص عند إرسال الطلب.</p></div></div>{!query.data?.length ? <AdminEmpty title="لا توجد عروض مضافة" text="يمكنك إضافة رمز خصم متى أردت." /> : <div className="entity-list">{query.data.map(item => <article className="entity-row" key={item.id}><div className="entity-image offer-art"><BadgePercent size={20} /></div><div className="entity-main"><strong>{item.title}</strong><small>{item.code} · {item.discountType === "percent" ? `${item.discountValue}%` : money(item.discountValue)} · حد أدنى {money(item.minimumOrder)} · {item.startsAt ? new Date(item.startsAt).toLocaleDateString("ar-YE") : "دون بداية محددة"} — {item.endsAt ? new Date(item.endsAt).toLocaleDateString("ar-YE") : "دون انتهاء محدد"}</small></div><label className="toggle-field compact-toggle"><input type="checkbox" checked={item.isActive} onChange={e => update.mutate({ id: item.id, values: { isActive: e.target.checked } })} /> فعّال</label><div className="entity-actions"><button className="small-button" onClick={() => edit(item)}>تعديل</button><button className="small-button danger-soft" onClick={() => remove.mutate({ id: item.id })}>حذف</button></div></article>)}</div>}</div>;
}

function OrdersPanel() {
  const utils = trpc.useUtils();
  const query = trpc.commerce.admin.orders.list.useQuery(undefined, { retry: 1 });
  const nextStates: Record<string, string[]> = { new: ["preparing", "cancelled"], preparing: ["ready", "cancelled"], ready: ["out_for_delivery", "cancelled"], out_for_delivery: ["delivered"], delivered: [], cancelled: [] };
  const [deliveryNotes, setDeliveryNotes] = useState<Record<number, string>>({});
  const change = trpc.commerce.admin.orders.setStatus.useMutation({ onSuccess: async () => { toast.success("تم تحديث حالة الطلب"); await Promise.all([utils.commerce.admin.orders.list.invalidate(), utils.commerce.admin.overview.invalidate(), utils.commerce.orders.mine.invalidate(), utils.commerce.catalog.home.invalidate(), utils.commerce.catalog.listProducts.invalidate()]); }, onError: error => toast.error(error.message) });
  const exportOrders = () => {
    if (!query.data?.length) return;
    const quote = (value: string | number | null | undefined) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows: Array<Array<string | number | null | undefined>> = [
      ["رقم الطلب", "التاريخ", "المستلم", "الهاتف", "المدينة", "الحي", "الحالة", "المجموع الفرعي", "التوصيل", "الخصم", "الإجمالي", "طريقة الدفع", "الأصناف"],
      ...query.data.map(order => [order.orderNumber, new Date(order.createdAt).toLocaleString("ar-YE"), order.recipientName, order.phone, order.city, order.district, labels[order.status], order.subtotal, order.deliveryFee, order.discount, order.total, "نقدًا عند الاستلام", order.items.map(item => `${item.productName} × ${item.quantity}`).join("; ")]),
    ];
    const blob = new Blob(["\uFEFF", rows.map(row => row.map(quote).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `original-orders-${new Date().toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="admin-content">
    <AdminHeading eyebrow="من لحظة الطلب حتى التسليم" title="إدارة الطلبات" text="حدّث الحالة بالتسلسل، وستظهر للعميل في صفحة طلباتي." icon={ClipboardList} />
    {query.data?.length ? <div className="admin-actions-row admin-export-row"><span className="subtle-note">{query.data.length} طلبًا · التصدير يشمل البيانات التي حمّلتها اللوحة</span><button className="small-button" onClick={exportOrders}><Download size={15} />تصدير CSV</button></div> : null}
    {query.isLoading ? <AdminLoading /> : query.error ? <AdminError message={query.error.message} retry={() => void query.refetch()} /> : !query.data?.length ? <AdminEmpty title="لا توجد طلبات" text="ستظهر الطلبات الجديدة هنا بعد تفعيل إعدادات التوصيل." /> : <div className="admin-orders">{query.data.map(order => {
      const allowedStatuses = [order.status, ...(nextStates[order.status] ?? [])];
      return <article className="admin-order-card" key={order.id}>
        <div className="admin-order-top"><div><strong className="order-number">{order.orderNumber}</strong><small>{new Date(order.createdAt).toLocaleString("ar-YE")}</small></div><span className={`status-pill status-${order.status}`}>{labels[order.status]}</span></div>
        <div className="admin-order-customer"><strong>{order.recipientName}</strong><span>{order.phone}</span><span>{order.city}، {order.district}</span>{order.addressDetails && <small>{order.addressDetails}</small>}{order.customerNote && <small>ملاحظة العميل: {order.customerNote}</small>}</div>
        <div className="admin-order-lines">{order.items.map(item => <span key={item.id}>{item.productName} × {item.quantity} · {money(item.lineTotal)}</span>)}</div>
        <div className="admin-order-total"><span>فرعي {money(order.subtotal)} · توصيل {money(order.deliveryFee)}{order.discount ? ` · خصم ${money(order.discount)}` : ""}</span><strong>{money(order.total)}</strong></div>
        <div className="admin-order-controls"><label>حالة الطلب<select value={order.status} disabled={order.status === "delivered" || order.status === "cancelled" || change.isPending} onChange={e => change.mutate({ id: order.id, status: e.target.value as "new" | "preparing" | "ready" | "out_for_delivery" | "delivered" | "cancelled", note: deliveryNotes[order.id]?.trim() || undefined }, { onSuccess: () => setDeliveryNotes(current => ({ ...current, [order.id]: "" })) })}>{Object.entries(labels).filter(([value]) => allowedStatuses.includes(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><span className="cod-note small"><Truck size={15} /> نقدًا عند الاستلام</span></div>
        <label className="admin-order-delivery-note"><span>ملاحظة للعميل (اختياري)</span><input maxLength={500} value={deliveryNotes[order.id] ?? ""} onChange={e => setDeliveryNotes(current => ({ ...current, [order.id]: e.target.value }))} placeholder="مثال: خرج للتوصيل باتجاه الحي..." disabled={order.status === "delivered" || order.status === "cancelled"} /><small>تُرسل مع إشعار تغيير الحالة وتظهر في سجل طلباتي.</small></label>
        {order.events.length ? <details className="order-history"><summary>سجل تغييرات الحالة</summary><ol>{order.events.map(event => <li key={event.id}><span className={`status-pill status-${event.status}`}>{labels[event.status]}</span><time>{new Date(event.createdAt).toLocaleString("ar-YE")}</time>{event.note && <small>{event.note}</small>}</li>)}</ol></details> : null}
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
function AdminPanel({ section }: { section: Section }) {
  if (section === "chats") return <ChatsPanel />;
  if (section === "products") return <ProductsPanel />;
  if (section === "categories") return <CategoriesPanel />;
  if (section === "banners") return <BannersPanel />;
  if (section === "offers") return <OffersPanel />;
  if (section === "orders") return <OrdersPanel />;
  if (section === "users") return <UsersPanel />;
  if (section === "settings") return <SettingsPanel />;
  return <Overview />;
}

export default function Admin() {
  const [location, navigate] = useLocation(); const auth = useAuth();
  const access = trpc.commerce.access.useQuery(undefined, { retry: 1, refetchOnWindowFocus: false });
  const sectionName = location.split("/")[2] as Section | undefined;
  const section = sections.some(item => item.id === sectionName) ? sectionName! : "overview";
  const logout = async () => { try { await auth.logout(); } finally { navigate("/"); } };
  if (auth.loading || access.isLoading) return <main className="admin-gate" dir="rtl"><AdminLoading /></main>;
  if (auth.error && !auth.user) return <AdminLoginGate reason="login" />;
  if (!auth.user) return <AdminLoginGate reason="login" />;
  if (auth.user.suspended) return <AdminLoginGate reason="suspended" />;
  if (!access.data?.isAdmin) return <AdminLoginGate reason="forbidden" onLogout={logout} />;
  return <div className="admin-app" dir="rtl"><aside className="admin-sidebar"><Link href="/" className="admin-brand"><span className="brand-mark"><Leaf size={20} /></span><span><strong>ORIGINAL</strong><small>لوحة المالك</small></span></Link><div className="admin-profile"><span className="profile-initial">{(auth.user.name || "O").slice(0, 1)}</span><span><strong>{auth.user.name || "مالك المتجر"}</strong><small>إدارة المتجر</small></span><span className="online-dot" /></div><nav className="admin-nav">{sections.map(item => { const Icon = item.icon; return <button key={item.id} className={section === item.id ? "active" : ""} onClick={() => navigate(item.id === "overview" ? "/admin" : `/admin/${item.id}`)}><Icon size={18} /><span>{item.label}</span>{section === item.id && <i />}</button>; })}</nav><div className="admin-sidebar-bottom"><Link href="/" className="back-store"><ShoppingBag size={16} />عرض المتجر<ArrowLeft size={14} /></Link><button className="logout-admin" onClick={logout}><LogOut size={16} />تسجيل الخروج</button><small>بيانات المتجر محفوظة على الخادم</small></div></aside><main className="admin-main"><header className="admin-topbar"><button className="admin-menu-button" onClick={() => document.body.classList.toggle("admin-menu-open")}><ChevronDown size={18} />القائمة</button><span className="admin-breadcrumb">أوريجنال <span>/</span> {sections.find(item => item.id === section)?.label}</span><Link className="small-button" href="/">فتح المتجر<ArrowLeft size={14} /></Link></header><OwnerNotificationControl /><AdminPanel section={section} /></main><div className="admin-mobile-backdrop" onClick={() => document.body.classList.remove("admin-menu-open")} /></div>;
}
