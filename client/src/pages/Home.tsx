
const INSTANT_CATALOG_KEY = "original-instant-catalog-v3";
function getInstantLocalCatalog(): HomeData {
  try {
    const raw = localStorage.getItem(INSTANT_CATALOG_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if (p && Array.isArray(p.products)) return p;
    }
  } catch {}
  return { categories: [], products: [], banners: [], offers: [], settings: {} };
}

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useSearch } from "wouter";
import {
  ArrowDownWideNarrow, ArrowLeft, ArrowUpDown, BadgePercent, BellRing, Check, ChevronLeft, CircleUserRound, Copy,
  Heart, Home as HomeIcon, Leaf, LoaderCircle, MapPin, Menu, MessageCircle, Minus, Package,
  Plus, Search, ShoppingBag, ShoppingCart, SlidersHorizontal, Sparkles, Trash2, Truck, UserRound,
  X, Bot, Clock3, ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";
import { useStore, type CartLine } from "@/contexts/StoreContext";
import { clearPendingOrderIdempotencyKey, getPendingOrderIdempotencyKey, useCustomer } from "@/contexts/CustomerContext";
import PWAInstall from "@/components/PWAInstall";
import { buildMissingIngredientNote } from "@/lib/assistant-note";
import { ensureBrowserPushSubscription, getExistingBrowserPushSubscription, getPushPermissionState, requestPushPermission } from "@/lib/pushNotifications";

const formatPrice = (amount: number) => `${Math.max(0, amount).toLocaleString("en-US")} ر.ي`;
const stateLabels: Record<string, string> = { new: "جديد", preparing: "قيد التجهيز", ready: "جاهز للتوصيل", out_for_delivery: "خرج للتوصيل", delivered: "تم التسليم", cancelled: "ملغي" };

function useDebouncedValue<T>(value: T, delay = 220) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => { const timer = window.setTimeout(() => setDebounced(value), delay); return () => window.clearTimeout(timer); }, [value, delay]);
  return debounced;
}

type PublicProduct = { id: number; name: string; slug: string; description: string | null; imageUrl: string | null; categoryId: number | null; price: number; unit: string; stock: number | null; minQuantity: number; quantityStep: number; isPublished: boolean; isAvailable: boolean; sortOrder: number; createdAt: Date; updatedAt: Date };

type HomeData = { categories: Array<{ id: number; name: string; description: string | null; imageUrl: string | null; color: string; slug: string }>; products: PublicProduct[]; banners: Array<{ id: number; title: string; body: string | null; imageUrl: string | null; actionText: string | null; actionUrl: string | null }>; offers: Array<{ id: number; title: string; description: string | null; code: string; discountType: string; discountValue: number }>; settings: Record<string, string> };

function Header({ data, onSearch }: { data?: HomeData; onSearch: (text: string) => void }) {
  const { cart } = useStore();
  const { name } = useCustomer();
  const [text, setText] = useState("");
  const cartCount = cart.reduce((sum, row) => sum + row.quantity, 0);
  const storeName = data?.settings.storeName || "ORIGINAL – أوريجنال";
  const brandSubtitle = storeName === "ORIGINAL – أوريجنال" ? "أوريجنال" : storeName;
  const submitSearch = (event: FormEvent) => { event.preventDefault(); onSearch(text.trim()); };
  return <header className="store-header">
    <div className="header-main">
      <Link href="/" className="brand-lockup" aria-label={`${storeName} الرئيسية`}>
        <span className={`brand-mark ${data?.settings.storeIconUrl ? "has-brand-image" : ""}`}>{data?.settings.storeIconUrl ? <img src={data.settings.storeIconUrl} alt="" /> : <Leaf size={22} strokeWidth={1.8} />}</span>
        <span className="brand-type"><strong>ORIGINAL</strong><small>{brandSubtitle}</small></span>
      </Link>
      <form className="header-search" onSubmit={submitSearch}>
        <Search size={18} /><input value={text} onChange={event => setText(event.target.value)} placeholder="ابحث عن احتياجاتك..." aria-label="البحث عن المنتجات" />
        {text && <button type="button" className="search-clear" onClick={() => { setText(""); onSearch(""); }} aria-label="مسح البحث"><X size={14} /></button>}
      </form>
      <div className="header-actions">
        <Link href="/favorites" className="header-action mobile-header-shortcut" aria-label="المفضلة" title="المفضلة"><Heart size={19} /><span>المفضلة</span></Link>
        <Link href="/orders" className="header-action mobile-header-shortcut" aria-label="طلباتي" title="طلباتي"><Package size={19} /><span>طلباتي</span></Link>
        <Link href="/cart" className="header-cart"><ShoppingCart size={19} /><span>السلة</span>{cartCount > 0 && <b>{cartCount}</b>}</Link>
        <Link href="/account" className="account-chip"><CircleUserRound size={19} /><span>{name.trim().split(/\s+/)[0] || "حسابي"}</span></Link>
      </div>
    </div>
    <div className="header-subline">
      <nav className="desktop-links" aria-label="القائمة الرئيسية"><Link href="/">الرئيسية</Link><Link href="/categories">الأقسام</Link><Link href="/products">المنتجات</Link><Link href="/assistant" className="assistant-link"><Sparkles size={15} /> مساعد أوريجنال</Link></nav>
      <div className="header-promise"><ShieldCheck size={15} /><span></span></div><PWAInstall />
    </div>
    {data?.settings.orderPaused === "true" && <div className="service-notice"><Clock3 size={15} />{data.settings.pausedMessage || "استقبال الطلبات متوقف مؤقتًا"}</div>}
  </header>;
}

function BottomNav({ active }: { active: string }) {
  const links = [
    { href: "/", label: "الرئيسية", icon: HomeIcon },
    { href: "/categories", label: "الأقسام", icon: SlidersHorizontal },
    { href: "/assistant", label: "المساعد", icon: Sparkles, standout: true },
    { href: "/products", label: "المنتجات", icon: ShoppingBag },
    { href: "/account", label: "حسابي", icon: UserRound },
  ];
  return <nav className="bottom-nav" aria-label="التنقل"><div className="bottom-nav-inner">{links.map(item => {
    const Icon = item.icon;
    return <Link key={item.href} href={item.href} className={`bottom-nav-link ${active === item.href ? "is-active" : ""} ${item.standout ? "nav-assistant" : ""}`}><span className="bottom-icon"><Icon size={item.standout ? 21 : 19} /></span><small>{item.label}</small></Link>;
  })}</div></nav>;
}

function EmptyState({ icon: Icon = Package, title, description, action, href }: { icon?: typeof Package; title: string; description: string; action?: string; href?: string }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={25} strokeWidth={1.6} /></span><h3>{title}</h3><p>{description}</p>{action && href && <Link href={href} className="button button-primary">{action}<ArrowLeft size={16} /></Link>}</div>;
}

function BannerCarousel({ banners }: { banners: HomeData["banners"] }) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (banners.length < 2) return;
    const timer = window.setInterval(() => setIndex(value => (value + 1) % banners.length), 5200);
    return () => window.clearInterval(timer);
  }, [banners.length]);
  if (!banners.length) return null;
  const banner = banners[index % banners.length];
  if (!banner?.imageUrl) return null;
  return <section className="banner-frame" aria-label="إعلانات المتجر">
    <img src={banner.imageUrl} alt={banner.title} loading="eager" fetchPriority="high" decoding="async" />
    <div className="banner-shade" />
    <div className="banner-copy"><span className="eyebrow eyebrow-light">من أوريجنال إليك</span><h2>{banner.title}</h2>{banner.body && <p>{banner.body}</p>}{banner.actionText && banner.actionUrl && <a href={banner.actionUrl} className="button button-light">{banner.actionText}<ArrowLeft size={16} /></a>}</div>
    {banners.length > 1 && <div className="banner-dots">{banners.map((item, dot) => <button key={item.id} className={dot === index ? "active" : ""} aria-label={`الإعلان ${dot + 1}`} onClick={() => setIndex(dot)} />)}</div>}
  </section>;
}


function AiThinkingStatus(_props: { queryText?: string }) {
  return (
    <div className="ai-thinking-shimmer" aria-live="polite" style={{ fontWeight: 400, fontSize: "12px", color: "#687d6e", display: "inline-flex", alignItems: "center", gap: "4px", background: "transparent", border: "none", boxShadow: "none", padding: "4px 2px" }}>
      <span style={{ animation: "pulse 1.3s infinite ease-in-out", fontWeight: 400 }}>جاري التفكير...</span>
    </div>
  );
}

function GradualText({ text, animate = true }: { text: string; animate?: boolean }) {
  const words = useMemo(() => (text || "").split(/(\s+)/), [text]);
  const [count, setCount] = useState(() => (animate ? 2 : words.length));
  useEffect(() => {
    if (!animate) { setCount(words.length); return; }
    setCount(2);
    const step = Math.max(2, Math.ceil(words.length / 34));
    const timer = window.setInterval(() => {
      setCount(c => {
        if (c >= words.length) { window.clearInterval(timer); return words.length; }
        return Math.min(words.length, c + step);
      });
    }, 25);
    return () => window.clearInterval(timer);
  }, [text, animate, words.length]);
  return <span>{words.slice(0, count).join("")}</span>;
}

function AiRecipeModal({ product, onClose }: { product: PublicProduct; onClose: () => void }) {
  const { add } = useStore();
  const [, navigate] = useLocation();
  const [customInput, setCustomInput] = useState("");
  const [activeMod, setActiveMod] = useState("");
  const recipeMutation = trpc.commerce.assistant.recipe.useMutation();

  const askForProduct = (modification = "") => {
    setActiveMod(modification);
    const baseReq = `تحليل المنتج «${product.name}»`;
    recipeMutation.mutate({
      request: modification ? `${baseReq} السؤال المطلوب: ${modification}` : baseReq,
    });
  };

  useEffect(() => {
    askForProduct("");
  }, [product.id]);

  const data = recipeMutation.data as (typeof recipeMutation.data & { suggestedQuestions?: string[] }) | undefined;
  const isPending = recipeMutation.isPending;
  const suggestions = data?.suggestedQuestions?.length
    ? data.suggestedQuestions
    : ["كيف أحضر حلى حلو؟", "كم كمية السعرات؟"];

  const continueInAssistantChat = () => {
    try {
      const existingRaw = localStorage.getItem("original-assistant-history-v2");
      const existing = existingRaw ? JSON.parse(existingRaw) : [];
      const historyArr = Array.isArray(existing) ? existing : [];
      const userTurn = {
        role: "user",
        text: activeMod
          ? `سؤال عن «${product.name}»: ${activeMod}`
          : `حدثني عن «${product.name}»`,
      };
      const assistantTurn = data
        ? {
            role: "assistant",
            text: data.message,
            contextText: `نتحدث عن منتج ${product.name}`,
          }
        : null;
      const nextHistory = [...historyArr, userTurn, ...(assistantTurn ? [assistantTurn] : [])].slice(-32);
      localStorage.setItem("original-assistant-history-v2", JSON.stringify(nextHistory));
    } catch {}
    onClose();
    navigate("/assistant");
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="checkout-modal" role="dialog" aria-modal="true" style={{ maxWidth: "540px" }}>
        <div className="modal-heading">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ width: "36px", height: "36px", borderRadius: "12px", background: "#edf3e9", color: "#174b36", display: "grid", placeItems: "center" }}>
              <Sparkles size={20} />
            </span>
            <div>
              <span className="eyebrow">مساعد أوريجنال الذكي</span>
              <h2 style={{ fontSize: "16px" }}>{product.name}</h2>
            </div>
          </div>
          <button type="button" className="icon-button" onClick={onClose}><X size={19} /></button>
        </div>

        <div style={{ maxHeight: "72vh", overflowY: "auto", padding: "10px 4px", fontSize: "13px", lineHeight: "1.85" }}>
          {isPending ? (
            <div style={{ padding: "16px 4px" }}>
              <AiThinkingStatus queryText={activeMod ? `«${product.name}» ${activeMod}` : `«${product.name}»`} />
            </div>
          ) : data ? (
            <div>
              <div style={{ background: "#f5f8f3", border: "1px solid #dce8d8", borderRadius: "16px", padding: "14px 16px", marginBottom: "12px", whiteSpace: "pre-line", color: "#1d3528", fontSize: "13px" }}>
                <GradualText text={data.message} animate={true} />
              </div>

              {data.recipe && (
                <div className="recipe-card" style={{ width: "100%", marginBottom: "12px" }}>
                  <span className="eyebrow">طريقة التحضير بالتفصيل</span>
                  <h3 style={{ fontSize: "15px", margin: "4px 0" }}>{data.recipe.name}</h3>
                  <small style={{ color: "#687d6e", display: "block", marginBottom: "8px" }}>تكفي {data.recipe.servings} أشخاص</small>
                  {data.recipe.steps.length > 0 && (
                    <ol style={{ paddingInlineStart: "20px", margin: "8px 0" }}>
                      {data.recipe.steps.map((step, idx) => (
                        <li key={idx} style={{ marginBottom: "6px" }}>{step}</li>
                      ))}
                    </ol>
                  )}
                </div>
              )}

              {data.ingredients && data.ingredients.length > 0 && (
                <div style={{ background: "#edf3e9", borderRadius: "14px", padding: "12px", marginBottom: "12px" }}>
                  <strong style={{ fontSize: "12px", color: "#174b36", display: "block", marginBottom: "8px" }}>
                    الأصناف المتوفرة في المتجر:
                  </strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {data.ingredients.map(ing => (
                      <div key={ing.productId} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", background: "#fff", padding: "7px 10px", borderRadius: "8px" }}>
                        <span>{ing.name} ({ing.quantity} {ing.unit})</span>
                        <strong style={{ color: "#174b36" }}>{formatPrice(ing.price * ing.quantity)}</strong>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    className="button button-primary full-button"
                    style={{ marginTop: "10px" }}
                    onClick={() => {
                      let count = 0;
                      data.ingredients.forEach(ing => {
                        add({ id: ing.productId, name: ing.name, price: ing.price, unit: ing.unit, stock: ing.stock, minQuantity: ing.minQuantity, quantityStep: ing.quantityStep }, ing.quantity);
                        count++;
                      });
                      toast.success(`تمت إضافة ${count} صنف إلى سلتك!`);
                    }}
                  >
                    <ShoppingCart size={16} /> إضافة للسلة
                  </button>
                </div>
              )}

              {suggestions.length > 0 && (
                <div style={{ marginBottom: "14px" }}>
                  <small style={{ display: "block", color: "#526b5c", fontWeight: 700, marginBottom: "7px", fontSize: "11px" }}>
                    اختر سؤالك التالي:
                  </small>
                  <div style={{ display: "flex", gap: "7px", flexWrap: "wrap" }}>
                    {suggestions.map(sug => (
                      <button
                        key={sug}
                        type="button"
                        disabled={isPending}
                        onClick={() => askForProduct(sug)}
                        style={{
                          padding: "8px 13px",
                          borderRadius: "12px",
                          border: activeMod === sug ? "1.5px solid #174b36" : "1px solid #c5d6c7",
                          background: activeMod === sug ? "#174b36" : "#ffffff",
                          color: activeMod === sug ? "#ffffff" : "#174b36",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                          boxShadow: "0 3px 10px rgba(23, 75, 54, 0.08)",
                        }}
                      >
                        <Sparkles size={13} style={{ display: "inline", marginLeft: "5px", verticalAlign: "-2px" }} />
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <form
                onSubmit={e => {
                  e.preventDefault();
                  if (!customInput.trim() || isPending) return;
                  askForProduct(customInput.trim());
                  setCustomInput("");
                }}
                style={{ display: "flex", gap: "6px", marginBottom: "10px" }}
              >
                <input
                  value={customInput}
                  onChange={e => setCustomInput(e.target.value)}
                  placeholder="اسأل أي سؤال عن هذا المنتج (سعرات، طريقة تحضير، فوائد...)"
                  style={{ flex: 1, minHeight: "38px", padding: "0 12px", borderRadius: "11px", border: "1px solid #cdd9cb", fontSize: "12px" }}
                />
                <button type="submit" className="button button-primary" disabled={!customInput.trim() || isPending} style={{ minHeight: "38px", padding: "0 14px" }}>
                  إرسال
                </button>
              </form>

              <button
                type="button"
                className="button button-outline full-button"
                onClick={continueInAssistantChat}
              >
                <Sparkles size={16} /> متابعة الحوار في صفحة المساعد الذكي
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function ProductCard({ product, onOpen, onAiRecipe }: { product: PublicProduct; onOpen: () => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const { add, isFavorite, toggleFavorite } = useStore();
  const favorite = isFavorite(product.id);
  const disabled = product.stock !== null && product.stock < (product.minQuantity || 1);
  return <article className="product-card">
    <div className="product-visual" onClick={onOpen} role="button" tabIndex={0} onKeyDown={event => { if (event.key === "Enter") onOpen(); }}>
      {product.imageUrl ? <img src={product.imageUrl} alt={product.name} loading="lazy" /> : <div className="product-no-image"><Leaf size={27} strokeWidth={1.4} /><span>صورة المنتج</span></div>}
      <button type="button" className={`favorite-toggle ${favorite ? "is-favorite" : ""}`} aria-label={favorite ? "إزالة من المفضلة" : "أضف للمفضلة"} aria-pressed={favorite} onClick={event => { event.stopPropagation(); toggleFavorite(product.id); toast.success(favorite ? "أُزيل من المفضلة" : "أُضيف إلى المفضلة على هذا الجهاز"); }}><Heart size={17} fill={favorite ? "currentColor" : "none"} /></button>
      {onAiRecipe && <button type="button" className="ai-recipe-toggle" aria-label="أفكار وتحضير بالذكاء الاصطناعي" title="أفكار ووصفات تحضير" onClick={event => { event.stopPropagation(); onAiRecipe(product); }}><Sparkles size={16} /></button>}
      {disabled && <span className="product-sold-out">غير متوفر</span>}
    </div>
    <button type="button" className="product-title-button" onClick={onOpen}><strong>{product.name}</strong><span>{product.unit}</span></button>
    <div className="product-card-bottom"><div><b>{formatPrice(product.price)}</b><small> / {product.unit}</small></div><button className="add-button" disabled={disabled} onClick={() => { add(product, product.minQuantity || 1); toast.success("أُضيف إلى السلة"); }} aria-label={`إضافة ${product.name} للسلة`}><Plus size={18} /></button></div>
  </article>;
}

function ProductGrid({ items, onOpen, onAiRecipe }: { items: PublicProduct[]; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void }) {
  if (!items.length) return <EmptyState icon={ShoppingBag} title="المتجر ينتظر منتجاته الأولى" description="لا توجد منتجات منشورة بعد. ستظهر الأصناف هنا بعد أن تضيفها من لوحة الإدارة." action="تصفح الأقسام" href="/categories" />;
  return <div className="product-grid">{items.map(product => <ProductCard key={product.id} product={product} onOpen={() => onOpen(product.id)} onAiRecipe={onAiRecipe} />)}</div>;
}

function CategoryStrip({ data, onSelect }: { data: HomeData["categories"]; onSelect: (id: number) => void }) {
  if (!data.length) return <div className="category-empty"><span className="category-empty-mark"><SlidersHorizontal size={19} /></span><div><strong>الأقسام قيد التجهيز</strong><p>أضف أقسام متجرك لتبدأ ترتيب المنتجات.</p></div><Link href="/categories"><ChevronLeft size={18} /></Link></div>;
  return <div className="category-strip">{data.map((category, i) => <button key={category.id} className="category-tile" style={{ "--category-color": category.color } as React.CSSProperties} onClick={() => onSelect(category.id)}>
    <span className="category-art">{category.imageUrl ? <img src={category.imageUrl} alt="" loading="lazy" decoding="async" /> : <Leaf size={23} strokeWidth={1.5} />}</span><span className="category-pill">{category.name}</span><span className="category-number">{String(i + 1).padStart(2, "0")}</span>
  </button>)}</div>;
}

function HomePage({ data, onOpen, onAiRecipe }: { data: HomeData; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const [, navigate] = useLocation();
  const [sort, setSort] = useState<"featured" | "price-asc" | "price-desc">("featured");
  const { data: products, isLoading: productsLoading } = trpc.commerce.catalog.listProducts.useQuery({ sort, limit: 24 }, { retry: 1, staleTime: 3000, refetchInterval: 3500, refetchOnWindowFocus: true });
  const featured = products ?? data.products;
  const changeCategory = (id: number) => { navigate(`/products?category=${id}`); };
  return <main className="page-shell">
    <BannerCarousel banners={data.banners} />
    {data.offers.length > 0 && <section className="offers-row"><div className="section-heading compact"><div><span className="eyebrow">عروض المتجر</span><h2>فرص تستحق الانتباه</h2></div><BadgePercent size={22} /></div><div className="offer-strip">{data.offers.map(offer => <div className="offer-chip" key={offer.id}><span className="offer-chip-icon"><BadgePercent size={18} /></span><div><strong>{offer.title}</strong><small>{offer.description || (offer.discountType === "percent" ? `خصم ${offer.discountValue}%` : `خصم ${formatPrice(offer.discountValue)}`)}</small></div><code>{offer.code}</code></div>)}</div></section>}
    <section className="store-section categories-section"><div className="section-heading"><div><span className="eyebrow"></span><h2>ابدأ من الأقسام</h2></div><Link className="text-link" href="/categories">كل الأقسام <ArrowLeft size={15} /></Link></div><CategoryStrip data={data.categories} onSelect={changeCategory} /></section>
    <section className="store-section products-section"><div className="section-heading"><div><span className="eyebrow"></span><h2>منتجات المتجر</h2></div><div className="section-tools"><label className="sort-select"><ArrowUpDown size={15} /><select aria-label="ترتيب المنتجات" value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="featured">الأبرز</option><option value="price-asc">السعر: الأقل أولًا</option><option value="price-desc">السعر: الأعلى أولًا</option></select></label><Link className="text-link" href="/products">عرض الكل <ArrowLeft size={15} /></Link></div></div>{productsLoading && !featured.length ? <Loading /> : <ProductGrid items={featured} onOpen={onOpen} onAiRecipe={onAiRecipe} />}</section>
  </main>;
}

function ProductListPage({ data, onOpen, onAiRecipe }: { data: HomeData; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const [, setLocation] = useLocation();
  const searchString = useSearch();
  const params = new URLSearchParams(searchString);
  const selectedCategory = params.get("category");
  const routeSearch = params.get("search") ?? "";
  const [search, setSearch] = useState(routeSearch);
  const debouncedSearch = useDebouncedValue(search.trim());
  const [sort, setSort] = useState<"featured" | "price-asc" | "price-desc" | "name">("featured");
  useEffect(() => setSearch(routeSearch), [routeSearch]);
  const categoryId = selectedCategory ? Number(selectedCategory) : undefined;
  const cachedProducts = !debouncedSearch && sort === "featured"
    ? data.products.filter(product => categoryId === undefined || product.categoryId === categoryId)
    : [];
  const input = { search: debouncedSearch || undefined, categoryId, sort, limit: 60 };
  const query = trpc.commerce.catalog.listProducts.useQuery(input, { retry: 1, staleTime: 30_000, placeholderData: cachedProducts.length ? cachedProducts : undefined });
  return <main className="page-shell inner-page"><div className="page-title-row"><div><span className="eyebrow"></span><h1>المنتجات</h1><p></p></div><span className="page-title-icon"><ShoppingBag size={24} /></span></div>
    <div className="filter-bar"><label className="filter-search"><Search size={17} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="ابحث باسم المنتج..." /></label><label className="filter-select"><SlidersHorizontal size={16} /><select value={selectedCategory ?? ""} onChange={event => { const value = event.target.value; setLocation(value ? `/products?category=${value}` : "/products"); }}><option value="">كل الأقسام</option>{data.categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label className="filter-select"><ArrowDownWideNarrow size={16} /><select value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="featured">ترتيب افتراضي</option><option value="price-asc">السعر من الأقل</option><option value="price-desc">السعر من الأعلى</option><option value="name">الاسم</option></select></label></div>
    {query.isLoading ? <Loading /> : query.error ? <LoadError onRetry={() => void query.refetch()} /> : <ProductGrid items={query.data ?? []} onOpen={onOpen} onAiRecipe={onAiRecipe} />}
  </main>;
}

function CategoriesPage({ data }: { data: HomeData }) {
  const [, navigate] = useLocation();
  return <main className="page-shell inner-page"><div className="page-title-row"><div><span className="eyebrow"></span><h1>الأقسام</h1><p></p></div><span className="page-title-icon"><SlidersHorizontal size={23} /></span></div>
    {!data.categories.length ? <EmptyState icon={SlidersHorizontal} title="لا توجد أقسام بعد" description="سيضيف صاحب المتجر الأقسام المناسبة، وستظهر لك هنا تلقائيًا." action="استكشف المتجر" href="/products" /> : <div className="category-page-grid">{data.categories.map((category, i) => <button key={category.id} className="category-large" style={{ "--category-color": category.color } as React.CSSProperties} onClick={() => navigate(`/products?category=${category.id}`)}><span className="category-large-number">{String(i + 1).padStart(2, "0")}</span><span className="category-large-art">{category.imageUrl ? <img src={category.imageUrl} alt="" loading="lazy" decoding="async" /> : <Leaf size={34} />}</span><span className="category-pill">{category.name}</span>{category.description && <small>{category.description}</small>}<ChevronLeft size={19} /></button>)}</div>}
  </main>;
}

function ProductDetail({ id, onBack, onAiRecipe }: { id: number; onBack: () => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const { data: product, isLoading, error } = trpc.commerce.catalog.product.useQuery({ id }, { retry: 1 });
  const { add } = useStore(); const [quantity, setQuantity] = useState(1);
  if (isLoading) return <main className="page-shell inner-page"><Loading /></main>;
  if (error || !product) return <main className="page-shell inner-page"><LoadError onRetry={onBack} /></main>;
  const stockLimit = product.stock === null ? 9999 : product.stock;
  return <main className="page-shell inner-page"><button className="back-link" onClick={onBack}><ArrowLeft size={16} /> العودة للمتجر</button><div className="detail-layout"><div className="detail-visual">{product.imageUrl ? <img src={product.imageUrl} alt={product.name} fetchPriority="high" decoding="async" /> : <div className="product-no-image detail-placeholder"><Leaf size={45} /><span>لا توجد صورة لهذا المنتج</span></div>}</div><div className="detail-copy"><span className="eyebrow">من متجر أوريجنال</span><h1>{product.name}</h1><p className="detail-description">{product.description || "لا يوجد وصف مضاف لهذا المنتج حتى الآن."}</p><div className="detail-price">{formatPrice(product.price)} <small>/ {product.unit}</small></div><div className="detail-meta"><span><Package size={15} /> الوحدة: {product.unit}</span><span>{product.stock === null ? "التوفر يحدده المتجر" : `المتاح: ${product.stock}`}</span></div><div className="quantity-control"><button aria-label="تقليل" onClick={() => setQuantity(value => Math.max(product.minQuantity || 1, value - (product.quantityStep || 1)))}><Minus size={16} /></button><strong>{quantity}</strong><button aria-label="زيادة" disabled={quantity + (product.quantityStep || 1) > stockLimit} onClick={() => setQuantity(value => Math.min(stockLimit, value + (product.quantityStep || 1)))}><Plus size={16} /></button><small>{product.unit}</small></div><button className="button button-primary full-button" disabled={stockLimit < (product.minQuantity || 1)} onClick={() => { add(product, quantity); toast.success("أُضيف المنتج إلى السلة"); }}><ShoppingCart size={17} /> أضف إلى السلة</button></div></div>
    {!!product.recommendations.length && <section className="store-section"><div className="section-heading"><div><span className="eyebrow">قد يناسبك أيضًا</span><h2>منتجات مقترحة</h2></div></div><ProductGrid items={product.recommendations as PublicProduct[]} onOpen={nextId => window.location.assign(`/product/${nextId}`)} /></section>}
  </main>;
}

function CartPage({ minOrder = 0 }: { minOrder?: number }) {
  const { cart, setQuantity, remove, clear } = useStore();
  const [checkout, setCheckout] = useState(false);
  const subtotal = cart.reduce((sum, line) => sum + line.price * line.quantity, 0);
  const belowMin = minOrder > 0 && subtotal < minOrder;
  return (
    <main className="page-shell inner-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow"></span>
          <h1>سلة التسوق</h1>
          <p></p>
        </div>
        <span className="page-title-icon"><ShoppingCart size={24} /></span>
      </div>
      {!cart.length ? (
        <EmptyState
          icon={ShoppingCart}
          title="السلة فارغة الآن"
          description="عندما تضيف منتجات من المتجر، ستجدها هنا."
          action="ابدأ التسوق"
          href="/products"
        />
      ) : (
        <div className="cart-layout">
          <div className="cart-list">
            {cart.map(line => (
              <CartRow
                key={line.id}
                line={line}
                onQuantity={quantity => setQuantity(line.id, quantity)}
                onRemove={() => remove(line.id)}
              />
            ))}
            <button className="text-link clear-cart" onClick={clear}>
              <Trash2 size={15} /> إفراغ السلة
            </button>
          </div>
          <aside className="summary-card">
            <span className="eyebrow">ملخص الطلب</span>
            <div className="summary-line">
              <span>المجموع الفرعي</span>
              <strong>{formatPrice(subtotal)}</strong>
            </div>
            {minOrder > 0 && (
              <div className="summary-line">
                <span>الحد الأدنى للطلب</span>
                <strong>{formatPrice(minOrder)}</strong>
              </div>
            )}
            <div className="summary-line">
              <span>التوصيل</span>
              <span className="subtle-note">يحسب بعد تحديد المنطقة</span>
            </div>
            <div className="summary-total">
              <span>الإجمالي الحالي</span>
              <strong>{formatPrice(subtotal)}</strong>
            </div>
            {belowMin ? (
              <p
                className="summary-note"
                style={{
                  color: "#b42318",
                  background: "#fef3f2",
                  border: "1px solid #fecdca",
                  padding: "8px 10px",
                  borderRadius: "10px",
                  fontWeight: 700,
                }}
              >
                ⚠️ الحد الأدنى للطلب هو {formatPrice(minOrder)} — أضف منتجات بقيمة {formatPrice(minOrder - subtotal)} لإتمام الطلب.
              </p>
            ) : (
              <p className="summary-note">
                
              </p>
            )}
            <button
              className="button button-primary full-button"
              onClick={() => {
                if (belowMin) {
                  toast.error(`الحد الأدنى للطلب من المتجر هو ${formatPrice(minOrder)} (متبقي ${formatPrice(minOrder - subtotal)})`);
                  return;
                }
                setCheckout(true);
              }}
            >
              المتابعة لإتمام الطلب<ArrowLeft size={17} />
            </button>
            {checkout && <Checkout onClose={() => setCheckout(false)} onSuccess={clear} cart={cart} />}
          </aside>
        </div>
      )}
    </main>
  );
}

function CartRow({ line, onQuantity, onRemove }: { line: CartLine; onQuantity: (n: number) => void; onRemove: () => void }) {
  return <article className="cart-row"><div className="cart-thumb">{line.imageUrl ? <img src={line.imageUrl} alt="" loading="lazy" decoding="async" /> : <Leaf size={22} />}</div><div className="cart-row-info"><strong>{line.name}</strong><small>{formatPrice(line.price)} / {line.unit}</small><div className="cart-row-tools"><div className="quantity-compact"><button aria-label="تقليل" onClick={() => onQuantity(line.quantity - (line.quantityStep || 1))}><Minus size={14} /></button><b>{line.quantity}</b><button aria-label="زيادة" disabled={line.stock !== null && line.stock !== undefined && line.quantity + (line.quantityStep || 1) > line.stock} onClick={() => onQuantity(line.quantity + (line.quantityStep || 1))}><Plus size={14} /></button></div><button className="remove-line" onClick={onRemove}><Trash2 size={14} /> إزالة</button></div></div><strong className="cart-line-total">{formatPrice(line.price * line.quantity)}</strong></article>;
}

function Checkout({ onClose, onSuccess, cart }: { onClose: () => void; onSuccess: () => void; cart: CartLine[] }) {
  const utils = trpc.useUtils();
  const customer = useCustomer();
  const defaultAddress = customer.addresses.find(address => address.isDefault) ?? customer.addresses[0];
  const [selectedAddressId, setSelectedAddressId] = useState(defaultAddress?.id ?? "new");
  const [form, setForm] = useState(() => ({
    recipientName: defaultAddress?.recipientName ?? customer.name,
    phone: defaultAddress?.phone ?? customer.phone,
    city: defaultAddress?.city ?? "",
    district: defaultAddress?.district ?? "",
    addressDetails: defaultAddress?.details ?? "",
    customerNote: "",
    offerCode: "",
  }));
  const [saveDeliveryAddress, setSaveDeliveryAddress] = useState(false);
  const [makeDefaultAddress, setMakeDefaultAddress] = useState(customer.addresses.length === 0);
  const [addressLabel, setAddressLabel] = useState("المنزل");
  const items = cart.map(item => ({ productId: item.id, quantity: item.quantity }));
  const signature = JSON.stringify({ form, items });
  const keyRef = useRef<{ signature: string; key: string }>({ signature: "", key: "" });
  if (keyRef.current.signature !== signature) keyRef.current = { signature, key: getPendingOrderIdempotencyKey(signature) };
  const [quoteSignature, setQuoteSignature] = useState("");
  const quoteMutation = trpc.commerce.orders.quote.useMutation({ onError: error => toast.error(error.message || "تعذر حساب ملخص الطلب.") });
  const quote = quoteSignature === signature ? quoteMutation.data : undefined;
  const mutation = trpc.commerce.orders.place.useMutation({
    onSuccess: result => {
      const idempotencyKey = keyRef.current.key;
      customer.rememberOrder({ orderNumber: result.orderNumber, idempotencyKey, createdAt: new Date().toISOString() });
      clearPendingOrderIdempotencyKey(idempotencyKey);
      if (result.duplicate) {
        toast.info(`الطلب مسجل مسبقًا برقم ${result.orderNumber}. احتفظنا بالسلة كما هي؛ راجع «طلباتي» قبل إرسال طلب جديد.`);
        onClose();
        return;
      }
      customer.saveProfile(form.recipientName, form.phone);
      if (saveDeliveryAddress) {
        const matchingAddress = customer.addresses.find(address =>
          address.recipientName === form.recipientName.trim() && address.phone === form.phone.trim()
          && address.city === form.city.trim() && address.district === form.district.trim()
          && address.details === form.addressDetails.trim(),
        );
        if (matchingAddress) {
          if (makeDefaultAddress) customer.setDefaultAddress(matchingAddress.id);
        } else {
          customer.saveAddress({
            label: addressLabel, recipientName: form.recipientName, phone: form.phone,
            city: form.city, district: form.district, details: form.addressDetails,
            isDefault: makeDefaultAddress || customer.addresses.length === 0,
          });
        }
      }
      onSuccess();
      void utils.commerce.orders.trackMany.invalidate();
      toast.success(`تم استلام طلبك رقم ${result.orderNumber}. سيتواصل المتجر معك لتأكيده.`);
      onClose();
    },
    onError: error => { setQuoteSignature(""); quoteMutation.reset(); toast.error(error.message || "تعذر إرسال الطلب. لم تُفرغ السلة؛ راجع البيانات وحاول مجددًا."); },
  });
  const selectAddress = (id: string) => {
    setSelectedAddressId(id);
    if (id === "new") return;
    const address = customer.addresses.find(item => item.id === id);
    if (address) setForm(current => ({
      ...current, recipientName: address.recipientName, phone: address.phone,
      city: address.city, district: address.district, addressDetails: address.details,
    }));
    setSaveDeliveryAddress(false);
  };
  const updateField = (field: keyof typeof form, value: string) => {
    setForm(current => ({ ...current, [field]: value }));
    if (["recipientName", "phone", "city", "district", "addressDetails"].includes(field)) setSelectedAddressId("new");
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (mutation.isPending || quoteMutation.isPending) return;
    if (!quote) {
      quoteMutation.reset();
      setQuoteSignature(signature);
      quoteMutation.mutate({ items, city: form.city, offerCode: form.offerCode || undefined });
      return;
    }
    mutation.mutate({ ...form, idempotencyKey: keyRef.current.key, expectedTotal: quote.total, expectedQuoteHash: quote.quoteHash, offerCode: form.offerCode || undefined, items });
  };
  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}><section className="checkout-modal" role="dialog" aria-modal="true"><div className="modal-heading"><div><span className="eyebrow"></span><h2>بيانات التوصيل</h2><small></small></div><button type="button" className="icon-button" onClick={onClose}><X size={19} /></button></div><form onSubmit={submit} className="form-stack">
    {customer.addresses.length > 0 && <label>استخدم عنوانًا محفوظًا في هذا المتصفح<select value={selectedAddressId} onChange={event => selectAddress(event.target.value)}><option value="new">إدخال عنوان جديد</option>{customer.addresses.map(address => <option key={address.id} value={address.id}>{address.label} · {address.city}، {address.district}</option>)}</select></label>}
    <div className="form-grid"><label>اسم المستلم<input required minLength={2} maxLength={160} autoComplete="name" value={form.recipientName} onChange={event => updateField("recipientName", event.target.value)} /></label><label>رقم الهاتف<input required type="tel" minLength={7} maxLength={32} autoComplete="tel" value={form.phone} onChange={event => updateField("phone", event.target.value)} /></label><label>المدينة/المنطقة<input required maxLength={100} autoComplete="address-level1" value={form.city} onChange={event => updateField("city", event.target.value)} /></label><label>الحي<input required maxLength={120} autoComplete="address-level2" value={form.district} onChange={event => updateField("district", event.target.value)} /></label></div>
    <label>تفاصيل العنوان (اختياري)<textarea rows={2} maxLength={1000} autoComplete="street-address" value={form.addressDetails} onChange={event => updateField("addressDetails", event.target.value)} /></label>
    <label className="toggle-field"><input type="checkbox" checked={saveDeliveryAddress} onChange={event => setSaveDeliveryAddress(event.target.checked)} /> احفظ هذا العنوان في هذا المتصفح للطلبات القادمة</label>
    {saveDeliveryAddress && <div className="form-grid"><label>اسم العنوان<input maxLength={80} value={addressLabel} onChange={event => setAddressLabel(event.target.value)} placeholder="المنزل، العمل..." /></label><label className="toggle-field"><input type="checkbox" checked={makeDefaultAddress} onChange={event => setMakeDefaultAddress(event.target.checked)} /> اجعله العنوان الافتراضي</label></div>}
    <label>ملاحظة للمتجر (اختياري)<textarea rows={2} maxLength={1000} value={form.customerNote} onChange={event => updateField("customerNote", event.target.value)} /></label><label>رمز خصم (اختياري)<input maxLength={40} value={form.offerCode} onChange={event => updateField("offerCode", event.target.value.toUpperCase())} /></label>
    {quote && <section className="checkout-quote" aria-live="polite"><h3>راجع تفاصيل طلبك</h3><div className="checkout-quote-lines">{quote.lines.map(line => <div key={line.productId}><span>{line.name} × {line.quantity} {line.unit}</span><strong>{formatPrice(line.lineTotal)}</strong></div>)}</div><div className="summary-line"><span>المجموع الفرعي</span><strong>{formatPrice(quote.subtotal)}</strong></div><div className="summary-line"><span>التوصيل</span><strong>{formatPrice(quote.deliveryFee)}</strong></div>{quote.discount > 0 && <div className="summary-line discount-line"><span>الخصم{quote.offerTitle ? ` · ${quote.offerTitle}` : ""}</span><strong>−{formatPrice(quote.discount)}</strong></div>}<div className="summary-total"><span>الإجمالي · {quote.currency}</span><strong>{formatPrice(quote.total)}</strong></div></section>}
    <div className="cod-note"><Truck size={17} /><span>الدفع نقدًا عند الاستلام</span></div><div className="modal-footer"><button type="button" className="button button-quiet" onClick={onClose}>رجوع للسلة</button><button className="button button-primary" disabled={mutation.isPending || quoteMutation.isPending}>{mutation.isPending || quoteMutation.isPending ? <LoaderCircle className="spin" size={17} /> : quote ? <Check size={17} /> : <ArrowLeft size={17} />}{mutation.isPending ? "جارٍ إرسال الطلب..." : quoteMutation.isPending ? "جارٍ حساب الإجمالي..." : quote ? "تأكيد الطلب" : "عرض ملخص الطلب"}</button></div>
  </form></section></div>;
}

function FavoritesPage() {
  const { favoriteIds } = useStore();
  const [, navigate] = useLocation();
  const query = trpc.commerce.catalog.productsForReorder.useQuery({ ids: favoriteIds }, { enabled: favoriteIds.length > 0, retry: 1, staleTime: 30_000 });
  const products = query.data ?? [];
  return <main className="page-shell inner-page"><div className="page-title-row"><div><span className="eyebrow"></span><h1>المفضلة</h1><p></p></div><span className="page-title-icon"><Heart size={23} /></span></div>{query.isLoading ? <Loading /> : query.error ? <LoadError onRetry={() => void query.refetch()} /> : !favoriteIds.length ? <EmptyState icon={Heart} title="لم تحفظ منتجات بعد" description="اضغط علامة القلب على أي منتج لإضافته هنا." action="تصفح المنتجات" href="/products" /> : !products.length ? <EmptyState icon={Heart} title="لا توجد منتجات متاحة من مفضلتك الآن" description="قد تكون المنتجات التي حفظتها أُخفيت أو نفدت." action="تصفح المنتجات" href="/products" /> : <ProductGrid items={products as PublicProduct[]} onOpen={id => navigate(`/product/${id}`)} />}</main>;
}

const CUSTOMER_PUSH_KEY = "original-customer-push-enabled-v1";
const CUSTOMER_STATUS_MAP_KEY = "original-customer-order-statuses-v1";
function playCustomerOrderSound() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    [523.25, 783.99].forEach((freq, idx) => {
      const osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.15);
      gain.gain.setValueAtTime(0.22, ctx.currentTime + idx * 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.15 + 0.32);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.15);
      osc.stop(ctx.currentTime + idx * 0.15 + 0.34);
    });
  } catch {}
}
async function showCustomerPhoneNotification(title: string, body: string, tag: string) {
  try {
    if ("serviceWorker" in navigator && Notification.permission === "granted") {
      const reg = await Promise.race([
        navigator.serviceWorker.ready,
        new Promise<null>(r => setTimeout(() => r(null), 2000)),
      ]);
      if (reg) {
        await reg.showNotification(title, {
          body,
          icon: "/app-icon-192-v2.png",
          badge: "/app-icon-192-v2.png",
          tag,
          dir: "rtl",
          lang: "ar",
          vibrate: [220, 100, 220],
          requireInteraction: true,
          renotify: true,
          data: { url: "/orders" },
        } as any);
        return;
      }
    }
    if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "/app-icon-192-v2.png", tag, dir: "rtl", lang: "ar" });
    }
  } catch {}
}
function OrdersPage() {
  const customer = useCustomer();
  const { add } = useStore();
  const refs = useMemo(() => customer.orders.slice(0, 50).map(({ orderNumber, idempotencyKey }) => ({ orderNumber, idempotencyKey })), [customer.orders]);
  const query = trpc.commerce.orders.trackMany.useQuery({ refs }, { enabled: refs.length > 0, retry: 1, staleTime: 10_000, refetchInterval: refs.length ? 30_000 : false });
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.orders.subscribeToStatus.useMutation();
  const [permission, setPermission] = useState(getPushPermissionState);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushPending, setPushPending] = useState(false);
  const [reorder, setReorder] = useState<Array<{ productId: number; quantity: number }> | null>(null);
  const reorderQuery = trpc.commerce.catalog.productsForReorder.useQuery({ ids: reorder?.map(item => item.productId) ?? [1] }, { enabled: Boolean(reorder), retry: 1 });
  useEffect(() => {
    if (!refs.length || getPushPermissionState() !== "granted") return;
    let active = true;
    void getExistingBrowserPushSubscription().then(async subscription => {
      if (!subscription || !active) return;
      const result = await subscribe.mutateAsync({ refs, subscription });
      if (active) setPushEnabled(result.subscribed > 0);
    }).catch(() => undefined);
    return () => { active = false; };
  }, [refs, subscribe.mutateAsync]);
  const enableNotifications = async () => {
    if (!refs.length || pushPending) return;
    setPushPending(true);
    try {
      const requestedPermission = await requestPushPermission();
      setPermission(requestedPermission);
      if (requestedPermission === "unsupported") {
        throw new Error("متصفحك لا يدعم الإشعارات لهذا التطبيق.");
      }
      if (requestedPermission !== "granted") {
        throw new Error("لم تسمح بإشعارات المتصفح. فعلها من أيقونة القفل بجانب الرابط.");
      }
      try { localStorage.setItem(CUSTOMER_PUSH_KEY, "true"); } catch {}
      setPushEnabled(true);
      playCustomerOrderSound();
      await showCustomerPhoneNotification(
        "تم تفعيل إشعارات طلباتك 🔔",
        "سيصلك إشعار فوري في شريط الهاتف عند كل تحديث لحالة طلبك!",
        "original-customer-push-test"
      );
      toast.success("تم تفعيل إشعارات حالة طلباتك على هذا الجهاز بنجاح 🔔");
      void (async () => {
        try {
          const key = publicKey.data ?? (await publicKey.refetch()).data;
          if (!key) return;
          const subscription = await ensureBrowserPushSubscription(key);
          await subscribe.mutateAsync({ refs, subscription });
        } catch {}
      })();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "تعذر تفعيل الإشعارات الآن.");
    } finally {
      setPushPending(false);
    }
  };
  useEffect(() => {
    if (!reorder || !reorderQuery.data) return;
    let added = 0; let skipped = 0;
    for (const line of reorder) {
      const product = reorderQuery.data.find(candidate => candidate.id === line.productId);
      if (!product) { skipped += 1; continue; }
      const minimum = product.minQuantity || 1; const step = product.quantityStep || 1;
      let quantity = minimum + Math.max(0, Math.floor((Math.max(minimum, line.quantity) - minimum) / step)) * step;
      if (product.stock !== null) {
        const bounded = Math.min(quantity, product.stock);
        quantity = minimum + Math.max(0, Math.floor((bounded - minimum) / step)) * step;
        if (quantity > product.stock) { skipped += 1; continue; }
      }
      add(product, quantity); added += 1;
    }
    if (added) toast.success(`أُضيف ${added} منتج${skipped ? `، وتعذرت إضافة ${skipped} أصناف غير متاحة` : ""}. راجع الأسعار والكميات قبل الطلب.`);
    else toast.error("لا توجد منتجات متاحة من هذا الطلب الآن.");
    setReorder(null);
  }, [reorder, reorderQuery.data, add]);
  const orders = query.data ?? [];
  return <main className="page-shell inner-page">
    <div className="page-title-row"><div><span className="eyebrow"></span><h1>طلباتي</h1><p></p></div><span className="page-title-icon"><Package size={23} /></span></div>
    {refs.length > 0 && <section className="customer-push-panel"><div><strong>{pushEnabled ? "إشعارات حالة الطلب مفعّلة" : "تابع حالة طلبك بإشعار"}</strong><small>{permission === "denied" ? "الإشعارات محظورة من إعدادات المتصفح." : permission === "unsupported" ? "هذا المتصفح لا يدعم إشعارات Push." : pushEnabled ? "ستصلك الحالة وملاحظة المالك عند تحديث طلبك." : ""}</small></div><button type="button" className="small-button" onClick={() => void enableNotifications()} disabled={pushPending || permission === "denied" || permission === "unsupported"}><BellRing size={15} />{pushPending ? "جارٍ التفعيل..." : pushEnabled ? "تحديث الاشتراك" : "تفعيل الإشعارات"}</button></section>}
    {query.isLoading ? <Loading /> : query.error ? <LoadError onRetry={() => void query.refetch()} /> : !orders.length ? <EmptyState icon={Package} title={refs.length ? "لم نعثر على طلبات محفوظة على هذا الجهاز" : "لا توجد طلبات سابقة"} description="بعد إتمام طلب من هذا المتصفح، ستظهر حالته هنا. لا يحتاج الطلب إلى حساب أو تسجيل دخول." action="تسوق الآن" href="/products" /> : <div className="orders-list">{orders.map(order => <article className="order-card" key={order.orderNumber}><div className="order-head"><div><span className="order-number">{order.orderNumber}</span><small>{new Date(order.createdAt).toLocaleDateString("ar-YE")}</small></div><span className={`status-pill status-${order.status}`}>{stateLabels[order.status] || order.status}</span></div><div className="order-items-summary">{order.items.map(item => <span key={item.id}>{item.productName} × {item.quantity}</span>)}</div><div className="order-foot"><strong>{formatPrice(order.total)}</strong><button type="button" className="small-button" disabled={reorderQuery.isFetching} onClick={() => { const items = order.items.filter(item => item.productId !== null).map(item => ({ productId: item.productId!, quantity: item.quantity })); if (!items.length) { toast.error("لم تعد منتجات هذا الطلب متاحة في المتجر."); return; } setReorder(items); }}>إضافة للسلة مجددًا <ArrowLeft size={14} /></button></div>{order.events.length > 0 && <details className="order-history"><summary>سجل حالة الطلب</summary><ol>{order.events.map(event => <li key={event.id}><span className={`status-pill status-${event.status}`}>{stateLabels[event.status] || event.status}</span><time>{new Date(event.createdAt).toLocaleString("ar-YE")}</time>{event.note && <small>{event.note}</small>}</li>)}</ol></details>}</article>)}</div>}
  </main>;
}

function useGuestPushSubscriptionSync() {
  const customer = useCustomer();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setReady(true), 4000);
    return () => window.clearTimeout(t);
  }, []);
  const refs = useMemo(
    () => customer.orders.slice(0, 50).map(({ orderNumber, idempotencyKey }) => ({ orderNumber, idempotencyKey })),
    [customer.orders]
  );
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.orders.subscribeToStatus.useMutation();
  const tracked = trpc.commerce.orders.trackMany.useQuery(
    { refs },
    { enabled: ready && refs.length > 0, retry: 1, staleTime: 8000, refetchInterval: ready && refs.length ? 10000 : false, refetchIntervalInBackground: true }
  );
  useEffect(() => {
    if ("serviceWorker" in navigator && refs.length > 0) {
      void navigator.serviceWorker.ready.then(reg => {
        reg.active?.postMessage({ type: "SYNC_SW_STATE", refs });
        if ("periodicSync" in reg) {
          void (reg as any).periodicSync.register("original-order-sync", { minInterval: 60000 }).catch(() => {});
        }
      }).catch(() => {});
    }
  }, [refs]);
  useEffect(() => {
    if (!tracked.data?.length) return;
    let map: Record<string, string> = {};
    try { map = JSON.parse(localStorage.getItem(CUSTOMER_STATUS_MAP_KEY) || "{}"); } catch {}
    let changed = false;
    for (const order of tracked.data) {
      const prev = map[order.orderNumber];
      const latestNote = order.events?.[order.events.length - 1]?.note || "";
      const sig = `${order.status}:${latestNote}`;
      if (prev && prev !== sig) {
        const statusLabel = stateLabels[order.status] || order.status;
        playCustomerOrderSound();
        toast.info(`🔔 تحديث الطلب ${order.orderNumber}: ${statusLabel}${latestNote ? " · " + latestNote : ""}`);
        void showCustomerPhoneNotification(
          `تحديث الطلب ${order.orderNumber} 🔔`,
          `${statusLabel}${latestNote ? " · " + latestNote : ""}`,
          `original-order-status-${order.orderNumber}-${order.status}`
        );
      }
      if (prev !== sig) { map[order.orderNumber] = sig; changed = true; }
    }
    if (changed) { try { localStorage.setItem(CUSTOMER_STATUS_MAP_KEY, JSON.stringify(map)); } catch {} }
  }, [tracked.data]);
  useEffect(() => {
    if (!refs.length || getPushPermissionState() !== "granted") return;
    let active = true;
    void (async () => {
      try {
        const key = publicKey.data ?? (await publicKey.refetch()).data;
        if (!key || !active) return;
        const subscription = await ensureBrowserPushSubscription(key);
        if (!active) return;
        await subscribe.mutateAsync({ refs, subscription });
      } catch {}
    })();
    return () => { active = false; };
  }, [refs, subscribe.mutateAsync]);
}

function AccountPage() {
  const customer = useCustomer();
  const [name, setName] = useState(customer.name);
  const [phone, setPhone] = useState(customer.phone);
  const [address, setAddress] = useState({ label: "المنزل", recipientName: customer.name, phone: customer.phone, city: "", district: "", details: "", isDefault: customer.addresses.length === 0 });
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);
  useEffect(() => { setName(customer.name); setPhone(customer.phone); }, [customer.name, customer.phone]);
  const saveProfile = (event: FormEvent) => {
    event.preventDefault();
    customer.saveProfile(name, phone);
    toast.success("حُفظت بياناتك في هذا المتصفح.");
  };
  const resetAddressForm = () => {
    setEditingAddressId(null);
    setAddress({ label: "المنزل", recipientName: name, phone, city: "", district: "", details: "", isDefault: customer.addresses.length === 0 });
  };
  const submitAddress = (event: FormEvent) => {
    event.preventDefault();
    customer.saveAddress({ ...address, id: editingAddressId ?? undefined });
    toast.success(editingAddressId ? "تم تحديث العنوان المحفوظ على هذا الجهاز." : "تم حفظ العنوان على هذا الجهاز.");
    resetAddressForm();
  };
  return <main className="page-shell inner-page"><div className="page-title-row"><div><span className="eyebrow"></span><h1>حسابي</h1><p></p></div><span className="page-title-icon"><UserRound size={23} /></span></div><div className="account-grid"><section className="panel-card"><div className="panel-title"><CircleUserRound size={19} /><h2>بيانات التواصل</h2></div><form className="form-stack" onSubmit={saveProfile}><label>الاسم<input required minLength={2} maxLength={160} autoComplete="name" value={name} onChange={event => setName(event.target.value)} /></label><label>رقم الهاتف<input required type="tel" minLength={7} maxLength={32} autoComplete="tel" value={phone} onChange={event => setPhone(event.target.value)} placeholder="أضف رقمًا يمكن للمتجر الاتصال به" /></label><button className="button button-primary" disabled={name.trim().length < 2 || phone.trim().length < 7}>حفظ البيانات على هذا الجهاز</button><label>لغة الواجهة<select value="ar" disabled><option value="ar">العربية</option></select></label><small className="subtle-note"></small></form></section><section className="panel-card"><div className="panel-title"><MapPin size={19} /><h2>عناويني المحفوظة</h2></div>{customer.addresses.map(item => <div className="saved-address" key={item.id}><div><strong>{item.label}{item.isDefault && <span className="default-tag">افتراضي</span>}</strong><p>{item.recipientName} · {item.phone}<br />{item.city}، {item.district}<br />{item.details}</p></div><div className="address-actions"><button type="button" className="small-button" onClick={() => { setEditingAddressId(item.id); setAddress({ label: item.label, recipientName: item.recipientName, phone: item.phone, city: item.city, district: item.district, details: item.details, isDefault: item.isDefault }); }}>تعديل</button>{!item.isDefault && <button type="button" className="small-button" onClick={() => customer.setDefaultAddress(item.id)}>افتراضي</button>}<button type="button" className="icon-button" aria-label="حذف العنوان" onClick={() => { customer.removeAddress(item.id); toast.success("حُذف العنوان من هذا الجهاز."); if (editingAddressId === item.id) resetAddressForm(); }}><Trash2 size={16} /></button></div></div>)}{!customer.addresses.length && <p className="subtle-note">لا توجد عناوين محفوظة بعد. أضف عنوانًا مرة واحدة لإعادة استخدامه عند الطلب القادم.</p>}<details className="address-add" open={editingAddressId !== null}><summary>{editingAddressId ? "تعديل العنوان" : "إضافة عنوان جديد"} <Plus size={15} /></summary><form className="form-stack" onSubmit={submitAddress}><div className="form-grid"><label>اسم العنوان<input required maxLength={80} value={address.label} onChange={event => setAddress({ ...address, label: event.target.value })} placeholder="المنزل، العمل..." /></label><label>اسم المستلم<input required minLength={2} maxLength={160} autoComplete="name" value={address.recipientName} onChange={event => setAddress({ ...address, recipientName: event.target.value })} /></label><label>الهاتف<input required type="tel" minLength={7} maxLength={32} autoComplete="tel" value={address.phone} onChange={event => setAddress({ ...address, phone: event.target.value })} /></label><label>المدينة/المنطقة<input required maxLength={100} autoComplete="address-level1" value={address.city} onChange={event => setAddress({ ...address, city: event.target.value })} /></label><label>الحي<input required maxLength={120} autoComplete="address-level2" value={address.district} onChange={event => setAddress({ ...address, district: event.target.value })} /></label><label className="form-wide">تفاصيل العنوان<textarea rows={2} maxLength={1000} autoComplete="street-address" value={address.details} onChange={event => setAddress({ ...address, details: event.target.value })} /></label><label className="toggle-field form-wide"><input type="checkbox" checked={address.isDefault} onChange={event => setAddress({ ...address, isDefault: event.target.checked })} /> اجعل هذا العنوان الافتراضي</label></div><div className="address-form-actions"><button className="button button-primary">{editingAddressId ? "حفظ تعديل العنوان" : "حفظ العنوان"}</button>{editingAddressId && <button type="button" className="button button-quiet" onClick={resetAddressForm}>إلغاء</button>}</div></form></details></section></div><p className="local-data-note"></p></main>;
}

type AssistantProductLine = { productId: number; name: string; price: number; unit: string; quantity: number; stock: number | null; minQuantity: number; quantityStep: number };
type AssistantCartAction = { id: string; type: "add" | "remove"; items: AssistantProductLine[]; status: "pending" | "confirmed" | "cancelled" };
type AssistantMessage = {
  role: "user" | "assistant";
  text: string;
  contextText?: string;
  recipe?: { name: string; servings: number; steps: string[] } | null;
  ingredients?: AssistantProductLine[];
  missingIngredients?: string[];
  recipeActionId?: string;
  recipeAdded?: boolean;
  cartAction?: AssistantCartAction;
  suggestedQuestions?: string[];
};

const ASSISTANT_HISTORY_KEY = "original-assistant-history-v2";
const assistantGreeting: AssistantMessage = { role: "assistant", text: "مرحبًا، أنا مساعد أوريجنال. أخبرني عن الطبخة أو احتياجك، وسأساعدك من المنتجات المتاحة فعلًا في المتجر." };

function readAssistantHistory(): AssistantMessage[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(ASSISTANT_HISTORY_KEY) ?? "null");
    if (!Array.isArray(saved)) return [assistantGreeting];
    const history = saved.flatMap(item => {
      if (!item || typeof item !== "object") return [];
      const row = item as Record<string, unknown>;
      if ((row.role !== "user" && row.role !== "assistant") || typeof row.text !== "string") return [];
      return [{ role: row.role, text: row.text.slice(0, 1800), ...(typeof row.contextText === "string" ? { contextText: row.contextText.slice(0, 1800) } : {}) } as AssistantMessage];
    }).slice(-32);
    return history.length ? history : [assistantGreeting];
  } catch { return [assistantGreeting]; }
}

function assistantHistoryText(message: AssistantMessage) {
  return [message.text, message.contextText].filter(Boolean).join("\n").slice(0, 1800);
}

function AssistantPage() {
  const { add, cart, setQuantity, favoriteIds } = useStore();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>(readAssistantHistory);
  const messagesRef = useRef<HTMLDivElement>(null);
  const appliedActionsRef = useRef(new Set<string>());
  const retryRef = useRef<{ request: string; history: Array<{ role: "user" | "assistant"; text: string }> } | null>(null);
  const mutation = trpc.commerce.assistant.recipe.useMutation();

  useEffect(() => {
    const saved = messages.slice(-32).map(message => ({ role: message.role, text: message.text, ...(message.contextText ? { contextText: message.contextText } : {}) }));
    try { localStorage.setItem(ASSISTANT_HISTORY_KEY, JSON.stringify(saved)); } catch { /* local conversation storage may be unavailable */ }
  }, [messages]);
  useEffect(() => {
    const node = messagesRef.current;
    if (node) node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages.length, mutation.isPending]);

  const startNewConversation = () => {
    if (mutation.isPending) return;
    retryRef.current = null;
    appliedActionsRef.current.clear();
    setInput("");
    setMessages([assistantGreeting]);
    try { localStorage.removeItem(ASSISTANT_HISTORY_KEY); } catch { /* local storage may be unavailable */ }
  };

  const updateActionStatus = (actionId: string, status: "confirmed" | "cancelled") => {
    setMessages(current => current.map(message => {
      if (message.cartAction?.id === actionId) {
        return { ...message, cartAction: { ...message.cartAction, status }, contextText: `${message.contextText ?? message.text}\nحالة طلب السلة: ${status === "confirmed" ? "أكد العميل التغيير" : "رفض العميل التغيير"}.` };
      }
      if (message.recipeActionId === actionId) {
        return { ...message, recipeAdded: status === "confirmed", contextText: `${message.contextText ?? message.text}\nحالة إضافة مقادير الوصفة: ${status === "confirmed" ? "أكد العميل الإضافة" : "رفض العميل الإضافة"}.` };
      }
      return message;
    }));
  };

  const applyConfirmedChange = (actionId: string, type: "add" | "remove", items: AssistantProductLine[]) => {
    if (appliedActionsRef.current.has(actionId)) return;
    appliedActionsRef.current.add(actionId);
    let changed = 0;
    let skipped = 0;
    for (const item of items) {
      const current = cart.find(line => line.id === item.productId);
      if (type === "add") {
        const total = (current?.quantity ?? 0) + item.quantity;
        if (item.stock !== null && total > item.stock) { skipped += 1; continue; }
        add({ id: item.productId, name: item.name, price: item.price, unit: item.unit, stock: item.stock, minQuantity: item.minQuantity, quantityStep: item.quantityStep }, item.quantity);
        changed += 1;
      } else {
        if (!current) { skipped += 1; continue; }
        setQuantity(item.productId, Math.max(0, current.quantity - item.quantity));
        changed += 1;
      }
    }
    updateActionStatus(actionId, "confirmed");
    if (changed) toast.success(type === "add" ? `تمت إضافة ${changed} صنف إلى السلة.` : `تم حذف ${changed} صنف من السلة.`);
    if (skipped) toast.error("تغيّرت السلة أو الكمية المتاحة؛ راجع السلة قبل إتمام الطلب.");
    if (!changed && !skipped) toast.error("لم يحدث تغيير في السلة.");
  };

  const cancelCartChange = (actionId: string) => {
    if (appliedActionsRef.current.has(actionId)) return;
    appliedActionsRef.current.add(actionId);
    updateActionStatus(actionId, "cancelled");
    toast("لم يتم تغيير السلة.");
  };

  const send = (event: FormEvent) => {
    event.preventDefault();
    if (mutation.isPending || !input.trim()) return;
    const request = input.trim();
    const retry = retryRef.current;
    const isRetry = retry?.request === request;
    const history = isRetry ? retry.history : messages.slice(-16).map(message => ({ role: message.role, text: assistantHistoryText(message) }));
    if (!isRetry) setMessages(current => [...current, { role: "user" as const, text: request }].slice(-32));
    retryRef.current = { request, history };
    setInput("");
    mutation.mutate({ request, history, cart: cart.map(line => ({ productId: line.id, quantity: line.quantity })), favoriteProductIds: favoriteIds }, {
      onSuccess: result => {
        retryRef.current = null;
        const contextText = [
          result.recipe ? `الوصفة: ${result.recipe.name}؛ عدد الأشخاص: ${result.recipe.servings}.` : "",
          result.ingredients?.length ? `المقادير المتاحة في المتجر: ${result.ingredients.map(item => `${item.name} ${item.quantity} ${item.unit}`).join("، ")}.` : "",
          result.missingIngredients?.length ? `المقادير التي طلب العميل توفيرها وليست متاحة الآن: ${result.missingIngredients.join("، ")}.` : "",
          result.cartAction ? `طلب مقترح للسلة بانتظار اختيار العميل: ${result.cartAction.type === "add" ? "إضافة" : "حذف"} ${result.cartAction.items.map(item => `${item.name} ${item.quantity} ${item.unit}`).join("، ")}.` : "",
        ].filter(Boolean).join(" ");
        setMessages(current => [...current, {
          role: "assistant" as const, text: result.message, contextText,
          recipe: result.recipe, ingredients: result.ingredients,
          missingIngredients: result.missingIngredients,
          recipeActionId: result.recipe && result.ingredients?.length ? window.crypto.randomUUID() : undefined,
          recipeAdded: false,
          suggestedQuestions: (result as any).suggestedQuestions,
          cartAction: result.cartAction ? { ...result.cartAction, id: window.crypto.randomUUID(), status: "pending" as const } : undefined,
        }].slice(-32));
      },
      onError: error => {
        const code = error.data?.code;
        const friendly = code === "TOO_MANY_REQUESTS" || code === "SERVICE_UNAVAILABLE"
          ? error.message
          : code === "BAD_REQUEST"
            ? "اكتب طلبك بكلمات بسيطة، حتى لو كانت رسالة قصيرة مثل «لا» أو «نعم»."
            : "تعذر إرسال الرسالة الآن. احتفظت بها لتعيد المحاولة.";
        toast.error(friendly);
        setInput(request);
        setMessages(current => [...current, { role: "assistant" as const, text: `${friendly} اضغط الإرسال لإعادة المحاولة.` }].slice(-32));
      },
    });
  };

  const copyMissingRequest = async (message: AssistantMessage) => {
    const missing = message.missingIngredients ?? [];
    if (!message.recipe || !missing.length) return;
    const { text: note, truncated } = buildMissingIngredientNote(message.recipe.name, message.recipe.servings, missing);
    const successMessage = truncated
      ? "نُسخت ملاحظة مختصرة ضمن حد الطلب؛ بقية النواقص موضحة في المحادثة."
      : "نُسخت الملاحظة. الصقها في خانة «ملاحظة للمتجر» عند تأكيد الطلب.";
    try {
      await navigator.clipboard.writeText(note);
      toast.success(successMessage);
    } catch {
      const field = document.createElement("textarea");
      field.value = note;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.appendChild(field);
      field.select();
      const copied = document.execCommand("copy");
      field.remove();
      if (copied) toast.success(successMessage);
      else toast.error("تعذر النسخ تلقائيًا؛ يمكنك تحديد النص في تفاصيل النواقص ونسخه يدويًا.");
    }
  };

  return <main className="page-shell inner-page assistant-page"><div className="assistant-intro"><span className="assistant-orb"><Bot size={27} /></span><span className="eyebrow">مساعد أوريجنال</span><h1>نطبخها سوا؟</h1><p></p></div><section className="chat-panel"><div className="chat-head"><span className="chat-avatar"><Sparkles size={17} /></span><div><strong>مساعد أوريجنال</strong><small>متصل الآن · مساعد الذكاء الاصطناعي</small></div><span className="online-dot" /><button type="button" className="assistant-new-chat" disabled={mutation.isPending} onClick={startNewConversation}>محادثة جديدة</button></div><div className="chat-messages" ref={messagesRef}>{messages.map((message, index) => <div key={`${index}-${message.role}`} className={`chat-message ${message.role === "user" ? "from-user" : "from-assistant"}`}><p style={{ whiteSpace: "pre-line" }}><GradualText text={message.text} animate={message.role === "assistant" && index === messages.length - 1} /></p>{message.role === "assistant" && message.suggestedQuestions && message.suggestedQuestions.length > 0 && <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "10px" }}>{message.suggestedQuestions.map(q => <button key={q} type="button" disabled={mutation.isPending} onClick={() => { setInput(q); setTimeout(() => { const btn = document.querySelector(".chat-input button") as HTMLButtonElement | null; btn?.click(); }, 30); }} style={{ padding: "6px 11px", borderRadius: "10px", border: "1px solid #c5d6c7", background: "#ffffff", color: "#174b36", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}><Sparkles size={12} style={{ display: "inline", marginLeft: "4px", verticalAlign: "-2px" }} />{q}</button>)}</div>}{message.recipe && <div className="recipe-card"><span className="eyebrow">اقتراح وصفة</span><h3>{message.recipe.name}</h3><small>تكفي {message.recipe.servings} أشخاص</small>{message.ingredients?.length ? <div className="recipe-ingredients">{message.ingredients.map(item => <div className="recipe-ingredient" key={item.productId}><span>{item.name}<small>{item.quantity} {item.unit}</small></span><strong>{formatPrice(item.price)}</strong></div>)}{message.recipeAdded ? <div className="assistant-action-complete"><Check size={15} /> أُضيفت المقادير المتاحة إلى السلة</div> : <button className="button button-primary full-button" onClick={() => message.recipeActionId && applyConfirmedChange(message.recipeActionId, "add", message.ingredients ?? [])}><ShoppingCart size={16} /> تأكيد إضافة المقادير المتاحة للسلة</button>}</div> : <p className="missing-only-note">لا يوجد من مقادير الوصفة صنف متاح في المتجر الآن.</p>}{message.missingIngredients?.length ? <div className="missing-ingredients"><strong>مقادير غير متوفرة الآن — طلب توفير</strong><ul>{message.missingIngredients.map((item, i) => <li key={`${i}-${item}`}>{item}</li>)}</ul><p>يمكنك نسخ الطلب ولصقه في «ملاحظة للمتجر» عند تأكيد الطلب.</p><button type="button" className="small-button" onClick={() => void copyMissingRequest(message)}><Copy size={14} /> نسخ طلب توفير المقادير</button></div> : null}<details className="recipe-steps"><summary>طريقة التحضير <ChevronLeft size={16} /></summary><ol>{message.recipe.steps.map((step, stepIndex) => <li key={stepIndex}>{step}</li>)}</ol></details></div>}{message.cartAction?.status === "pending" && <div className="assistant-cart-confirm"><strong>{message.cartAction.type === "add" ? "طلب إضافة إلى السلة" : "طلب حذف من السلة"}</strong><ul>{message.cartAction.items.map(item => <li key={item.productId}><span>{item.name}</span><b>{item.quantity} {item.unit}</b></li>)}</ul><p>لن تتغير السلة إلا بعد تأكيدك.</p><div><button type="button" className="button button-primary" onClick={() => applyConfirmedChange(message.cartAction!.id, message.cartAction!.type, message.cartAction!.items)}>{message.cartAction.type === "add" ? "تأكيد الإضافة" : "تأكيد الحذف"}</button><button type="button" className="button button-quiet" onClick={() => cancelCartChange(message.cartAction!.id)}>إلغاء</button></div></div>}{message.cartAction?.status === "confirmed" && <div className="assistant-action-complete"><Check size={15} /> تم تنفيذ تغيير السلة بعد تأكيدك</div>}{message.cartAction?.status === "cancelled" && <div className="assistant-action-complete">لم يتم تغيير السلة.</div>}</div>)}{mutation.isPending && (
          <div className="chat-message from-assistant" style={{ maxWidth: "92%", background: "transparent", padding: 0, border: "none", boxShadow: "none" }}>
            <AiThinkingStatus queryText={messages.filter(m => m.role === "user").at(-1)?.text || input || "طلبك"} />
          </div>
        )}</div><form className="chat-input" onSubmit={send}><input maxLength={1200} value={input} onChange={event => setInput(event.target.value)} placeholder="مثال: أريد فكرة عشاء خفيف..." aria-label="رسالة للمساعد" disabled={mutation.isPending} /><button disabled={mutation.isPending || !input.trim()} aria-label="إرسال"><ArrowLeft size={18} /></button></form><div className="chat-hint"></div></section></main>;
}

function Loading() { return <div className="loading-state"><LoaderCircle size={22} className="spin" /><span>لحظة، نحدّث المعلومات...</span></div>; }
function LoadError({ onRetry }: { onRetry: () => void }) { return <div className="error-state"><span className="error-symbol">!</span><strong>تعذر تحميل البيانات</strong><p>تحقق من اتصالك ثم حاول مجددًا. لم نفترض وجود بيانات غير مؤكدة.</p><button className="button button-outline" onClick={onRetry}>إعادة المحاولة</button></div>; }

function shouldShowFooterDescription(description: string | null | undefined) {
  const text = description?.trim().replace(/\s+/g, " ");
  if (!text) return false;
  return text !== "كل ماتحتاجه باب بيتك بضغطه زر" && text !== "كل ما تحتاجه باب بيتك بضغطه زر";
}

export default function Home() {
  const [activeAiProduct, setActiveAiProduct] = useState<PublicProduct | null>(null);
  useGuestPushSubscriptionSync();
  const [location, navigate] = useLocation();
  const [instantStoreData, setInstantStoreData] = useState<HomeData>(getInstantLocalCatalog);
  const home = trpc.commerce.catalog.home.useQuery(undefined, {
    retry: 1,
    staleTime: 3000,
    refetchInterval: 3500,
    refetchOnWindowFocus: true,
  });
  useEffect(() => {
    if (home.data && Array.isArray(home.data.products)) {
      setInstantStoreData(home.data as HomeData);
      try { localStorage.setItem(INSTANT_CATALOG_KEY, JSON.stringify(home.data)); } catch {}
    }
  }, [home.data]);
  const data = ((home.data && home.data.products ? home.data : instantStoreData) ?? { categories: [], products: [], banners: [], offers: [], settings: {} }) as HomeData;
  const openProduct = (id: number) => navigate(`/product/${id}`);
  const currentNav = location.startsWith("/categories") ? "/categories" : location.startsWith("/products") ? "/products" : location.startsWith("/assistant") ? "/assistant" : location.startsWith("/account") ? "/account" : "/";
  const productPath = location.startsWith("/product/");
  const productId = productPath ? Number(location.split("/")[2]) : 0;
  const content = useMemo(() => {
    if (productPath && Number.isInteger(productId)) return <ProductDetail key={productId} id={productId} onBack={() => navigate("/")} onAiRecipe={setActiveAiProduct} />;
    if (location === "/products" || location.startsWith("/products?")) return <ProductListPage data={data} onOpen={openProduct} />;
    if (location === "/categories") return <CategoriesPage data={data} />;
    if (location === "/cart") return <CartPage minOrder={Number(data.settings?.minOrderAmount || 0)} />;
    if (location === "/favorites") return <FavoritesPage />;
    if (location === "/orders") return <OrdersPage />;
    if (location === "/account") return <AccountPage />;
    if (location === "/assistant") return <AssistantPage />;
    return <HomePage data={data} onOpen={openProduct} onAiRecipe={setActiveAiProduct} />;
  }, [location, productId, productPath, data]);
  return <div className="store-app" dir="rtl"><Header data={data} onSearch={text => navigate(`/products${text ? `?search=${encodeURIComponent(text)}` : ""}`)} />{home.isError && <div className="connection-strip"><span>الاتصال بالخدمة غير متاح مؤقتًا</span><button onClick={() => void home.refetch()}>إعادة المحاولة</button></div>}{home.isError && !home.data ? <main className="page-shell inner-page"><LoadError onRetry={() => void home.refetch()} /></main> : content}<footer className="store-footer"><div className="footer-brand"><span className={`brand-mark ${data.settings.storeIconUrl ? "has-brand-image" : ""}`}>{data.settings.storeIconUrl ? <img src={data.settings.storeIconUrl} alt="" /> : <Leaf size={18} />}</span><span><b>ORIGINAL</b><small>{data.settings.storeName === "ORIGINAL – أوريجنال" || !data.settings.storeName ? "أوريجنال" : data.settings.storeName}</small></span></div>{shouldShowFooterDescription(data.settings.storeDescription) && <span>{data.settings.storeDescription}</span>}<small>© {new Date().getFullYear()} {data.settings.storeName || "ORIGINAL"}</small></footer>{activeAiProduct && <AiRecipeModal product={activeAiProduct} onClose={() => setActiveAiProduct(null)} />}
    <BottomNav active={currentNav} /></div>;
}
