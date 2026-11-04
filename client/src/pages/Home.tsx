
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
  ArrowDownWideNarrow, ArrowLeft, ArrowUpDown, BadgePercent, BellRing, Check, ChevronDown, ChevronLeft, ChevronRight, CircleUserRound, Copy,
  Heart, Home as HomeIcon, Leaf, LoaderCircle, MapPin, Menu, MessageCircle, Minus, Package,
  Plus, Search, ShoppingBag, ShoppingCart, SlidersHorizontal, Sparkles, Trash2, Truck, UserRound,
  X, Bot, Clock3, ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { trpc } from "@/lib/trpc";
import { useStore, type CartLine } from "@/contexts/StoreContext";
import { cleanYemeniPhone, clearPendingOrderIdempotencyKey, getPendingOrderIdempotencyKey, isValidYemeniPhone, useCustomer } from "@/contexts/CustomerContext";
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
  const storeName = data?.settings.storeName || "ORIGINAL – أورجنال";
  const brandSubtitle = storeName === "ORIGINAL – أورجنال" ? "أورجنال" : storeName;
  const submitSearch = (event: FormEvent) => { event.preventDefault(); onSearch(text.trim()); };
  return <header className="store-header">
    <div className="header-main">
      <Link href="/" className="brand-lockup" aria-label={`${storeName} الرئيسية`}>
        <span className="brand-mark"><Leaf size={22} strokeWidth={1.8} /></span>
        <span className="brand-type"><strong>ORIGINAL</strong><small>{brandSubtitle}</small></span>
      </Link>
      <form className="header-search" onSubmit={submitSearch}>
        <Search size={18} /><input value={text} onChange={event => setText(event.target.value)} placeholder="ابحث عن احتياجاتك..." aria-label="البحث عن المنتجات" />
        {text && <button type="button" className="search-clear" onClick={() => { setText(""); onSearch(""); }} aria-label="مسح البحث"><X size={14} /></button>}
      </form>
      <div className="header-actions">
        <Link href="/favorites" className="header-action mobile-header-shortcut" aria-label="المفضلة" title="المفضلة"><Heart size={17} /><span>المفضلة</span></Link>
        <Link href="/orders" className="header-action mobile-header-shortcut" aria-label="طلباتي" title="طلباتي"><Package size={17} /><span>طلباتي</span></Link>
        <Link href="/cart" className="header-cart"><ShoppingCart size={17} /><span>السلة</span>{cartCount > 0 && <b>{cartCount}</b>}</Link>
        <Link href="/account" className="account-chip"><CircleUserRound size={17} /><span>{name.trim().split(/\s+/)[0] || "حسابي"}</span></Link>
      </div>
    </div>
    <div className="header-subline">
      <nav className="desktop-links" aria-label="القائمة الرئيسية"><Link href="/">الرئيسية</Link><Link href="/categories">الأقسام</Link><Link href="/products">المنتجات</Link><Link href="/assistant" className="assistant-link"><Sparkles size={15} /> مساعد أورجنال</Link></nav>
      <div className="header-promise"><ShieldCheck size={15} /><span></span></div><PWAInstall />
    </div>
    {(() => { const p = (globalThis as any).checkClientAutoPause ? (globalThis as any).checkClientAutoPause(data?.settings) : { paused: data?.settings.orderPaused === "true", msg: data?.settings.pausedMessage || "استقبال الطلبات متوقف مؤقتًا" }; return p.paused ? <div className="service-notice"><Clock3 size={15} />{p.msg}</div> : null; })()}
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

type BannerConfig = {
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

const defaultBannerCfg: BannerConfig = {
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

function parseBannerMeta(rawActionUrl?: string | null): { targetUrl: string; cfg: BannerConfig } {
  const raw = String(rawActionUrl || "").trim();
  const marker = "#bcfg=";
  const idx = raw.indexOf(marker);
  if (idx === -1) {
    return { targetUrl: raw, cfg: { ...defaultBannerCfg, clickMode: raw ? "full" : "none" } };
  }
  const targetUrl = raw.slice(0, idx).trim();
  try {
    const parsed = JSON.parse(decodeURIComponent(raw.slice(idx + marker.length)));
    return {
      targetUrl,
      cfg: {
        placement: ["top", "middle", "bottom", "popup"].includes(parsed.placement) ? parsed.placement : "top",
        size: ["auto", "small", "medium", "large"].includes(parsed.size) ? parsed.size : "auto",
        clickMode: ["full", "hotspot", "none"].includes(parsed.clickMode) ? parsed.clickMode : (targetUrl ? "full" : "none"),
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
    return { targetUrl, cfg: { ...defaultBannerCfg, clickMode: targetUrl ? "full" : "none" } };
  }
}

function BannerCarousel({ banners }: { banners: HomeData["banners"] }) {
  const [, navigate] = useLocation();
  const [index, setIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);
  useEffect(() => {
    if (banners.length < 2) return;
    const timer = window.setInterval(() => setIndex(value => (value + 1) % banners.length), 5200);
    return () => window.clearInterval(timer);
  }, [banners.length]);
  if (!banners.length) return null;
  const banner = banners[index % banners.length];
  if (!banner?.imageUrl) return null;
  const { targetUrl, cfg } = parseBannerMeta(banner.actionUrl);

  const goTarget = () => {
    if (!targetUrl) return;
    if (targetUrl.startsWith("/")) navigate(targetUrl);
    else window.location.href = targetUrl;
  };

  const sizeHeights: Record<BannerConfig["size"], string | undefined> = {
    auto: undefined,
    small: "clamp(115px, 18vw, 180px)",
    medium: "clamp(175px, 25vw, 275px)",
    large: "clamp(235px, 34vw, 380px)",
  };
  const isAutoSize = cfg.size === "auto";
  const isFullClick = Boolean(targetUrl && cfg.clickMode === "full");
  const isHotspotClick = Boolean(targetUrl && cfg.clickMode === "hotspot");

  return (
    <section
      className="banner-frame"
      aria-label="إعلانات المتجر"
      onClick={isFullClick ? goTarget : undefined}
      onTouchStart={e => { touchStartX.current = e.touches[0]?.clientX ?? null; }}
      onTouchEnd={e => {
        if (touchStartX.current === null || banners.length < 2) return;
        const diff = (e.changedTouches[0]?.clientX ?? touchStartX.current) - touchStartX.current;
        touchStartX.current = null;
        if (Math.abs(diff) > 40) {
          setIndex(v => diff > 0 ? (v + 1) % banners.length : (v - 1 + banners.length) % banners.length);
        }
      }}
      style={{
        position: "relative",
        height: isAutoSize ? "auto" : sizeHeights[cfg.size],
        minHeight: isAutoSize ? 0 : sizeHeights[cfg.size],
        borderRadius: "20px",
        overflow: "hidden",
        margin: "6px 0 24px",
        background: "transparent",
        cursor: isFullClick ? "pointer" : "default",
        boxShadow: "0 10px 26px rgba(15, 45, 30, 0.08)",
      }}
    >
      <img
        src={banner.imageUrl}
        alt={banner.title || "إعلان المتجر"}
        loading="eager"
        decoding="async"
        fetchPriority="high"
        style={isAutoSize ? {
          position: "relative",
          width: "100%",
          height: "auto",
          display: "block",
          objectFit: "contain",
          zIndex: 1,
        } : {
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          zIndex: 1,
        }}
      />
      {cfg.shade && <div className="banner-shade" style={{ zIndex: 2 }} />}
      {(cfg.showTitle || (cfg.showBtn && banner.actionText && targetUrl)) && (
        <div className="banner-copy" style={{ zIndex: 3 }}>
          {cfg.showTitle && banner.title && <h2>{banner.title}</h2>}
          {cfg.showTitle && banner.body && <p>{banner.body}</p>}
          {cfg.showBtn && banner.actionText && targetUrl && (
            <button type="button" onClick={e => { e.stopPropagation(); goTarget(); }} className="button button-light">
              {banner.actionText}<ArrowLeft size={16} />
            </button>
          )}
        </div>
      )}
      {isHotspotClick && (
        <button
          type="button"
          aria-label={banner.actionText || banner.title || "انتقال للعرض"}
          onClick={e => { e.stopPropagation(); goTarget(); }}
          style={{
            position: "absolute",
            left: cfg.hx + "%",
            top: cfg.hy + "%",
            width: cfg.hw + "%",
            height: cfg.hh + "%",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            zIndex: 5,
            padding: 0,
          }}
        />
      )}
      {banners.length > 1 && (
        <div className="banner-dots" style={{ zIndex: 6 }}>
          {banners.map((item, dot) => (
            <button key={item.id} type="button" className={dot === index ? "active" : ""} aria-label={"الإعلان " + (dot + 1)} onClick={e => { e.stopPropagation(); setIndex(dot); }} />
          ))}
        </div>
      )}
    </section>
  );
}

function PromoPopupModal({ banners }: { banners: HomeData["banners"] }) {
  const [, navigate] = useLocation();
  const [openBanner, setOpenBanner] = useState<HomeData["banners"][number] | null>(null);

  useEffect(() => {
    if (!banners.length) return;
    const candidate = banners[0];
    if (!candidate?.imageUrl) return;
    const { cfg } = parseBannerMeta(candidate.actionUrl);
    const storageKey = "original-popup-seen-" + candidate.id;
    if (cfg.popupOnce) {
      try {
        if (sessionStorage.getItem(storageKey) === "1") return;
      } catch {}
    }
    setOpenBanner(candidate);
  }, [banners]);

  if (!openBanner || !openBanner.imageUrl) return null;
  const { targetUrl, cfg } = parseBannerMeta(openBanner.actionUrl);

  const closePopup = () => {
    try { sessionStorage.setItem("original-popup-seen-" + openBanner.id, "1"); } catch {}
    setOpenBanner(null);
  };

  const goTarget = () => {
    closePopup();
    if (!targetUrl) return;
    if (targetUrl.startsWith("/")) navigate(targetUrl);
    else window.location.href = targetUrl;
  };

  const isFullClick = Boolean(targetUrl && cfg.clickMode === "full");
  const isHotspotClick = Boolean(targetUrl && cfg.clickMode === "hotspot");

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      onClick={closePopup}
      style={{ zIndex: 120, background: "rgba(8, 22, 15, 0.72)", padding: "18px" }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          position: "relative",
          width: "min(460px, 94vw)",
          borderRadius: "22px",
          overflow: "hidden",
          background: "transparent",
          boxShadow: "0 24px 60px rgba(0,0,0,0.45)",
        }}
      >
        <button
          type="button"
          onClick={closePopup}
          aria-label="إغلاق الإعلان"
          style={{
            position: "absolute",
            top: "10px",
            right: "10px",
            width: "34px",
            height: "34px",
            borderRadius: "50%",
            border: "none",
            background: "rgba(15, 38, 26, 0.82)",
            color: "#ffffff",
            display: "grid",
            placeItems: "center",
            cursor: "pointer",
            zIndex: 10,
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        >
          <X size={18} />
        </button>
        <div
          onClick={isFullClick ? goTarget : undefined}
          style={{ position: "relative", cursor: isFullClick ? "pointer" : "default", lineHeight: 0 }}
        >
          <img
            src={openBanner.imageUrl}
            alt={openBanner.title || "عرض خاص"}
            style={{ width: "100%", height: "auto", maxHeight: "82vh", objectFit: "contain", display: "block", borderRadius: "22px" }}
          />
          {isHotspotClick && (
            <button
              type="button"
              aria-label="انتقال للعرض"
              onClick={e => { e.stopPropagation(); goTarget(); }}
              style={{
                position: "absolute",
                left: cfg.hx + "%",
                top: cfg.hy + "%",
                width: cfg.hw + "%",
                height: cfg.hh + "%",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                zIndex: 5,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}


function parseAssistantMessageAndSuggestions(rawText?: string) {
  const text = rawText || "";
  const match = text.match(/\[\[SUGGESTIONS:([^\]]+)\]\]/);
  const cleanText = text.replace(/\s*\[\[SUGGESTIONS:[^\]]+\]\]/g, "").trim();
  const suggestions = match
    ? match[1].split("|").map(s => s.trim()).filter(Boolean)
    : [];
  return { cleanText, suggestions };
}

function AiThinkingStatus() {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 10px", color: "#64748b", fontSize: "11.5px", fontWeight: 500 }} aria-live="polite">
      <span style={{ width: "6px", height: "6px", borderRadius: "999px", background: "#174b36", animation: "pulse 1.2s infinite" }} />
      <span>جاري التفكير...</span>
    </div>
  );
}

function splitCleanReplyAndChips(rawText: string, fallbackChips?: string[]) {
  const raw = String(rawText || "");
  const rawList: string[] = [];
  const match = raw.match(/\[\[SUGGESTIONS:([\s\S]*?)\]\]/i);
  if (match) {
    rawList.push(...match[1].split("|"));
  } else if (Array.isArray(fallbackChips) && fallbackChips.length > 0) {
    rawList.push(...fallbackChips);
  }
  const seen = new Set<string>();
  const chips: string[] = [];
  for (const item of rawList) {
    const c = String(item || "").replace(/^[\s"'•✨*-]+|[\s"']+$/g, "").trim();
    if (c && c.length >= 2 && !seen.has(c)) {
      seen.add(c);
      chips.push(c);
    }
    if (chips.length >= 3) break;
  }
  const cleanText = raw.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/gi, "").trim();
  return { cleanText, chips };
}

const tinyChipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  width: "auto",
  minHeight: "22px",
  padding: "2px 8px",
  borderRadius: "6px",
  background: "#f1f5f2",
  border: "1px solid #d5e2d8",
  color: "#174b36",
  fontSize: "10.5px",
  fontWeight: 600,
  lineHeight: 1.3,
  cursor: "pointer"
};

function AiRecipeModal({ product, onClose }: { product: PublicProduct; onClose: () => void }) {
  const { add } = useStore();
  const [, navigate] = useLocation();
  const [customInput, setCustomInput] = useState('');
  const [activeMod, setActiveMod] = useState('');
  const recipeMutation = trpc.commerce.assistant.recipe.useMutation();

  const isDrinkOrSnack = useMemo(() => {
    return /(?:عصير|شراب|مشروب|موسي|استروك|طاقة|طاقه|زنجبيل|ون سي|راني|دلتا|روابي|سيزر|سن توب|بيبسي|كوكاكولا|سفن|ميرندا|فانتا|سبرايت|مياه|ماء|بسكويت|شيبس|شوكولاتة|شوكولاته|كيك)/i.test(product.name);
  }, [product.name]);

  const askForProduct = (modification = '') => {
    setActiveMod(modification);
    const baseReq = isDrinkOrSnack
      ? ('ما هي أفضل 3 طرق تقديم وأفكار للاستمتاع بـ «' + product.name + '» (تقديم بارد ومنعش، خلطة مبتكرة، وأفضل وقت وسناك معه)؟')
      : ('ما هي أفضل 3 طرق لتحضير «' + product.name + '» (اقتصادية وسريعة، وشعبية يمنية، وصحية مميزة)؟');
    recipeMutation.mutate({
      request: modification ? (baseReq + ' التعديل المطلوب: ' + modification) : baseReq,
    });
  };

  useEffect(() => {
    askForProduct('');
  }, [product.id]);

  const data = recipeMutation.data;
  const isPending = recipeMutation.isPending;

  const continueInAssistantChat = () => {
    try {
      const existingRaw = localStorage.getItem('original-assistant-history-v2');
      const existing = existingRaw ? JSON.parse(existingRaw) : [];
      const historyArr = Array.isArray(existing) ? existing : [];
      const userTurn = {
        role: 'user',
        text: activeMod
          ? ('أريد أفكار وطريقة تحضير «' + product.name + '» (' + activeMod + ')')
          : ('أريد أفضل أفكار وطرق تحضير لـ «' + product.name + '»'),
      };
      const assistantTurn = data
        ? {
            role: 'assistant',
            text: data.message,
            contextText: 'نتحدث عن المنتج المتوفر في المتجر: «' + product.name + '» بسعر ' + formatPrice(product.price),
          }
        : null;
      const nextHistory = [...historyArr, userTurn, ...(assistantTurn ? [assistantTurn] : [])].slice(-32);
      localStorage.setItem('original-assistant-history-v2', JSON.stringify(nextHistory));
    } catch {}
    onClose();
    navigate('/assistant');
  };

  const quickMods = isDrinkOrSnack
    ? [
        '🧊 تقديم بارد ومنعش جداً',
        '🍹 خلطة موكيتل مبتكرة به',
        '🥨 أفضل سناك خفيف معه',
        '⚡ أفضل وقت لتناوله',
      ]
    : [
        '⚡ وصفة اقتصادية وسريعة جداً',
        '🌿 بدون توابل / خفيفة التوابل',
        '🇾🇪 وصفة يمنية شعبية أصيلة',
        '🥗 وجبة صحية وخفيفة',
      ];

  return (
    <div className='modal-backdrop' role='presentation' onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
      <section className='checkout-modal' role='dialog' aria-modal='true' style={{ maxWidth: '540px' }}>
        <div className='modal-heading'>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ width: '36px', height: '36px', borderRadius: '12px', background: '#edf3e9', color: '#174b36', display: 'grid', placeItems: 'center' }}>
              <Sparkles size={20} />
            </span>
            <div>
              <span className='eyebrow'>المساعد والشيف الذكي · أورجنال</span>
              <h2 style={{ fontSize: '16px' }}>أفكار وطرق: {product.name}</h2>
            </div>
          </div>
          <button type='button' className='icon-button' onClick={onClose}><X size={19} /></button>
        </div>

        <div style={{ maxHeight: '70vh', overflowY: 'auto', padding: '10px 4px', fontSize: '12px', lineHeight: '1.8' }}>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {quickMods.map(mod => (
              <button
                key={mod}
                type='button'
                disabled={isPending}
                onClick={() => askForProduct(mod)}
                style={{
                  padding: '6px 11px',
                  borderRadius: '999px',
                  border: activeMod === mod ? '1.5px solid #174b36' : '1px solid #d5e0d3',
                  background: activeMod === mod ? '#174b36' : '#f5f8f3',
                  color: activeMod === mod ? '#ffffff' : '#253e31',
                  fontSize: '11px',
                  fontWeight: 800,
                  cursor: 'pointer',
                }}
              >
                {mod}
              </button>
            ))}
          </div>

          {isPending ? (
            <div style={{ padding: '12px 4px' }}>
              <AiThinkingStatus />
            </div>
          ) : recipeMutation.error ? (
            <div style={{ padding: '20px 10px', textAlign: 'center', color: '#9c3b37' }}>
              <p>{recipeMutation.error.message || 'تعذر جلب الأفكار الآن.'}</p>
              <button className='button button-outline' onClick={() => askForProduct(activeMod)}>إعادة المحاولة</button>
            </div>
          ) : data ? (
            <div>
              <div style={{ background: '#f5f8f3', border: '1px solid #dce8d8', borderRadius: '14px', padding: '14px', marginBottom: '12px', whiteSpace: 'pre-line', color: '#1e382b', fontSize: '13px', lineHeight: 1.75 }}>
                {data.message}
              </div>

              <div style={{ background: '#edf5f0', border: '1px solid #cde0d4', borderRadius: '14px', padding: '12px', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <div>
                  <strong style={{ fontSize: '13px', color: '#143a28', display: 'block' }}>{product.name}</strong>
                  <small style={{ color: '#4d6658', fontSize: '11.5px', fontWeight: 800 }}>{formatPrice(product.price)} / {product.unit}</small>
                </div>
                <button
                  type='button'
                  className='button button-primary'
                  style={{ minHeight: '38px', padding: '6px 14px', borderRadius: '11px', fontSize: '12.5px', fontWeight: 800 }}
                  onClick={() => {
                    add(product, product.minQuantity || 1);
                    toast.success('تمت إضافة «' + product.name + '» إلى سلتك ✓');
                  }}
                >
                  <ShoppingCart size={15} /> أضف «{product.name}» للسلة
                </button>
              </div>

              <form
                onSubmit={e => {
                  e.preventDefault();
                  if (!customInput.trim() || isPending) return;
                  askForProduct(customInput.trim());
                  setCustomInput('');
                }}
                style={{ display: 'flex', gap: '6px', marginTop: '8px', marginBottom: '10px' }}
              >
                <input
                  value={customInput}
                  onChange={e => setCustomInput(e.target.value)}
                  placeholder='اطلب تعديلاً خاصاً (مثلاً: بدون سكر، طريقة سريعة، لـ 4 أشخاص)...'
                  style={{ flex: 1, padding: '8px 11px', borderRadius: '11px', border: '1px solid #cddbd2', fontSize: '12px' }}
                />
                <button type='submit' className='button button-primary' disabled={isPending || !customInput.trim()} style={{ minHeight: '38px', padding: '0 14px', borderRadius: '11px' }}>
                  <Sparkles size={15} />
                </button>
              </form>

              <button type='button' className='button button-outline full-button' onClick={continueInAssistantChat} style={{ fontSize: '12px' }}>
                <Sparkles size={15} /> متابعة النقاش في صفحة المساعد الذكي
              </button>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
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

function formatWeightLabel(grams: number): string {
  if (grams <= 0) return "0 جرام";
  if (grams === 125) return "125 جرام (ثمن كيلو)";
  if (grams === 250) return "250 جرام (ربع كيلو)";
  if (grams === 500) return "500 جرام (نصف كيلو)";
  if (grams === 1000) return "1 كيلو كامل (1000 جرام)";
  if (grams > 1000) return (grams / 1000).toFixed(2).replace(/\.?0+$/, "") + " كيلو (" + grams.toLocaleString("en-US") + " جرام)";
  return grams.toLocaleString("en-US") + " جرام";
}

function VariantPickerModal({
  product,
  variants,
  weightEnabled = false,
  minWeightAmount = 100,
  initialVariant,
  initialQty,
  onClose,
}: {
  product: PublicProduct;
  variants: string[];
  weightEnabled?: boolean;
  minWeightAmount?: number;
  initialVariant?: string;
  initialQty?: number;
  onClose: () => void;
}) {
  const { add } = useStore();
  const [selected, setSelected] = useState<string>(initialVariant && variants.includes(initialVariant) ? initialVariant : (variants[0] || ""));
  const [qty, setQty] = useState<number>(initialQty || product.minQuantity || 1);
  const [buyMode, setBuyMode] = useState<"price" | "weight">("price");
  const pricePerKg = Math.max(1, product.price);
  const effectiveMin = Math.min(minWeightAmount, Math.max(50, Math.round(pricePerKg * 0.125)));
  const defaultAmount = Math.max(effectiveMin, Math.round(pricePerKg * 0.25) || 200);
  const [amountStr, setAmountStr] = useState<string>(String(defaultAmount));
  const [gramsStr, setGramsStr] = useState<string>("250");
  const step = product.quantityStep || 1;
  const minQ = product.minQuantity || 1;
  const maxQ = product.stock === null ? 9999 : product.stock;

  const finalGrams = buyMode === "price"
    ? Math.max(0, Math.round(((Math.max(0, Number(amountStr) || 0)) / pricePerKg) * 1000))
    : Math.max(0, Math.round(Number(gramsStr) || 0));
  const finalAmount = buyMode === "price"
    ? Math.max(0, Math.floor(Number(amountStr) || 0))
    : Math.max(0, Math.round((finalGrams / 1000) * pricePerKg));
  const weightText = formatWeightLabel(finalGrams);
  const isAmountValid = !weightEnabled || (finalAmount >= effectiveMin && finalGrams > 0);

  const confirmAdd = () => {
    if (variants.length > 0 && !selected) return;
    if (weightEnabled) {
      if (!isAmountValid) {
        toast.error("أقل مبلغ للشراء هو " + formatPrice(effectiveMin));
        return;
      }
      const vLabel = selected ? (selected + " · " + weightText) : weightText;
      const displayTitle = product.name + " (" + vLabel + ")";
      add({
        ...product,
        name: displayTitle,
        price: finalAmount,
        unit: weightText,
        variant: vLabel,
        customAmount: finalAmount,
      }, 1);
      toast.success("أُضيف «" + displayTitle + "» بمبلغ " + formatPrice(finalAmount));
      onClose();
      return;
    }
    if (selected) {
      add({ ...product, name: product.name + " (" + selected + ")", variant: selected }, qty);
      toast.success("تمت إضافة «" + product.name + " (" + selected + ")» إلى السلة");
    } else {
      add(product, qty);
      toast.success("أُضيف المنتج إلى السلة");
    }
    onClose();
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose} style={{ zIndex: 140 }}>
      <section className="checkout-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: "370px", padding: "18px", borderRadius: "22px" }}>
        <div className="modal-heading" style={{ marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {product.imageUrl && <img src={product.imageUrl} alt="" style={{ width: "44px", height: "44px", borderRadius: "12px", objectFit: "cover" }} />}
            <div>
              <h2 style={{ fontSize: "16px", margin: "0 0 2px" }}>{product.name}</h2>
              <small style={{ color: "#174b36", fontWeight: 800 }}>
                {weightEnabled ? ("سعر الكيلو: " + formatPrice(product.price)) : (formatPrice(product.price) + " / " + product.unit)}
              </small>
            </div>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="إغلاق"><X size={18} /></button>
        </div>

        {variants.length > 0 && (
          <div style={{ display: "grid", gap: "6px", marginBottom: "12px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: "6px" }}>
              {variants.map(v => {
                const isSel = selected === v;
                return (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setSelected(v)}
                    style={{ padding: "9px", borderRadius: "11px", border: isSel ? "2px solid #174b36" : "1px solid #d5e2d8", background: isSel ? "#174b36" : "#f7faf8", color: isSel ? "#ffffff" : "#1b3829", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}
                  >
                    {v}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {weightEnabled ? (
          <div style={{ display: "grid", gap: "12px", marginBottom: "14px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", background: "#f2f6f3", padding: "5px", borderRadius: "14px" }}>
              <button
                type="button"
                onClick={() => setBuyMode("price")}
                style={{ padding: "10px 8px", borderRadius: "10px", border: "none", background: buyMode === "price" ? "#174b36" : "transparent", color: buyMode === "price" ? "#ffffff" : "#174b36", fontWeight: 800, fontSize: "12.5px", cursor: "pointer", transition: "0.15s" }}
              >
                💰 الشراء بالسعر
              </button>
              <button
                type="button"
                onClick={() => setBuyMode("weight")}
                style={{ padding: "10px 8px", borderRadius: "10px", border: "none", background: buyMode === "weight" ? "#174b36" : "transparent", color: buyMode === "weight" ? "#ffffff" : "#174b36", fontWeight: 800, fontSize: "12.5px", cursor: "pointer", transition: "0.15s" }}
              >
                ⚖️ الشراء بالوزن
              </button>
            </div>

            {buyMode === "price" ? (
              <div style={{ display: "grid", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 700, color: "#2b4736", textAlign: "center" }}>اكتب المبلغ الذي تريد الشراء به (ر.ي):</label>
                <input
                  type="number"
                  min={effectiveMin}
                  step="50"
                  value={amountStr}
                  onChange={e => setAmountStr(e.target.value)}
                  placeholder="مثلاً: 500"
                  style={{ width: "100%", padding: "10px", borderRadius: "12px", border: "1.5px solid #174b36", fontSize: "17px", fontWeight: 800, textAlign: "center", background: "#ffffff", color: "#113a28" }}
                />
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "6px" }}>
                {[
                  { label: "ثمن كيلو", g: 125 },
                  { label: "ربع كيلو", g: 250 },
                  { label: "نصف كيلو", g: 500 },
                  { label: "كيلو كامل", g: 1000 },
                ].map(w => {
                  const active = finalGrams === w.g;
                  return (
                    <button
                      key={w.g}
                      type="button"
                      onClick={() => setGramsStr(String(w.g))}
                      style={{ padding: "10px 4px", borderRadius: "11px", border: active ? "2px solid #174b36" : "1px solid #d5e3da", background: active ? "#eaf5ee" : "#ffffff", color: "#174b36", fontWeight: 800, fontSize: "11.5px", cursor: "pointer" }}
                    >
                      {w.label}
                    </button>
                  );
                })}
              </div>
            )}

            <div style={{ padding: "10px 14px", borderRadius: "12px", background: "#f4f8f5", border: "1px solid #cde0d3", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px", fontWeight: 800, color: "#174b36" }}>
              <span>الوزن: {weightText}</span>
              <span>المبلغ: {formatPrice(finalAmount)}</span>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", padding: "10px 12px", borderRadius: "12px", background: "#f4f7f3" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#2b4736" }}>الكمية ({product.unit}):</span>
            <div className="quantity-compact">
              <button type="button" aria-label="تقليل" onClick={() => setQty(q => Math.max(minQ, q - step))}><Minus size={14} /></button>
              <b>{qty}</b>
              <button type="button" aria-label="زيادة" disabled={qty + step > maxQ} onClick={() => setQty(q => Math.min(maxQ, q + step))}><Plus size={14} /></button>
            </div>
          </div>
        )}

        <button type="button" className="button button-primary full-button" disabled={!isAmountValid} onClick={confirmAdd}>
          <ShoppingCart size={17} />
          {weightEnabled
            ? ("تأكيد الإضافة (" + formatPrice(finalAmount) + ")")
            : ("إضافة إلى السلة (" + formatPrice(product.price * qty) + ")")}
        </button>
      </section>
    </div>
  );
}

function ProductCard({ product, onOpen, onAiRecipe, priority = false }: { product: PublicProduct; onOpen: () => void; onAiRecipe?: (p: PublicProduct) => void; priority?: boolean }) {
  const { add, isFavorite, toggleFavorite } = useStore();
  const favorite = isFavorite(product.id);
  const disabled = product.stock !== null && product.stock < (product.minQuantity || 1);
  const { variants, weightEnabled, minWeightAmount } = useMemo(() => unpackProductVariants(product.description), [product.description]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerVariant, setPickerVariant] = useState<string>("");

  const handleAddClick = (e: React.MouseEvent, preferredVariant?: string) => {
    e.stopPropagation();
    if (disabled) return;
    if (variants.length > 0 || weightEnabled) {
      setPickerVariant(preferredVariant || variants[0] || "");
      setPickerOpen(true);
      return;
    }
    add(product, product.minQuantity || 1);
    toast.success("أُضيف إلى السلة");
  };

  return <>
    <article className="product-card">
      <div className="product-visual" onClick={onOpen} role="button" tabIndex={0} onKeyDown={event => { if (event.key === "Enter") onOpen(); }}>
        {product.imageUrl ? <img src={product.imageUrl} alt={product.name} loading="eager" fetchPriority={priority ? "high" : "auto"} decoding="async" /> : <div className="product-no-image"><Leaf size={27} strokeWidth={1.4} /><span>صورة المنتج</span></div>}
        <button type="button" className={"favorite-toggle " + (favorite ? "is-favorite" : "")} aria-label={favorite ? "إزالة من المفضلة" : "أضف للمفضلة"} aria-pressed={favorite} onClick={event => { event.stopPropagation(); toggleFavorite(product.id); toast.success(favorite ? "أُزيل من المفضلة" : "أُضيف إلى المفضلة على هذا الجهاز"); }}><Heart size={17} fill={favorite ? "currentColor" : "none"} /></button>
        {onAiRecipe && <button type="button" className="ai-recipe-toggle" aria-label="أفكار وتحضير بالذكاء الاصطناعي" title="أفكار ووصفات تحضير" onClick={event => { event.stopPropagation(); onAiRecipe(product); }}><Sparkles size={16} /></button>}
        {disabled && <span className="product-sold-out">غير متوفر</span>}
      </div>
      <button type="button" className="product-title-button" onClick={onOpen}><strong>{product.name}</strong><span>{product.unit}</span></button>
      <div className="product-card-bottom"><div><b>{formatPrice(product.price)}</b><small> / {product.unit}</small></div><button type="button" className="add-button" disabled={disabled} onClick={e => handleAddClick(e)} aria-label={"إضافة " + product.name + " للسلة"}><Plus size={18} /></button></div>
    </article>
    {pickerOpen && (
      <VariantPickerModal
        product={product}
        variants={variants}
        weightEnabled={weightEnabled}
        minWeightAmount={minWeightAmount}
        initialVariant={pickerVariant}
        onClose={() => setPickerOpen(false)}
      />
    )}
  </>;
}


function ProductGrid({ items, onOpen, onAiRecipe, maxItems, totalStoreCount, onViewAll, gridKey = "default" }: { items: PublicProduct[]; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void; maxItems?: number; totalStoreCount?: number; onViewAll?: () => void; gridKey?: string }) {
  const BATCH = 12;
  const list = useMemo(() => (maxItems ? items.slice(0, maxItems) : items), [items, maxItems]);
  const getSaved = () => { try { const m = (window as any).__gridVisibleCounts || {}; return m[gridKey] >= BATCH ? m[gridKey] : BATCH; } catch { return BATCH; } };
  const [visibleCount, setVisibleCount] = useState<number>(getSaved);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const prevKey = useRef(gridKey);
  useEffect(() => { if (prevKey.current !== gridKey) { prevKey.current = gridKey; setVisibleCount(getSaved()); setLoadingMore(false); } }, [gridKey]);
  useEffect(() => { try { const w = window as any; w.__gridVisibleCounts = w.__gridVisibleCounts || {}; w.__gridVisibleCounts[gridKey] = visibleCount; } catch {} }, [visibleCount, gridKey]);
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      if (cancelled) return;
      const w = window as any;
      const seen: Set<string> = w.__preloadedImgSet || (w.__preloadedImgSet = new Set<string>());
      const slice = list.slice(0, Math.min(list.length, visibleCount + BATCH));
      let idx = 0;
      const step = () => {
        if (cancelled) return;
        let count = 0;
        while (idx < slice.length && count < 4) {
          const url = slice[idx++]?.imageUrl;
          if (url && !seen.has(url)) {
            seen.add(url);
            const img = new Image();
            img.decoding = "async";
            img.src = url;
            count++;
          }
        }
        if (idx < slice.length) setTimeout(step, 35);
      };
      step();
    }, 45);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [list, visibleCount]);
  useEffect(() => {
    if (visibleCount >= list.length || loadingMore) return;
    const node = loadMoreRef.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(entries => {
      if (entries[0]?.isIntersecting) {
        setLoadingMore(true);
        setTimeout(() => { setVisibleCount(c => Math.min(list.length, c + BATCH)); setLoadingMore(false); }, 220);
      }
    }, { rootMargin: "120px 0px" });
    obs.observe(node);
    return () => obs.disconnect();
  }, [visibleCount, list.length, loadingMore]);
  if (!list.length) return <EmptyState icon={ShoppingBag} title="المتجر ينتظر منتجاته الأولى" description="لا توجد منتجات منشورة في هذا القسم حالياً." action="تصفح الأقسام" href="/categories" />;
  const visibleItems = list.slice(0, visibleCount);
  const done = visibleCount >= list.length;
  const total = totalStoreCount ?? items.length;
  return <>
    <div className="product-grid">{visibleItems.map((p, i) => <ProductCard key={p.id} product={p} priority={i < 8} onOpen={() => onOpen(p.id)} onAiRecipe={onAiRecipe} />)}</div>
    {!done && <div ref={loadMoreRef} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", padding: "18px 12px", margin: "10px auto", color: "#174b36", fontWeight: 800, fontSize: "0.86rem" }}><div style={{ width: "22px", height: "22px", borderRadius: "50%", border: "2.5px solid #d5e6dc", borderTopColor: "#174b36", animation: "spin 0.65s linear infinite" }} /><span>جاري تحميل المزيد من المنتجات...</span></div>}
    {done && maxItems && total > maxItems && onViewAll && <div style={{ display: "flex", justifyContent: "center", padding: "18px 12px 10px" }}><button type="button" onClick={onViewAll} style={{ display: "inline-flex", alignItems: "center", gap: "10px", padding: "14px 28px", borderRadius: "18px", background: "linear-gradient(135deg, #174b36 0%, #0f3525 100%)", color: "#fff", border: "1.5px solid #d4af37", fontWeight: 900, fontSize: "0.95rem", boxShadow: "0 10px 24px rgba(15, 53, 37, 0.22)", cursor: "pointer" }}><span>عرض جميع المنتجات ({total} منتج)</span><ArrowLeft size={18} /></button></div>}
  </>;
}
function ProductCard({ product, onOpen, onAiRecipe, priority = false }: { product: PublicProduct; onOpen: () => void; onAiRecipe?: (p: PublicProduct) => void; priority?: boolean }) {
  const { add, isFavorite, toggleFavorite } = useStore();
  const favorite = isFavorite(product.id);
  const disabled = product.stock !== null && product.stock < (product.minQuantity || 1);
  const { variants, weightEnabled, minWeightAmount } = useMemo(() => unpackProductVariants(product.description), [product.description]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerVariant, setPickerVariant] = useState<string>("");

  const handleAddClick = (e: React.MouseEvent, preferredVariant?: string) => {
    e.stopPropagation();
    if (disabled) return;
    if (variants.length > 0 || weightEnabled) {
      setPickerVariant(preferredVariant || variants[0] || "");
      setPickerOpen(true);
      return;
    }
    add(product, product.minQuantity || 1);
    toast.success("أُضيف إلى السلة");
  };

  return <>
    <article className="product-card">
      <div className="product-visual" onClick={onOpen} role="button" tabIndex={0} onKeyDown={event => { if (event.key === "Enter") onOpen(); }}>
        {product.imageUrl ? <img src={product.imageUrl} alt={product.name} loading="eager" fetchPriority={priority ? "high" : "auto"} decoding="async" /> : <div className="product-no-image"><Leaf size={27} strokeWidth={1.4} /><span>صورة المنتج</span></div>}
        <button type="button" className={"favorite-toggle " + (favorite ? "is-favorite" : "")} aria-label={favorite ? "إزالة من المفضلة" : "أضف للمفضلة"} aria-pressed={favorite} onClick={event => { event.stopPropagation(); toggleFavorite(product.id); toast.success(favorite ? "أُزيل من المفضلة" : "أُضيف إلى المفضلة على هذا الجهاز"); }}><Heart size={17} fill={favorite ? "currentColor" : "none"} /></button>
        {onAiRecipe && <button type="button" className="ai-recipe-toggle" aria-label="أفكار وتحضير بالذكاء الاصطناعي" title="أفكار ووصفات تحضير" onClick={event => { event.stopPropagation(); onAiRecipe(product); }}><Sparkles size={16} /></button>}
        {disabled && <span className="product-sold-out">غير متوفر</span>}
      </div>
      <button type="button" className="product-title-button" onClick={onOpen}><strong>{product.name}</strong><span>{product.unit}</span></button>
      <div className="product-card-bottom"><div><b>{formatPrice(product.price)}</b><small> / {product.unit}</small></div><button type="button" className="add-button" disabled={disabled} onClick={e => handleAddClick(e)} aria-label={"إضافة " + product.name + " للسلة"}><Plus size={18} /></button></div>
    </article>
    {pickerOpen && (
      <VariantPickerModal
        product={product}
        variants={variants}
        weightEnabled={weightEnabled}
        minWeightAmount={minWeightAmount}
        initialVariant={pickerVariant}
        onClose={() => setPickerOpen(false)}
      />
    )}
  </>;
}


function ProductGrid({ items, onOpen, onAiRecipe, maxItems, totalStoreCount, onViewAll, gridKey = "default" }: { items: PublicProduct[]; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void; maxItems?: number; totalStoreCount?: number; onViewAll?: () => void; gridKey?: string }) {
  const BATCH = 12;
  const list = useMemo(() => (maxItems ? items.slice(0, maxItems) : items), [items, maxItems]);
  const getSaved = () => { try { const m = (window as any).__gridVisibleCounts || {}; return m[gridKey] >= BATCH ? m[gridKey] : BATCH; } catch { return BATCH; } };
  const [visibleCount, setVisibleCount] = useState<number>(getSaved);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const prevKey = useRef(gridKey);
  useEffect(() => { if (prevKey.current !== gridKey) { prevKey.current = gridKey; setVisibleCount(getSaved()); setLoadingMore(false); } }, [gridKey]);
  useEffect(() => { try { const w = window as any; w.__gridVisibleCounts = w.__gridVisibleCounts || {}; w.__gridVisibleCounts[gridKey] = visibleCount; } catch {} }, [visibleCount, gridKey]);
  useEffect(() => {
    for (const p of list.slice(0, Math.min(list.length, visibleCount + BATCH))) {
      if (p.imageUrl) { const img = new Image(); img.decoding = "async"; img.src = p.imageUrl; }
    }
  }, [list, visibleCount]);
  useEffect(() => {
    if (visibleCount >= list.length || loadingMore) return;
    const node = loadMoreRef.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(entries => {
      if (entries[0]?.isIntersecting) {
        setLoadingMore(true);
        setTimeout(() => { setVisibleCount(c => Math.min(list.length, c + BATCH)); setLoadingMore(false); }, 250);
      }
    }, { rootMargin: "110px 0px" });
    obs.observe(node);
    return () => obs.disconnect();
  }, [visibleCount, list.length, loadingMore]);
  if (!list.length) return <EmptyState icon={ShoppingBag} title="المتجر ينتظر منتجاته الأولى" description="لا توجد منتجات منشورة في هذا القسم حالياً." action="تصفح الأقسام" href="/categories" />;
  const visibleItems = list.slice(0, visibleCount);
  const done = visibleCount >= list.length;
  const total = totalStoreCount ?? items.length;
  return <>
    <div className="product-grid">{visibleItems.map((p, i) => <ProductCard key={p.id} product={p} priority={i < 12} onOpen={() => onOpen(p.id)} onAiRecipe={onAiRecipe} />)}</div>
    {!done && <div ref={loadMoreRef} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "18px 0 10px", color: "#174b36", fontSize: "12.5px", fontWeight: 800 }}><LoaderCircle size={20} className="spin" /><span>جارٍ عرض المزيد من المنتجات...</span></div>}
    {done && onViewAll && <div style={{ textAlign: "center", padding: "20px 0 10px" }}><button type="button" className="button button-primary" onClick={onViewAll} style={{ minHeight: "44px", padding: "10px 24px", borderRadius: "14px", fontSize: "13.5px", fontWeight: 800, display: "inline-flex", alignItems: "center", gap: "8px" }}><span>عرض جميع المنتجات ({total} منتج)</span><ArrowLeft size={16} /></button></div>}
  </>;
}
function CategoryStrip({ data, onSelect }: { data: HomeData["categories"]; onSelect: (id: number) => void }) {
  if (!data.length) return <div className="category-empty"><span className="category-empty-mark"><SlidersHorizontal size={19} /></span><div><strong>الأقسام قيد التجهيز</strong><p>أضف أقسام متجرك لتبدأ ترتيب المنتجات.</p></div><Link href="/categories"><ChevronLeft size={18} /></Link></div>;
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        flexWrap: "nowrap",
        gap: "12px",
        overflowX: "auto",
        overflowY: "hidden",
        padding: "4px 2px 12px",
        scrollSnapType: "x proximity",
        WebkitOverflowScrolling: "touch",
        scrollbarWidth: "none",
      }}
    >
      {data.map(category => {
        const btnColor = category.color && category.color.trim() ? category.color.trim() : "#397a54";
        return (
          <button
            key={category.id}
            type="button"
            onClick={() => onSelect(category.id)}
            style={{
              flex: "0 0 156px",
              width: "156px",
              scrollSnapAlign: "start",
              background: "#ffffff",
              border: "1px solid #e6ece8",
              borderRadius: "18px",
              padding: "5px 5px 9px",
              cursor: "pointer",
              boxShadow: "0 4px 12px rgba(17, 58, 40, 0.05)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <div style={{ width: "100%", height: "134px", borderRadius: "14px", overflow: "hidden", background: "#f4f8f5" }}>
              {category.imageUrl ? (
                <img
                  src={category.imageUrl}
                  alt={category.name}
                  loading="eager"
                  fetchPriority="high"
                  decoding="async"
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                />
              ) : (
                <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", color: btnColor }}>
                  <Leaf size={30} strokeWidth={1.6} />
                </div>
              )}
            </div>
            <span
              style={{
                display: "inline-block",
                maxWidth: "100%",
                padding: "5px 12px",
                borderRadius: "10px",
                backgroundColor: btnColor,
                color: "#ffffff",
                fontSize: "11px",
                fontWeight: 700,
                lineHeight: 1.35,
                textAlign: "center",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {category.name}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function HomePage({ data, onOpen, onAiRecipe }: { data: HomeData; onOpen: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const [, navigate] = useLocation();
  const [sort, setSort] = useState<"featured" | "price-asc" | "price-desc">("featured");
  const { data: products, isLoading: productsLoading } = trpc.commerce.catalog.listProducts.useQuery({ sort, limit: 10000 }, { enabled: sort !== "featured", retry: 1, staleTime: 15000, refetchInterval: false, refetchOnWindowFocus: true });
  const featured = sort === "featured" ? (data.products?.length ? data.products : (products ?? [])) : (products ?? data.products);
  const changeCategory = (id: number) => { navigate("/products?category=" + id); };

  const topBanners = useMemo(() => (data.banners ?? []).filter(b => parseBannerMeta(b.actionUrl).cfg.placement === "top"), [data.banners]);
  const middleBanners = useMemo(() => (data.banners ?? []).filter(b => parseBannerMeta(b.actionUrl).cfg.placement === "middle"), [data.banners]);
  const bottomBanners = useMemo(() => (data.banners ?? []).filter(b => parseBannerMeta(b.actionUrl).cfg.placement === "bottom"), [data.banners]);
  const popupBanners = useMemo(() => (data.banners ?? []).filter(b => parseBannerMeta(b.actionUrl).cfg.placement === "popup"), [data.banners]);

  return <main className="page-shell">
    <PromoPopupModal banners={popupBanners} />
    <BannerCarousel banners={topBanners} />
    {data.offers.length > 0 && <section className="offers-row"><div className="section-heading compact"><div><span className="eyebrow">عروض المتجر</span><h2>فرص تستحق الانتباه</h2></div><BadgePercent size={22} /></div><div className="offer-strip">{data.offers.map(offer => <div className="offer-chip" key={offer.id}><span className="offer-chip-icon"><BadgePercent size={18} /></span><div><strong>{offer.title}</strong><small>{offer.description || (offer.discountType === "percent" ? "خصم " + offer.discountValue + "%" : "خصم " + formatPrice(offer.discountValue))}</small></div><code>{offer.code}</code></div>)}</div></section>}
    <section className="store-section categories-section"><div className="section-heading"><div><h2>الأقسام</h2></div><Link className="text-link" href="/categories">عرض الكل <ArrowLeft size={15} /></Link></div><CategoryStrip data={data.categories} onSelect={changeCategory} /></section>
    {middleBanners.length > 0 && <BannerCarousel banners={middleBanners} />}
    <section className="store-section products-section"><div className="section-heading"><div><h2>منتجات المتجر</h2></div><div className="section-tools"><label className="sort-select"><ArrowUpDown size={15} /><select aria-label="ترتيب المنتجات" value={sort} onChange={event => setSort(event.target.value as typeof sort)}><option value="featured">الأبرز</option><option value="price-asc">السعر: الأقل أولًا</option><option value="price-desc">السعر: الأعلى أولًا</option></select></label><Link className="text-link" href="/products">عرض الكل <ArrowLeft size={15} /></Link></div></div>{productsLoading && !featured.length ? <Loading /> : <ProductGrid items={featured} maxItems={40} totalStoreCount={featured.length} onViewAll={() => navigate("/products")} gridKey={"home:" + sort} onOpen={onOpen} onAiRecipe={onAiRecipe} />}</section>
    {bottomBanners.length > 0 && <BannerCarousel banners={bottomBanners} />}
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
  useEffect(() => setSearch(routeSearch), [routeSearch]);
  const categoryId = selectedCategory ? Number(selectedCategory) : undefined;
  const activeCategory = useMemo(() => data.categories.find(c => c.id === categoryId) ?? null, [data.categories, categoryId]);
  const [offset, setOffset] = useState(0);
  const [loadedProducts, setLoadedProducts] = useState<PublicProduct[]>([]);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const input = {
    search: debouncedSearch || undefined,
    categoryId,
    sort: "featured" as const,
    limit: 40,
    offset,
  };

  const query = trpc.commerce.catalog.listProducts.useQuery(input, {
    retry: 1,
    staleTime: 15000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    setOffset(0);
    setLoadedProducts([]);
  }, [debouncedSearch, categoryId]);

  useEffect(() => {
    if (!query.data) return;

    setLoadedProducts(current => {
      const base = offset === 0 ? [] : current;
      const existing = new Set(base.map(product => product.id));
      const next = query.data.filter(product => !existing.has(product.id));
      return [...base, ...next];
    });
  }, [query.data, offset]);

  const hasMore = (query.data?.length ?? 0) === 40;

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node || !hasMore || query.isFetching || query.isError) return;

    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setOffset(current => current + 40);
      }
    }, { rootMargin: "450px" });

    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, query.isFetching, query.isError, offset]);

  return (
    <main className="page-shell inner-page" style={{ paddingTop: "12px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          padding: "10px 14px",
          borderRadius: "18px",
          background: "#ffffff",
          border: "1.5px solid #dce8df",
          boxShadow: "0 8px 22px rgba(17, 58, 40, 0.06)",
          marginBottom: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "11px" }}>
          {activeCategory?.imageUrl ? (
            <img
              src={activeCategory.imageUrl}
              alt={activeCategory.name}
              style={{ width: "48px", height: "48px", borderRadius: "14px", objectFit: "cover", border: "1.5px solid #174b36", flexShrink: 0 }}
            />
          ) : (
            <span style={{ width: "46px", height: "46px", borderRadius: "14px", background: "#edf6f0", color: "#174b36", display: "grid", placeItems: "center", flexShrink: 0 }}>
              <ShoppingBag size={22} />
            </span>
          )}
          <div>
            <h1 style={{ fontSize: "19px", fontWeight: 800, color: "#123b29", margin: 0, lineHeight: 1.25 }}>
              {activeCategory ? activeCategory.name : (debouncedSearch ? ("نتائج البحث: " + debouncedSearch) : "كل المنتجات")}
            </h1>
            {activeCategory?.description && (
              <small style={{ fontSize: "11.5px", color: "#5c7063", display: "block", marginTop: "2px" }}>{activeCategory.description}</small>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setLocation("/categories")}
          style={{
            padding: "7px 12px",
            borderRadius: "12px",
            border: "1px solid #cfe0d4",
            background: "#f4f9f6",
            color: "#174b36",
            fontSize: "12px",
            fontWeight: 800,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            flexShrink: 0,
          }}
        >
          <span>الأقسام</span>
          <ArrowLeft size={14} />
        </button>
      </div>

      {data.categories.length > 1 && (
        <div
          style={{
            display: "flex",
            gap: "8px",
            overflowX: "auto",
            paddingBottom: "8px",
            marginBottom: "10px",
            scrollbarWidth: "none",
          }}
        >
          <button
            type="button"
            onClick={() => setLocation("/products")}
            style={{
              padding: "6px 13px",
              borderRadius: "99px",
              border: !categoryId ? "1.5px solid #174b36" : "1px solid #d5e3da",
              background: !categoryId ? "#174b36" : "#ffffff",
              color: !categoryId ? "#ffffff" : "#174b36",
              fontSize: "12px",
              fontWeight: 800,
              whiteSpace: "nowrap",
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            الكل
          </button>
          {data.categories.map(cat => {
            const isActive = categoryId === cat.id;
            const catColor = cat.color && cat.color.trim() ? cat.color.trim() : "#397a54";
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setLocation("/products?category=" + cat.id)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 11px 4px 6px",
                  borderRadius: "99px",
                  border: isActive ? ("1.5px solid " + catColor) : "1px solid #d5e3da",
                  background: isActive ? catColor : "#ffffff",
                  color: isActive ? "#ffffff" : "#174b36",
                  fontSize: "12px",
                  fontWeight: 800,
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                {cat.imageUrl && (
                  <img src={cat.imageUrl} alt="" style={{ width: "24px", height: "24px", borderRadius: "50%", objectFit: "cover" }} />
                )}
                <span>{cat.name}</span>
              </button>
            );
          })}
        </div>
      )}

      {query.isLoading && loadedProducts.length === 0 ? (
        <Loading />
      ) : query.error && loadedProducts.length === 0 ? (
        <LoadError onRetry={() => void query.refetch()} />
      ) : (
        <>
          <ProductGrid items={loadedProducts} onOpen={onOpen} onAiRecipe={onAiRecipe} />
          <div ref={sentinelRef} style={{ minHeight: "24px", display: "grid", placeItems: "center", padding: "12px" }}>
            {query.isFetching && loadedProducts.length > 0 && <span style={{ color: "#54715f", fontSize: "13px" }}>جارٍ تحميل المزيد من المنتجات...</span>}
            {query.error && loadedProducts.length > 0 && <button type="button" onClick={() => void query.refetch()} style={{ border: "1px solid #cfe0d4", borderRadius: "10px", padding: "8px 14px", background: "#f4f9f6", color: "#174b36", fontWeight: 700 }}>إعادة المحاولة</button>}
            {!hasMore && loadedProducts.length > 0 && !query.isFetching && <span style={{ color: "#718078", fontSize: "12px" }}>وصلت إلى نهاية المنتجات</span>}
          </div>
        </>
      )}
    </main>
  );
}

function CategoriesPage({ data }: { data: HomeData }) {
  const [, navigate] = useLocation();
  return (
    <main className="page-shell inner-page" style={{ paddingTop: "12px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
        <h1 style={{ fontSize: "21px", fontWeight: 800, color: "#123b29", margin: 0 }}>أقسام المتجر</h1>
        <span style={{ fontSize: "12px", fontWeight: 700, color: "#556b5d", background: "#edf5ef", padding: "4px 10px", borderRadius: "99px" }}>{data.categories.length} أقسام</span>
      </div>
      {!data.categories.length ? (
        <EmptyState icon={SlidersHorizontal} title="لا توجد أقسام بعد" description="سيضيف صاحب المتجر الأقسام المناسبة، وستظهر لك هنا تلقائيًا." action="استكشف المتجر" href="/products" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))", gap: "14px" }}>
          {data.categories.map(category => {
            const btnColor = category.color && category.color.trim() ? category.color.trim() : "#397a54";
            return (
              <button
                key={category.id}
                type="button"
                onClick={() => navigate("/products?category=" + category.id)}
                style={{
                  background: "#ffffff",
                  border: "1px solid #e6ece8",
                  borderRadius: "18px",
                  padding: "8px 8px 11px",
                  cursor: "pointer",
                  boxShadow: "0 4px 14px rgba(15, 52, 35, 0.05)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "9px",
                  width: "100%",
                }}
              >
                <div style={{ width: "100%", height: "174px", borderRadius: "14px", overflow: "hidden", background: "#f4f8f5" }}>
                  {category.imageUrl ? (
                    <img
                      src={category.imageUrl}
                      alt={category.name}
                      loading="eager"
                      decoding="async"
                      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                    />
                  ) : (
                    <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", color: btnColor }}>
                      <Leaf size={40} strokeWidth={1.5} />
                    </div>
                  )}
                </div>
                <span
                  style={{
                    display: "inline-block",
                    maxWidth: "94%",
                    padding: "6px 14px",
                    borderRadius: "10px",
                    backgroundColor: btnColor,
                    color: "#ffffff",
                    fontSize: "12px",
                    fontWeight: 700,
                    lineHeight: 1.35,
                    textAlign: "center",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {category.name}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </main>
  );
}

function ProductDetail({ id, allProducts = [], onSelectProduct, onBack, onAiRecipe }: { id: number; allProducts?: PublicProduct[]; onSelectProduct?: (nextId: number) => void; onBack: () => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const cachedProduct = useMemo(() => allProducts.find(p => p.id === id) ?? null, [allProducts, id]);
  const { data: fetchedProduct, isLoading } = trpc.commerce.catalog.product.useQuery({ id }, {
    retry: 1,
    staleTime: 30000,
    placeholderData: cachedProduct ? { ...cachedProduct, recommendations: allProducts.filter(p => p.id !== id).slice(0, 4) } : undefined,
  });
  const product = fetchedProduct ?? (cachedProduct ? { ...cachedProduct, recommendations: allProducts.filter(p => p.id !== id).slice(0, 4) } : null);
  const { add } = useStore();
  const [quantity, setQuantity] = useState(1);
  const [detailPickerOpen, setDetailPickerOpen] = useState(false);
  const [selectedDetailVariant, setSelectedDetailVariant] = useState<string>('');
  const unpackedDetail = useMemo(() => unpackProductVariants(product?.description), [product?.description]);
  const touchStartX = useRef<number | null>(null);

  useEffect(() => {
    setQuantity(product?.minQuantity || 1);
    setSelectedDetailVariant('');
  }, [id, product?.minQuantity]);

  const galleryList = useMemo(() => (!product ? allProducts : allProducts.some(p => p.id === product.id) ? allProducts : [...allProducts, product as PublicProduct]), [allProducts, product]);
  const currentIndex = useMemo(() => galleryList.findIndex(p => p.id === id), [galleryList, id]);
  const hasGallery = galleryList.length > 1 && currentIndex >= 0;
  const nextProduct = hasGallery ? galleryList[(currentIndex + 1) % galleryList.length] : null;
  const prevProduct = hasGallery ? galleryList[(currentIndex - 1 + galleryList.length) % galleryList.length] : null;

  useEffect(() => {
    if (nextProduct?.imageUrl) { const img = new Image(); img.src = nextProduct.imageUrl; }
    if (prevProduct?.imageUrl) { const img = new Image(); img.src = prevProduct.imageUrl; }
  }, [nextProduct?.imageUrl, prevProduct?.imageUrl]);

  const goNext = () => { if (nextProduct && onSelectProduct) onSelectProduct(nextProduct.id); };
  const goPrev = () => { if (prevProduct && onSelectProduct) onSelectProduct(prevProduct.id); };

  const handleTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    touchStartX.current = e.touches[0]?.clientX ?? null;
  };
  const handleTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    if (touchStartX.current === null || !hasGallery) return;
    const endX = e.changedTouches[0]?.clientX ?? touchStartX.current;
    const diff = endX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(diff) > 35) {
      if (diff > 0) goNext();
      else goPrev();
    }
  };

  if (!product && isLoading) return <main className='page-shell inner-page'><Loading /></main>;
  if (!product) return <main className='page-shell inner-page'><LoadError onRetry={() => window.location.reload()} /></main>;
  const stockLimit = product.stock === null ? 9999 : product.stock;

  const handleDetailAdd = () => {
    if (unpackedDetail.weightEnabled || unpackedDetail.variants.length > 0) {
      if (!unpackedDetail.weightEnabled && selectedDetailVariant) {
        add({ ...product, name: product.name + ' (' + selectedDetailVariant + ')', variant: selectedDetailVariant }, quantity);
        toast.success('تمت إضافة «' + product.name + ' (' + selectedDetailVariant + ')» إلى السلة');
      } else {
        setDetailPickerOpen(true);
      }
      return;
    }
    add(product, quantity);
    toast.success('أُضيف «' + product.name + '» إلى السلة ✓');
  };

  return (
    <main className='page-shell inner-page' style={{ paddingTop: '6px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', gap: '8px' }}>
        <button type='button' className='back-link' style={{ marginBottom: 0, padding: '5px 11px', borderRadius: '10px', background: '#ffffff', border: '1px solid #dce5de', color: '#174b36', fontWeight: 800, fontSize: '12px' }} onClick={onBack}><ArrowLeft size={14} /> العودة للمتجر</button>
        {hasGallery && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#ffffff', border: '1px solid #dfe7e0', borderRadius: '999px', padding: '4px 10px', fontSize: '11px', fontWeight: 800, color: '#174b36' }}>
            <button type='button' onClick={goNext} style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: '2px 5px', fontWeight: 900, color: '#174b36' }}>‹ التالي</button>
            <span style={{ color: '#78847b', fontSize: '10.5px' }} dir='ltr'>{currentIndex + 1} / {galleryList.length}</span>
            <button type='button' onClick={goPrev} style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: '2px 5px', fontWeight: 900, color: '#174b36' }}>السابق ›</button>
          </div>
        )}
      </div>

      <div className='detail-layout' style={{ background: '#ffffff', border: '1px solid #dce6df', borderRadius: '20px', padding: '12px', boxShadow: '0 4px 16px rgba(18, 53, 36, 0.05)', marginBottom: '14px', display: 'grid', gap: '10px' }}>
        <div
          className='detail-visual'
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          style={{ position: 'relative', userSelect: 'none', maxHeight: '215px', borderRadius: '16px', overflow: 'hidden' }}
        >
          {product.imageUrl ? (
            <img key={product.id} src={product.imageUrl} alt={product.name} decoding='async' fetchPriority='high' draggable={false} />
          ) : (
            <div className='product-no-image detail-placeholder'><Leaf size={40} /><span>لا توجد صورة لهذا المنتج</span></div>
          )}
          {hasGallery && (
            <>
              <button type='button' aria-label='المنتج التالي' onClick={e => { e.stopPropagation(); goNext(); }} style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', width: '36px', height: '36px', borderRadius: '50%', border: '1.5px solid rgba(255,255,255,0.9)', background: 'rgba(23, 75, 54, 0.85)', color: '#ffffff', display: 'grid', placeItems: 'center', cursor: 'pointer', fontSize: '18px', fontWeight: 900 }}>‹</button>
              <button type='button' aria-label='المنتج السابق' onClick={e => { e.stopPropagation(); goPrev(); }} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', width: '36px', height: '36px', borderRadius: '50%', border: '1.5px solid rgba(255,255,255,0.9)', background: 'rgba(23, 75, 54, 0.85)', color: '#ffffff', display: 'grid', placeItems: 'center', cursor: 'pointer', fontSize: '18px', fontWeight: 900 }}>›</button>
            </>
          )}
        </div>

        <div className='detail-copy' style={{ display: 'grid', gap: '10px', padding: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ display: 'grid', gap: '2px' }}>
              <h1 style={{ margin: 0, fontSize: '19px', fontWeight: 900, color: '#143a28', lineHeight: 1.25 }}>{product.name}</h1>
              <small style={{ color: '#6b7d72', fontSize: '11.5px', fontWeight: 700 }}>الوحدة: {product.unit} · {product.stock === null ? 'متوفر في المتجر' : ('المتاح: ' + product.stock)}</small>
            </div>
            <div style={{ background: '#f2f8f4', border: '1px solid #d4e6da', padding: '6px 12px', borderRadius: '12px', textAlign: 'left', flexShrink: 0 }}>
              <strong style={{ fontSize: '17px', fontWeight: 900, color: '#174b36' }}>{formatPrice(product.price)}</strong>
              <small style={{ fontSize: '11px', color: '#5b7063', marginRight: '4px' }}>/ {product.unit}</small>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
            <div className='quantity-control' style={{ margin: 0, height: '44px', padding: '0 6px', borderRadius: '13px', flexShrink: 0, background: '#f6faf7', border: '1px solid #d8e6dd' }}>
              <button type='button' aria-label='تقليل' style={{ width: '32px', height: '32px' }} onClick={() => setQuantity(value => Math.max(product.minQuantity || 1, value - (product.quantityStep || 1)))}><Minus size={15} /></button>
              <strong style={{ minWidth: '24px', textAlign: 'center', fontSize: '14.5px' }}>{quantity}</strong>
              <button type='button' aria-label='زيادة' style={{ width: '32px', height: '32px' }} disabled={quantity + (product.quantityStep || 1) > stockLimit} onClick={() => setQuantity(value => Math.min(stockLimit, value + (product.quantityStep || 1)))}><Plus size={15} /></button>
            </div>
            <button
              type='button'
              className='button button-primary'
              disabled={stockLimit < (product.minQuantity || 1)}
              onClick={handleDetailAdd}
              style={{ flex: 1, height: '44px', borderRadius: '13px', fontSize: '14px', fontWeight: 900, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '7px' }}
            >
              <ShoppingCart size={17} />
              <span>{unpackedDetail.variants.length > 0 ? (selectedDetailVariant ? ('أضف «' + selectedDetailVariant + '» للسلة') : 'اختر النوع وأضف للسلة') : 'أضف إلى السلة'}</span>
            </button>
          </div>

          {unpackedDetail.variants.length > 0 && (
            <div style={{ padding: '10px', borderRadius: '13px', background: '#f5f9f6', border: '1px solid #d5e5da', display: 'grid', gap: '7px' }}>
              <strong style={{ fontSize: '12px', color: '#174b36' }}>اختر النوع المطلوب:</strong>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(88px, 1fr))', gap: '6px' }}>
                {unpackedDetail.variants.map(v => {
                  const isSel = selectedDetailVariant === v;
                  return (
                    <button
                      key={v}
                      type='button'
                      onClick={() => setSelectedDetailVariant(v)}
                      style={{
                        padding: '8px 10px',
                        borderRadius: '10px',
                        border: isSel ? '2px solid #174b36' : '1px solid #c5d9cc',
                        background: isSel ? '#174b36' : '#ffffff',
                        color: isSel ? '#ffffff' : '#174b36',
                        fontWeight: 800,
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '4px',
                      }}
                    >
                      {isSel && <Check size={14} />}
                      <span>{v}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {unpackedDetail.cleanDescription ? <p className='detail-description' style={{ margin: 0, fontSize: '12.5px', color: '#5c6f63', lineHeight: 1.5 }}>{unpackedDetail.cleanDescription}</p> : null}

          {onAiRecipe && (
            <button type='button' className='button button-outline full-button' style={{ minHeight: '38px', padding: '7px 12px', borderRadius: '12px', borderColor: '#286a48', color: '#174b36', fontSize: '12px' }} onClick={() => onAiRecipe(product as PublicProduct)}>
              <Sparkles size={15} /> أفكار وطرق تحضير بالذكاء الاصطناعي
            </button>
          )}

          {detailPickerOpen && (unpackedDetail.variants.length > 0 || unpackedDetail.weightEnabled) && (
            <VariantPickerModal product={product as PublicProduct} variants={unpackedDetail.variants} weightEnabled={unpackedDetail.weightEnabled} minWeightAmount={unpackedDetail.minWeightAmount} initialVariant={selectedDetailVariant} initialQty={quantity} onClose={() => setDetailPickerOpen(false)} />
          )}
        </div>
      </div>

      {!!product.recommendations?.length && (
        <section className='store-section'>
          <div className='section-heading'><div><span className='eyebrow'>قد يناسبك أيضًا</span><h2>منتجات مقترحة</h2></div></div>
          <ProductGrid items={product.recommendations as PublicProduct[]} onOpen={nextId => onSelectProduct ? onSelectProduct(nextId) : window.location.assign('/product/' + nextId)} onAiRecipe={onAiRecipe} />
        </section>
      )}
    </main>
  );
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

function getYemenCarrierName(phone: string): string {
  const clean = cleanYemeniPhone(phone);
  if (clean.startsWith("77") || clean.startsWith("78")) return "يمن موبايل";
  if (clean.startsWith("73")) return "YOU";
  if (clean.startsWith("71")) return "سبأفون";
  if (clean.startsWith("70")) return "واي";
  return "";
}

type PublicDeliveryStreet = { id: string; name: string; fee: number; promoFee: number | null; promoLabel: string; freeAbove: number | null; etaText: string; enabled: boolean };
type PublicDeliveryArea = { id: string; name: string; defaultFee: number; enabled: boolean; streets: PublicDeliveryStreet[] };
type PublicDeliveryCity = { id: string; name: string; defaultFee: number; freeDeliveryPromo: boolean; promoBanner: string; enabled: boolean; areas: PublicDeliveryArea[] };
type PublicDeliveryTree = {
  strictSelectionOnly: boolean;
  globalFreeAbove: number | null;
  cities: PublicDeliveryCity[];
  vipFreePhones: Array<{ phone: string; name: string; minOrder: number; enabled: boolean }>;
};

const DEFAULT_PUBLIC_DELIVERY_TREE: PublicDeliveryTree = {
  strictSelectionOnly: true,
  globalFreeAbove: null,
  vipFreePhones: [],
  cities: [
    {
      id: "city_sanaa", name: "صنعاء", defaultFee: 500, freeDeliveryPromo: false, promoBanner: "", enabled: true,
      areas: [
        { id: "area_maeen", name: "معين", defaultFee: 500, enabled: true, streets: [
          { id: "st_raqqas", name: "الرقاص", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_daeri", name: "الدائري", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_hael", name: "شارع هائل", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_sunaina", name: "السنينة", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
          { id: "st_asr", name: "عصر", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
          { id: "st_madhbah", name: "مذبح", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
        ]},
        { id: "area_sabeen", name: "السبعين", defaultFee: 600, enabled: true, streets: [
          { id: "st_haddah", name: "حدة", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 40 دقيقة", enabled: true },
          { id: "st_asbahi", name: "الأصبحي", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
          { id: "st_baitbaws", name: "بيت بوس", fee: 700, promoFee: null, promoLabel: "", freeAbove: null, etaText: "35 - 50 دقيقة", enabled: true },
          { id: "st_maqaleh", name: "شارع المقالح", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
          { id: "st_shumaila", name: "شميلة", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
        ]},
        { id: "area_wahdah", name: "الوحدة", defaultFee: 500, enabled: true, streets: [
          { id: "st_jazaer", name: "شارع الجزائر", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_baghdad", name: "شارع بغداد", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_siyasi", name: "الحي السياسي", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 35 دقيقة", enabled: true },
          { id: "st_tahrir", name: "التحرير", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
        ]},
        { id: "area_shoub", name: "شعوب والثورة", defaultFee: 600, enabled: true, streets: [
          { id: "st_hasaba", name: "الحصبة", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
          { id: "st_juraf", name: "الجراف", fee: 700, promoFee: null, promoLabel: "", freeAbove: null, etaText: "35 - 50 دقيقة", enabled: true },
          { id: "st_sawan", name: "سعوان", fee: 700, promoFee: null, promoLabel: "", freeAbove: null, etaText: "35 - 50 دقيقة", enabled: true },
          { id: "st_sheraton", name: "شيراتون", fee: 600, promoFee: null, promoLabel: "", freeAbove: null, etaText: "30 - 45 دقيقة", enabled: true },
        ]},
      ],
    },
    {
      id: "city_ibb", name: "إب", defaultFee: 500, freeDeliveryPromo: false, promoBanner: "", enabled: true,
      areas: [
        { id: "area_dhihar", name: "الظهار", defaultFee: 500, enabled: true, streets: [
          { id: "st_ibb_taiz", name: "شارع تعز", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
          { id: "st_ibb_daeri", name: "الدائري", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
          { id: "st_ibb_subul", name: "السبل", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
        ]},
        { id: "area_mashanah", name: "المشنة", defaultFee: 500, enabled: true, streets: [
          { id: "st_ibb_odain", name: "شارع العدين", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
          { id: "st_ibb_maayen", name: "المعاين", fee: 500, promoFee: null, promoLabel: "", freeAbove: null, etaText: "25 - 40 دقيقة", enabled: true },
        ]},
      ],
    },
  ],
};

function readPublicDeliveryTree(raw?: string | null): PublicDeliveryTree {
  let source = raw;
  if (!source) {
    try {
      source = (typeof window !== 'undefined' && (window as any).__INITIAL_CATALOG__?.settings?.deliveryTreeConfig)
        || localStorage.getItem('original-admin-delivery-tree-v1')
        || null;
    } catch {}
  }
  if (!source) return DEFAULT_PUBLIC_DELIVERY_TREE;
  try {
    const p = JSON.parse(source);
    if (!p || typeof p !== 'object' || !Array.isArray(p.cities)) return DEFAULT_PUBLIC_DELIVERY_TREE;
    const activeCities = p.cities
      .filter((c: any) => c && c.enabled !== false)
      .map((c: any) => ({
        ...c,
        areas: (Array.isArray(c.areas) ? c.areas : [])
          .filter((a: any) => a && a.enabled !== false)
          .map((a: any) => ({
            ...a,
            streets: (Array.isArray(a.streets) ? a.streets : []).filter((s: any) => s && s.enabled !== false),
          })),
      }));
    if (!activeCities.length) return DEFAULT_PUBLIC_DELIVERY_TREE;
    return {
      strictSelectionOnly: p.strictSelectionOnly !== false,
      globalFreeAbove: p.globalFreeAbove && Number(p.globalFreeAbove) > 0 ? Math.floor(Number(p.globalFreeAbove)) : null,
      cities: activeCities,
      vipFreePhones: Array.isArray(p.vipFreePhones) ? p.vipFreePhones.filter((v: any) => v && v.enabled !== false) : [],
    };
  } catch {
    return DEFAULT_PUBLIC_DELIVERY_TREE;
  }
}

function splitDistrictToAreaAndStreet(district: string): { areaName: string; streetName: string } {
  const parts = String(district || "").split(/\s*[—\-|/]+\s*/).map(s => s.trim()).filter(Boolean);
  if (parts.length >= 2) return { areaName: parts[0], streetName: parts.slice(1).join(" ") };
  return { areaName: "", streetName: parts[0] || "" };
}

function computeLocalDeliveryFee(
  tree: PublicDeliveryTree,
  cityObj: PublicDeliveryCity | null,
  areaObj: PublicDeliveryArea | null,
  streetObj: PublicDeliveryStreet | null,
  phone: string,
  subtotal: number,
): number {
  const cleanP = cleanYemeniPhone(phone);
  const vipMatch = cleanP ? tree.vipFreePhones.find(v => cleanYemeniPhone(v.phone) === cleanP && subtotal >= Number(v.minOrder || 0)) : null;
  if (vipMatch) return 0;
  if (tree.globalFreeAbove && subtotal >= tree.globalFreeAbove) return 0;
  if (cityObj?.freeDeliveryPromo) return 0;
  if (streetObj?.freeAbove && subtotal >= streetObj.freeAbove) return 0;
  if (streetObj && streetObj.promoFee !== null && streetObj.promoFee !== undefined) return streetObj.promoFee;
  if (streetObj) return streetObj.fee;
  if (areaObj) return areaObj.defaultFee;
  return cityObj?.defaultFee ?? 500;
}

function ThreeStepLocationPicker({
  tree,
  city,
  district,
  phone,
  subtotal,
  onChangeLocation,
}: {
  tree: PublicDeliveryTree;
  city: string;
  district: string;
  phone: string;
  subtotal: number;
  onChangeLocation: (nextCity: string, nextDistrict: string) => void;
}) {
  const parsed = splitDistrictToAreaAndStreet(district);
  const committedCity = tree.cities.find(c => c.name === city) ?? null;
  const committedArea = committedCity?.areas.find(a => a.name === parsed.areaName) ?? null;
  const committedStreet = committedArea?.streets.find(s => s.name === parsed.streetName) ?? null;
  const isSelectionComplete = Boolean(committedCity && committedArea && (committedArea.streets.length === 0 || committedStreet));

  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [step, setStep] = useState<"city" | "area" | "street">("city");
  const [draftCity, setDraftCity] = useState<PublicDeliveryCity | null>(committedCity);
  const [draftArea, setDraftArea] = useState<PublicDeliveryArea | null>(committedArea);

  useEffect(() => {
    setDraftCity(committedCity);
    setDraftArea(committedArea);
  }, [city, district, tree]);

  const handleToggleOpen = () => {
    if (isOpen) {
      setIsOpen(false);
      return;
    }
    setDraftCity(committedCity);
    setDraftArea(committedArea);
    setStep("city");
    setIsOpen(true);
  };

  const handleSelectCity = (c: PublicDeliveryCity) => {
    setDraftCity(c);
    setDraftArea(null);
    if (city !== c.name) {
      onChangeLocation("", "");
    }
    if (c.areas.length > 0) {
      setStep("area");
    } else {
      onChangeLocation(c.name, c.name);
      setIsOpen(false);
    }
  };

  const handleSelectArea = (a: PublicDeliveryArea) => {
    if (!draftCity) return;
    setDraftArea(a);
    if (a.streets.length > 0) {
      setStep("street");
    } else {
      onChangeLocation(draftCity.name, a.name);
      setIsOpen(false);
    }
  };

  const handleSelectStreet = (st: PublicDeliveryStreet) => {
    if (!draftCity || !draftArea) return;
    onChangeLocation(draftCity.name, draftArea.name + " — " + st.name);
    setIsOpen(false);
  };

  const effectiveFee = isSelectionComplete
    ? computeLocalDeliveryFee(tree, committedCity, committedArea, committedStreet, phone, subtotal)
    : null;

  const fullAddressLabel = isSelectionComplete
    ? [committedCity?.name, committedArea?.name, committedStreet?.name].filter(Boolean).join(" – ")
    : "";

  return (
    <div style={{ display: "grid", gap: "6px" }}>
      <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#1c3326" }}>عنوان التوصيل</span>

      <button
        type="button"
        onClick={handleToggleOpen}
        style={{
          width: "100%",
          minHeight: isSelectionComplete ? "64px" : "50px",
          padding: "12px 14px",
          borderRadius: "12px",
          border: isOpen ? "1.5px solid #174b36" : "1px solid #d8e1db",
          background: "#ffffff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
          cursor: "pointer",
          textAlign: "right",
          transition: "border-color 0.2s ease, box-shadow 0.2s ease",
          boxShadow: isOpen ? "0 4px 14px rgba(23, 75, 54, 0.08)" : "0 1px 3px rgba(15, 42, 28, 0.03)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", minWidth: 0, flex: 1 }}>
          <span style={{ width: "32px", height: "32px", borderRadius: "9px", background: "#f2f7f4", color: "#174b36", display: "grid", placeItems: "center", flexShrink: 0, marginTop: isSelectionComplete ? "2px" : "0" }}>
            <MapPin size={17} />
          </span>
          {!isSelectionComplete ? (
            <span style={{ fontSize: "13.5px", fontWeight: 700, color: "#2d4537", alignSelf: "center" }}>
              اختر منطقة التوصيل
            </span>
          ) : (
            <div style={{ display: "grid", gap: "3px", minWidth: 0 }}>
              <strong style={{ fontSize: "13.5px", color: "#122b1e", fontWeight: 800, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {fullAddressLabel}
              </strong>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "12px", color: effectiveFee === 0 ? "#174b36" : "#516659", fontWeight: 700 }}>
                  رسوم التوصيل: {effectiveFee === 0 ? "مجاني" : formatPrice(effectiveFee ?? 0)}
                </span>
                {effectiveFee === 0 && (
                  <span style={{ fontSize: "10.5px", fontWeight: 700, padding: "1px 8px", borderRadius: "99px", background: "#eaf4ee", color: "#174b36" }}>
                    توصيل مجاني
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {!isSelectionComplete ? (
          <ChevronDown
            size={18}
            style={{
              color: "#5b7063",
              flexShrink: 0,
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          />
        ) : (
          <span style={{ fontSize: "12px", fontWeight: 700, color: "#174b36", display: "inline-flex", alignItems: "center", gap: "4px", flexShrink: 0 }}>
            {isOpen ? "إغلاق" : "تعديل العنوان ←"}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            padding: "14px",
            borderRadius: "12px",
            background: "#fafcfa",
            border: "1px solid #dce5df",
            display: "grid",
            gap: "12px",
            animation: "fadeIn 0.18s ease-out",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", paddingBottom: "8px", borderBottom: "1px solid #e9efeb", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => setStep("city")}
                style={{
                  border: "none",
                  background: step === "city" ? "#174b36" : "#eef3f0",
                  color: step === "city" ? "#ffffff" : "#2c4537",
                  padding: "4px 10px",
                  borderRadius: "8px",
                  fontSize: "11.5px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {draftCity ? draftCity.name : "المدينة"}
              </button>
              {draftCity && (
                <>
                  <span style={{ color: "#95a59b", fontSize: "11px" }}>/</span>
                  <button
                    type="button"
                    onClick={() => setStep("area")}
                    style={{
                      border: "none",
                      background: step === "area" ? "#174b36" : "#eef3f0",
                      color: step === "area" ? "#ffffff" : "#2c4537",
                      padding: "4px 10px",
                      borderRadius: "8px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {draftArea ? draftArea.name : "المنطقة"}
                  </button>
                </>
              )}
              {draftCity && draftArea && (
                <>
                  <span style={{ color: "#95a59b", fontSize: "11px" }}>/</span>
                  <span
                    style={{
                      background: step === "street" ? "#174b36" : "#eef3f0",
                      color: step === "street" ? "#ffffff" : "#2c4537",
                      padding: "4px 10px",
                      borderRadius: "8px",
                      fontSize: "11.5px",
                      fontWeight: 700,
                    }}
                  >
                    الشارع
                  </span>
                </>
              )}
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              style={{ border: "none", background: "transparent", color: "#687b6f", fontSize: "11.5px", cursor: "pointer", padding: "2px 4px" }}
            >
              إغلاق
            </button>
          </div>

          {step === "city" && (
            <div style={{ display: "grid", gap: "8px" }}>
              <small style={{ fontSize: "11.5px", color: "#586d60", fontWeight: 600 }}>اختر المدينة أو المحافظة:</small>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {tree.cities.map(c => {
                  const isSelected = draftCity?.id === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => handleSelectCity(c)}
                      style={{
                        padding: "9px 18px",
                        borderRadius: "10px",
                        border: isSelected ? "1.5px solid #174b36" : "1px solid #d5e0d9",
                        background: isSelected ? "#174b36" : "#ffffff",
                        color: isSelected ? "#ffffff" : "#1c3326",
                        fontSize: "13px",
                        fontWeight: 700,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {c.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === "area" && draftCity && (
            <div style={{ display: "grid", gap: "8px" }}>
              <small style={{ fontSize: "11.5px", color: "#586d60", fontWeight: 600 }}>اختر المنطقة أو المديرية في {draftCity.name}:</small>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "7px" }}>
                {draftCity.areas.map(a => {
                  const isSelected = draftArea?.id === a.id;
                  return (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => handleSelectArea(a)}
                      style={{
                        padding: "8px 14px",
                        borderRadius: "10px",
                        border: isSelected ? "1.5px solid #174b36" : "1px solid #d5e0d9",
                        background: isSelected ? "#174b36" : "#ffffff",
                        color: isSelected ? "#ffffff" : "#1c3326",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {a.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === "street" && draftCity && draftArea && (
            <div style={{ display: "grid", gap: "8px" }}>
              <small style={{ fontSize: "11.5px", color: "#586d60", fontWeight: 600 }}>اختر الشارع أو الحي في {draftArea.name}:</small>
              <div style={{ display: "grid", gap: "6px", maxHeight: "210px", overflowY: "auto", paddingLeft: "2px" }}>
                {draftArea.streets.map(st => {
                  const isSelected = committedCity?.id === draftCity.id && committedArea?.id === draftArea.id && committedStreet?.id === st.id;
                  const stFee = computeLocalDeliveryFee(tree, draftCity, draftArea, st, phone, subtotal);
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => handleSelectStreet(st)}
                      style={{
                        width: "100%",
                        padding: "10px 12px",
                        borderRadius: "10px",
                        border: isSelected ? "1.5px solid #174b36" : "1px solid #dde6e0",
                        background: isSelected ? "#f0f7f3" : "#ffffff",
                        color: "#1c3326",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "8px",
                        cursor: "pointer",
                        textAlign: "right",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <span style={{ fontSize: "13px", fontWeight: isSelected ? 800 : 600 }}>{st.name}</span>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: stFee === 0 ? "#174b36" : "#5a6f62" }}>
                        {stFee === 0 ? "مجاني" : formatPrice(stFee)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Checkout({ onClose, onSuccess, cart }: { onClose: () => void; onSuccess: () => void; cart: CartLine[] }) {
  const { remove } = useStore();
  const utils = trpc.useUtils();
  const [, navigate] = useLocation();
  const customer = useCustomer();
  const homeCatalog = trpc.commerce.catalog.home.useQuery(undefined, { staleTime: 30000, placeholderData: readLocalInstantCatalog() as any });
  const deliveryTree = useMemo(() => readPublicDeliveryTree((homeCatalog.data?.settings as any)?.deliveryTreeConfig), [homeCatalog.data?.settings]);
  const subtotal = useMemo(() => cart.reduce((s, l) => s + l.price * l.quantity, 0), [cart]);

  const defaultAddress = customer.addresses.find(address => address.isDefault) ?? customer.addresses[0];
  const [selectedAddressId, setSelectedAddressId] = useState(defaultAddress?.id ?? "new");
  const [showExtras, setShowExtras] = useState(false);
  const [form, setForm] = useState(() => ({
    recipientName: defaultAddress?.recipientName ?? customer.name,
    phone: cleanYemeniPhone(defaultAddress?.phone ?? customer.phone),
    city: defaultAddress?.city ?? "",
    district: defaultAddress?.district ?? "",
    addressDetails: defaultAddress?.details ?? "",
    customerNote: "",
    offerCode: "",
  }));
  const items = useMemo(() => cart.map(item => ({ productId: item.id, quantity: item.quantity, name: item.name, ...(item.variant ? { variant: item.variant } : {}), ...(item.customAmount ? { customAmount: item.customAmount } : {}) })), [cart]);
  const signature = JSON.stringify({ form, items });
  const keyRef = useRef<{ signature: string; key: string }>({ signature: "", key: "" });
  if (keyRef.current.signature !== signature) keyRef.current = { signature, key: getPendingOrderIdempotencyKey(signature) };
  const [quoteSignature, setQuoteSignature] = useState("");

  const handleUnavailableOrderError = (rawMsg: string) => {
    let msg = rawMsg || "تعذر إتمام الطلب.";
    if (msg.includes("Failed query:") || msg.includes("data:image/") || msg.length > 260) {
      msg = "تعذر حفظ الطلب مؤقتاً، يرجى الضغط على تأكيد الطلب مرة أخرى.";
    }
    if (msg.includes("لم يعد متوفراً") || msg.includes("لم يعد متاحًا")) {
      const removedIds = new Set<number>();
      const removedNames: string[] = [];
      msg = msg.replace(/منتج\s*#(\d+)/g, (_full, idStr) => {
        const pid = Number(idStr);
        removedIds.add(pid);
        const inCart = cart.find(c => c.id === pid);
        if (inCart && inCart.name) {
          if (!removedNames.includes(inCart.name)) removedNames.push(inCart.name);
          return inCart.name;
        }
        return "منتج #" + pid;
      });
      const m = msg.match(/«([^»]+)»/);
      if (m && m[1]) {
        const parts = m[1].split("،").map(s => s.trim()).filter(Boolean);
        for (const line of cart) {
          if (removedIds.has(line.id) || parts.some(p => line.name === p || line.name.includes(p) || p.includes(line.name))) {
            removedIds.add(line.id);
            if (!removedNames.includes(line.name)) removedNames.push(line.name);
          }
        }
      }
      for (const line of cart) {
        if (removedIds.has(line.id)) {
          remove(line.id, line.variant);
        }
      }
      if (removedNames.length > 0) {
        msg = "المنتج «" + removedNames.join("، ") + "» لم يعد متوفراً حالياً في المتجر. تم حذفه من السلة تلقائياً.";
      }
      toast.error(msg);
      void utils.commerce.catalog.home.invalidate();
      void utils.commerce.catalog.listProducts.invalidate();
      onClose();
      return;
    }
    toast.error(msg);
  };

  const quoteMutation = trpc.commerce.orders.quote.useMutation({ onError: error => handleUnavailableOrderError(error.message || "تعذر حساب ملخص الطلب.") });
  const quote = quoteSignature === signature ? quoteMutation.data : undefined;

  useEffect(() => {
    if (!form.city || !form.district || !items.length) return;
    const timer = setTimeout(() => {
      setQuoteSignature(signature);
      quoteMutation.mutate({ items, city: form.city, district: form.district, phone: cleanYemeniPhone(form.phone), offerCode: form.offerCode || undefined } as any);
    }, 20);
    return () => clearTimeout(timer);
  }, [form.city, form.district, form.phone, form.offerCode, signature]);

  const mutation = trpc.commerce.orders.place.useMutation({
    onSuccess: result => {
      const idempotencyKey = keyRef.current.key;
      customer.rememberOrder({ orderNumber: result.orderNumber, idempotencyKey, createdAt: new Date().toISOString() });
      clearPendingOrderIdempotencyKey(idempotencyKey);
      if (result.duplicate) {
        toast.info("الطلب مسجل مسبقاً برقم " + result.orderNumber + ". راجع «طلباتي».");
        onClose();
        return;
      }
      const cleanPhone = cleanYemeniPhone(form.phone);
      customer.saveProfile(form.recipientName, cleanPhone);
      const matchingAddress = customer.addresses.find(address =>
        address.city === form.city.trim() && address.district === form.district.trim() && address.details === form.addressDetails.trim(),
      );
      if (!matchingAddress) {
        customer.saveAddress({
          label: form.district.split("—").pop()?.trim() || "عنواني",
          recipientName: form.recipientName,
          phone: cleanPhone,
          city: form.city,
          district: form.district,
          details: form.addressDetails,
          isDefault: customer.addresses.length === 0,
        });
      }
      onSuccess();
      void utils.commerce.orders.trackMany.invalidate();
      toast.success("تم استلام طلبك رقم " + result.orderNumber + " بنجاح");
      onClose();
      navigate("/orders?order=" + encodeURIComponent(result.orderNumber) + "&justOrdered=1");
    },
    onError: error => { setQuoteSignature(""); quoteMutation.reset(); handleUnavailableOrderError(error.message || "تعذر إرسال الطلب. راجع البيانات وحاول مجدداً."); },
  });

  const selectAddress = (id: string) => {
    setSelectedAddressId(id);
    if (id === "new") return;
    const address = customer.addresses.find(item => item.id === id);
    if (address) {
      setForm(current => ({
        ...current,
        recipientName: address.recipientName,
        phone: cleanYemeniPhone(address.phone),
        city: address.city,
        district: address.district,
        addressDetails: address.details,
      }));
    }
  };

  const updateField = (field: keyof typeof form, value: string) => {
    const nextVal = field === "phone" ? cleanYemeniPhone(value) : value;
    setForm(current => ({ ...current, [field]: nextVal }));
    if (["recipientName", "phone", "city", "district", "addressDetails"].includes(field)) {
      setSelectedAddressId("new");
    }
  };

  const phoneValid = isValidYemeniPhone(form.phone);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (mutation.isPending || quoteMutation.isPending) return;
    if (form.recipientName.trim().length < 2) {
      toast.error("يرجى إدخال اسم المستلم.");
      return;
    }
    if (!phoneValid) {
      toast.error("يرجى إدخال رقم جوال يمني صحيح مكون من 9 أرقام ويبدأ بـ 77 أو 73 أو 78 أو 71 أو 70.");
      return;
    }
    if (!form.city.trim() || !form.district.trim()) {
      toast.error("يرجى الضغط على حقل عنوان التوصيل واختيار المدينة والمنطقة والشارع.");
      return;
    }
    if (!form.addressDetails.trim()) {
      toast.error("يرجى كتابة أقرب معلم للعنوان.");
      return;
    }
    try {
      const activeQuote = quote ?? await quoteMutation.mutateAsync({ items, city: form.city, district: form.district, phone: cleanYemeniPhone(form.phone), offerCode: form.offerCode || undefined } as any);
      mutation.mutate({
        ...form,
        phone: cleanYemeniPhone(form.phone),
        idempotencyKey: keyRef.current.key,
        expectedTotal: activeQuote.total,
        expectedQuoteHash: activeQuote.quoteHash,
        offerCode: form.offerCode || undefined,
        items,
      });
    } catch {}
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="checkout-modal" role="dialog" aria-modal="true" style={{ maxWidth: "470px", padding: "20px", borderRadius: "18px", background: "#ffffff" }}>
        <div className="modal-heading" style={{ paddingBottom: "12px", borderBottom: "1px solid #ebefec", marginBottom: "14px" }}>
          <div>
            <h2 style={{ fontSize: "17.5px", margin: 0, color: "#122b1e", fontWeight: 800 }}>إتمام الطلب</h2>
            <small style={{ color: "#687b6f", fontSize: "12px" }}>أدخل بيانات الاستلام واختر عنوان التوصيل</small>
          </div>
          <button type="button" className="icon-button" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={e => void submit(e)} className="form-stack" style={{ gap: "14px" }}>
          {customer.addresses.length > 0 && (
            <div style={{ display: "flex", gap: "6px", overflowX: "auto", paddingBottom: "2px" }}>
              {customer.addresses.map(addr => {
                const isSel = selectedAddressId === addr.id;
                return (
                  <button
                    key={addr.id}
                    type="button"
                    onClick={() => selectAddress(addr.id)}
                    style={{
                      flex: "0 0 auto",
                      padding: "6px 12px",
                      borderRadius: "10px",
                      border: isSel ? "1.5px solid #174b36" : "1px solid #dce4de",
                      background: isSel ? "#f0f7f3" : "#ffffff",
                      color: "#1c3326",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {addr.label} ({addr.district.replace("—", "–")})
                  </button>
                );
              })}
            </div>
          )}

          <div className="form-grid" style={{ gap: "10px" }}>
            <label style={{ fontSize: "12.5px", fontWeight: 700, color: "#1c3326" }}>
              <span>الاسم الكامل</span>
              <input required minLength={2} maxLength={160} autoComplete="name" value={form.recipientName} onChange={event => updateField("recipientName", event.target.value)} placeholder="اسم المستلم" />
            </label>
            <label style={{ fontSize: "12.5px", fontWeight: 700, color: "#1c3326" }}>
              <span style={{ display: "flex", justifyContent: "space-between" }}>
                <span>رقم الهاتف</span>
                {form.phone && <small style={{ color: phoneValid ? "#174b36" : "#b43c2f", fontSize: "10.5px" }}>{phoneValid ? getYemenCarrierName(form.phone) : (form.phone.length + "/9")}</small>}
              </span>
              <input
                required
                type="tel"
                inputMode="numeric"
                maxLength={9}
                dir="ltr"
                value={form.phone}
                onChange={event => updateField("phone", event.target.value)}
                placeholder="77XXXXXXX"
                style={{ textAlign: "left", fontWeight: 700, borderColor: form.phone && !phoneValid ? "#d9534f" : undefined }}
              />
            </label>
          </div>

          <ThreeStepLocationPicker
            tree={deliveryTree}
            city={form.city}
            district={form.district}
            phone={form.phone}
            subtotal={subtotal}
            onChangeLocation={(nextCity, nextDist) => {
              setForm(curr => ({ ...curr, city: nextCity, district: nextDist }));
              setSelectedAddressId("new");
            }}
          />

          <label style={{ fontSize: "12.5px", fontWeight: 700, color: "#1c3326" }}>
            <span>أقرب معلم للعنوان</span>
            <input
              required
              maxLength={400}
              autoComplete="street-address"
              value={form.addressDetails}
              onChange={event => updateField("addressDetails", event.target.value)}
              placeholder="مثال: بجوار بنك الكريمي، أمام جامع..."
            />
          </label>

          <div>
            <button
              type="button"
              onClick={() => setShowExtras(v => !v)}
              style={{ background: "none", border: "none", padding: 0, color: "#4e6658", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
            >
              {showExtras ? "إخفاء الملاحظة ورمز الخصم" : "إضافة ملاحظة أو رمز خصم (اختياري)"}
            </button>
            {showExtras && (
              <div className="form-grid" style={{ marginTop: "8px", gap: "8px" }}>
                <label style={{ fontSize: "12px" }}>ملاحظة التوصيل<input maxLength={500} value={form.customerNote} onChange={event => updateField("customerNote", event.target.value)} placeholder="ملاحظة اختيارية..." /></label>
                <label style={{ fontSize: "12px" }}>رمز الخصم<input maxLength={40} value={form.offerCode} onChange={event => updateField("offerCode", event.target.value.toUpperCase())} placeholder="الكود" dir="ltr" /></label>
              </div>
            )}
          </div>

          <section style={{ padding: "14px", borderRadius: "12px", background: "#f8faf8", border: "1px solid #e1e9e3", display: "grid", gap: "7px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12.5px", color: "#4a5e52" }}>
              <span>المجموع الفرعي ({cart.length} أصناف)</span>
              <strong>{formatPrice(quote ? quote.subtotal : subtotal)}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12.5px", color: "#4a5e52" }}>
              <span>رسوم التوصيل</span>
              <strong style={{ color: quote && quote.deliveryFee === 0 ? "#174b36" : "#1c3326" }}>
                {!form.city || !form.district ? "يحدد بعد اختيار العنوان" : quote ? (quote.deliveryFee === 0 ? "مجاني" : formatPrice(quote.deliveryFee)) : "..."}
              </strong>
            </div>
            {quote && quote.discount > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12.5px", color: "#174b36", fontWeight: 700 }}>
                <span>الخصم</span>
                <strong>−{formatPrice(quote.discount)}</strong>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "8px", marginTop: "2px", borderTop: "1px solid #e2eae4" }}>
              <strong style={{ fontSize: "14px", color: "#122b1e" }}>الإجمالي</strong>
              <strong style={{ fontSize: "17px", color: "#174b36", fontWeight: 800 }}>{formatPrice(quote ? quote.total : subtotal)}</strong>
            </div>
          </section>

          <div className="modal-footer" style={{ marginTop: "2px" }}>
            <button type="button" className="button button-quiet" onClick={onClose}>رجوع</button>
            <button type="submit" className="button button-primary" disabled={mutation.isPending} style={{ flex: 1, fontSize: "14px", fontWeight: 800 }}>
              {mutation.isPending ? <LoaderCircle className="spin" size={17} /> : null}
              {mutation.isPending ? "جارٍ إرسال الطلب..." : "تأكيد الطلب"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
function FavoritesPage({ allProducts = [], onOpen, onAiRecipe }: { allProducts?: PublicProduct[]; onOpen?: (id: number) => void; onAiRecipe?: (p: PublicProduct) => void }) {
  const { favoriteIds } = useStore();
  const [, navigate] = useLocation();
  const localFavs = useMemo(() => allProducts.filter(p => favoriteIds.includes(p.id)), [allProducts, favoriteIds]);
  const query = trpc.commerce.catalog.productsForReorder.useQuery({ ids: favoriteIds }, { enabled: favoriteIds.length > 0 && localFavs.length === 0, retry: 1, staleTime: 60_000 });
  const products = localFavs.length > 0 ? localFavs : (query.data ?? []);
  return <main className="page-shell inner-page"><div className="page-title-row"><div><span className="eyebrow">احتفظ بما تحب</span><h1>المفضلة ({products.length})</h1><p>تُحفظ مفضلتك على هذا المتصفح وتفتح فوراً دون انتظار.</p></div><span className="page-title-icon"><Heart size={23} /></span></div>{!favoriteIds.length ? <EmptyState icon={Heart} title="لم تحفظ منتجات بعد" description="اضغط علامة القلب على أي منتج لإضافته هنا." action="تصفح المنتجات" href="/products" /> : (query.isLoading && !products.length) ? <Loading /> : !products.length ? <EmptyState icon={Heart} title="لا توجد منتجات متاحة من مفضلتك الآن" description="قد تكون المنتجات التي حفظتها أُخفيت أو نفدت." action="تصفح المنتجات" href="/products" /> : <ProductGrid items={products as PublicProduct[]} onOpen={id => onOpen ? onOpen(id) : navigate("/product/" + id)} onAiRecipe={onAiRecipe} />}</main>;
}

function OrdersPage() {
  const customer = useCustomer();
  const { add } = useStore();
  const searchStr = useSearch();
  const searchParams = new URLSearchParams(searchStr);
  const focusedOrderNumber = searchParams.get('order');
  const justOrdered = searchParams.get('justOrdered') === '1';
  const [selectedOrderNumber, setSelectedOrderNumber] = useState<string | null>(focusedOrderNumber);
  const [strictFallbackMode, setStrictFallbackMode] = useState(false);

  useEffect(() => {
    if (focusedOrderNumber) setSelectedOrderNumber(focusedOrderNumber);
  }, [focusedOrderNumber]);

  const allRefs = useMemo(() => customer.orders.slice(0, 50).map(({ orderNumber, idempotencyKey }) => ({ orderNumber: String(orderNumber || '').trim(), idempotencyKey: String(idempotencyKey || '').trim() })).filter(r => r.orderNumber && r.idempotencyKey), [customer.orders]);
  const strictRefs = useMemo(() => allRefs.filter(r => /^OR-[A-Z0-9]+-[A-Z0-9]{5}$/i.test(r.orderNumber)), [allRefs]);
  const refs = strictFallbackMode ? strictRefs : allRefs;

  const cleanPhoneForTrack = cleanYemeniPhone(customer.phone || customer.addresses[0]?.phone || '');
  const validPhoneForTrack = isValidYemeniPhone(cleanPhoneForTrack) ? cleanPhoneForTrack : undefined;
  const canTrackOrders = refs.length > 0 || (!strictFallbackMode && Boolean(validPhoneForTrack));

  const cachedOrdersData = useMemo(() => {
    try {
      const raw = localStorage.getItem('original-orders-track-cache-v1');
      const parsed = raw ? JSON.parse(raw) : null;
      return Array.isArray(parsed) && parsed.length > 0 ? parsed : undefined;
    } catch { return undefined; }
  }, [allRefs.length]);

  const queryInput = strictFallbackMode ? { refs: strictRefs } : { refs, ...(validPhoneForTrack ? { phone: validPhoneForTrack } : {}) };
  const query = trpc.commerce.orders.trackMany.useQuery(queryInput as any, { enabled: canTrackOrders, retry: 0, staleTime: 10000, refetchInterval: canTrackOrders ? 10000 : false, initialData: cachedOrdersData as any, placeholderData: cachedOrdersData });

  useEffect(() => {
    if (query.error && !strictFallbackMode) {
      setStrictFallbackMode(true);
    }
  }, [query.error, strictFallbackMode]);

  useEffect(() => {
    if (query.data && Array.isArray(query.data) && query.data.length > 0) {
      try { localStorage.setItem('original-orders-track-cache-v1', JSON.stringify(query.data)); } catch {}
    }
  }, [query.data]);

  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  const subscribe = trpc.commerce.orders.subscribeToStatus.useMutation();
  const [permission, setPermission] = useState(getPushPermissionState);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushPending, setPushPending] = useState(false);
  const [reorder, setReorder] = useState<Array<{ productId: number; quantity: number }> | null>(null);
  const reorderQuery = trpc.commerce.catalog.productsForReorder.useQuery({ ids: reorder?.map(item => item.productId) ?? [1] }, { enabled: Boolean(reorder), retry: 1 });

  useEffect(() => {
    const subRefs = strictFallbackMode ? strictRefs : allRefs;
    if (!subRefs.length || getPushPermissionState() !== 'granted') return;
    let active = true;
    void (async () => {
      try {
        let subscription = await getExistingBrowserPushSubscription();
        if (!subscription) {
          const key = publicKey.data ?? (await publicKey.refetch()).data;
          if (key) subscription = await ensureBrowserPushSubscription(key);
        }
        if (!subscription || !active) return;
        const result = await subscribe.mutateAsync({ refs: subRefs, subscription });
        if (active) setPushEnabled(result.subscribed > 0);
      } catch {}
    })();
    return () => { active = false; };
  }, [allRefs.length, strictFallbackMode]);

  const enableNotifications = async () => {
    if (pushPending) return;
    setPushPending(true);
    try {
      const requestedPermission = await requestPushPermission();
      setPermission(requestedPermission);
      if (requestedPermission === 'unsupported') {
        toast.error('متصفحك لا يدعم إشعارات تتبع الطلبات.');
        return;
      }
      if (requestedPermission !== 'granted') {
        toast.error('يرجى السماح بالإشعارات من إعدادات المتصفح لتتبع طلبك.');
        return;
      }
      const key = publicKey.data ?? (await publicKey.refetch()).data;
      if (!key) {
        toast.error('تعذر الاتصال بخدمة الإشعارات حالياً.');
        return;
      }
      const subscription = await ensureBrowserPushSubscription(key);
      if (allRefs.length > 0) {
        try {
          await subscribe.mutateAsync({ refs: allRefs, subscription });
        } catch {
          if (strictRefs.length > 0) {
            await subscribe.mutateAsync({ refs: strictRefs, subscription }).catch(() => {});
          }
        }
      }
      setPushEnabled(true);
      toast.success('تم تفعيل إشعارات تتبع الطلب بنجاح ✓');
    } catch {
      toast.error('تعذر تفعيل الإشعارات حالياً، يرجى المحاولة بعد قليل.');
    } finally {
      setPushPending(false);
    }
  };

  useEffect(() => {
    if (!reorder || !reorderQuery.data) return;
    let added = 0;
    for (const line of reorder) {
      const product = reorderQuery.data.find(candidate => candidate.id === line.productId);
      if (!product) continue;
      const minimum = product.minQuantity || 1; const step = product.quantityStep || 1;
      let quantity = minimum + Math.max(0, Math.floor((Math.max(minimum, line.quantity) - minimum) / step)) * step;
      if (product.stock !== null) {
        const bounded = Math.min(quantity, product.stock);
        quantity = minimum + Math.max(0, Math.floor((bounded - minimum) / step)) * step;
        if (quantity > product.stock) continue;
      }
      add(product, quantity); added += 1;
    }
    if (added) toast.success('أُضيف ' + added + ' منتج إلى السلة.');
    else toast.error('لا توجد منتجات متاحة من هذا الطلب الآن.');
    setReorder(null);
  }, [reorder, reorderQuery.data, add]);

  const orders = useMemo(() => {
    const raw = [...(query.data ?? cachedOrdersData ?? [])];
    raw.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    return raw;
  }, [query.data, cachedOrdersData]);

  const orderStatusLabels: Record<string, string> = { new: 'جديد', preparing: 'قيد التجهيز', ready: 'جاهز للتوصيل', out_for_delivery: 'خرج للتوصيل', delivered: 'تم التسليم', cancelled: 'ملغي' };
  const stepOrder = ['new', 'preparing', 'ready', 'out_for_delivery', 'delivered'];
  const stepTitles: Record<string, string> = {
    new: 'تم الاستلام',
    preparing: 'قيد التجهيز',
    ready: 'جاهز',
    out_for_delivery: 'خرج للتوصيل',
    delivered: 'تم التسليم',
  };

  const selectedOrder = useMemo(() => {
    if (!selectedOrderNumber) return null;
    return orders.find(o => o.orderNumber === selectedOrderNumber) ?? null;
  }, [orders, selectedOrderNumber]);

  if (selectedOrder) {
    const currentStepIdx = stepOrder.indexOf(selectedOrder.status);
    const ordAny = selectedOrder as any;
    const cancelledNotes = (selectedOrder.events || []).filter((ev: any) => String(ev.note || '').startsWith('❌')).map((ev: any) => String(ev.note || '').replace(/\s*\|\s*الإجمالي الجديد:.*$/, ''));
    const regularNotes = (selectedOrder.events || []).filter((ev: any) => ev.note && ev.note.trim() && ev.note !== 'تم استلام الطلب' && !String(ev.note).startsWith('❌'));
    const latestStoreNote = regularNotes.at(-1);

    return (
      <main className='page-shell inner-page' style={{ paddingTop: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '10px' }}>
          <button type='button' className='back-link' style={{ marginBottom: 0, padding: '7px 14px', borderRadius: '12px', background: '#ffffff', border: '1px solid #dce6df', color: '#174b36', fontWeight: 800, fontSize: '12.5px' }} onClick={() => setSelectedOrderNumber(null)}>
            <ArrowLeft size={15} /> العودة إلى طلباتي
          </button>
        </div>
        <div style={{ marginBottom: '12px' }}>
          <span className='eyebrow'>تفاصيل طلبك</span>
          <h1 style={{ margin: '2px 0 4px', fontSize: '22px', fontWeight: 900, color: '#143a28' }}>طلبك بين يديك</h1>
          <p style={{ margin: 0, fontSize: '12.5px', color: '#6b7d72' }}>كل تفاصيل الفاتورة وحالة التوصيل في مكان واحد.</p>
        </div>

        <article style={{ background: '#ffffff', border: '1px solid #dce6df', borderRadius: '20px', padding: '16px', display: 'grid', gap: '14px', boxShadow: '0 4px 16px rgba(20, 55, 35, 0.04)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px', flexWrap: 'wrap', paddingBottom: '12px', borderBottom: '1px solid #edf3ee' }}>
            <div style={{ display: 'grid', gap: '4px' }}>
              <small style={{ color: '#6b7d72', fontSize: '11px', fontWeight: 700 }}>رقم الطلب</small>
              <strong style={{ fontSize: '16px', color: '#143a28', fontWeight: 900, letterSpacing: '0.5px' }} dir='ltr'>{selectedOrder.orderNumber}</strong>
              <small style={{ color: '#6b7d72', fontSize: '11.5px' }}>{new Date(selectedOrder.createdAt).toLocaleString('ar-YE')}</small>
              <small style={{ color: '#4d6356', fontSize: '12px', fontWeight: 700 }}>{selectedOrder.city} - {selectedOrder.district}</small>
            </div>
            <span className={'status-pill status-' + selectedOrder.status} style={{ fontSize: '12px', fontWeight: 800, padding: '6px 12px' }}>
              {orderStatusLabels[selectedOrder.status] || selectedOrder.status}
            </span>
          </div>

          {selectedOrder.status !== 'cancelled' ? (
            <div style={{ background: '#f5faf7', border: '1px solid #deede3', borderRadius: '16px', padding: '14px 12px', display: 'grid', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: '13px', color: '#174b36', fontWeight: 900 }}>حالة تجهيز وتوصيل الطلب</strong>
                <small style={{ fontSize: '11px', color: '#5c7467', fontWeight: 700 }}>الخطوة {Math.max(1, currentStepIdx + 1)} من 5</small>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: '6px', width: '100%' }}>
                {stepOrder.map((st, sIdx) => {
                  const done = currentStepIdx >= sIdx;
                  const active = currentStepIdx === sIdx;
                  return (
                    <div key={st} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '6px', minWidth: 0 }}>
                      <span style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '50%',
                        background: done ? '#174b36' : '#ffffff',
                        color: done ? '#f1d897' : '#8a998f',
                        border: active ? '2.5px solid #d4a64a' : (done ? '2px solid #174b36' : '1.5px solid #cdd9d1'),
                        display: 'grid',
                        placeItems: 'center',
                        fontSize: '12px',
                        fontWeight: 900,
                        flexShrink: 0,
                      }}>
                        {done ? '✓' : (sIdx + 1)}
                      </span>
                      <span style={{ fontSize: '10.5px', fontWeight: active ? 900 : 700, color: done ? '#143a28' : '#7b8b80', lineHeight: 1.25 }}>
                        {stepTitles[st]}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div style={{ padding: '12px', borderRadius: '14px', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', fontSize: '12.5px', fontWeight: 800 }}>
              تم إلغاء هذا الطلب.
            </div>
          )}

          {latestStoreNote && (
            <div style={{ padding: '11px 13px', borderRadius: '13px', background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', fontSize: '12px' }}>
              <strong style={{ display: 'block', marginBottom: '3px' }}>🔔 رسالة من إدارة المتجر:</strong>
              <span>{latestStoreNote.note}</span>
            </div>
          )}

          {cancelledNotes.length > 0 && (
            <div style={{ padding: '11px 13px', borderRadius: '13px', background: '#fff5f5', border: '1px solid #feb2b2', color: '#9b2c2c', fontSize: '12px', display: 'grid', gap: '4px' }}>
              <strong>تعديلات الفاتورة:</strong>
              {cancelledNotes.map((n: string, i: number) => <div key={i}>{n}</div>)}
            </div>
          )}

          <div style={{ border: '1px solid #e1ece4', borderRadius: '16px', padding: '13px 14px', background: '#ffffff', display: 'grid', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid #eef3f0' }}>
              <strong style={{ fontSize: '13px', color: '#143a28', fontWeight: 900 }}>الأصناف المطلوبة</strong>
              <span style={{ fontSize: '11px', fontWeight: 800, padding: '2px 9px', borderRadius: '99px', background: '#eef5f0', color: '#174b36' }}>
                {selectedOrder.items.length} صنف
              </span>
            </div>
            <div style={{ display: 'grid', gap: '8px' }}>
              {selectedOrder.items.map((item: any, idx: number) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', padding: '8px 10px', borderRadius: '11px', background: '#f8fbf9', fontSize: '12.5px' }}>
                  <strong style={{ color: '#143a28', fontWeight: 800 }}>{item.productName}</strong>
                  <span style={{ color: '#174b36', fontWeight: 900, whiteSpace: 'nowrap' }}>
                    {item.quantity} × {formatPrice(item.unitPrice || Math.round((item.lineTotal || 0) / Math.max(1, item.quantity)))}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: '#f4f8f5', border: '1px solid #dce8df', borderRadius: '16px', padding: '13px 15px', display: 'grid', gap: '6px' }}>
            {typeof ordAny.subtotal === 'number' && ordAny.subtotal > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#5c6f63' }}>
                <span>قيمة المنتجات</span>
                <strong>{formatPrice(ordAny.subtotal)}</strong>
              </div>
            )}
            {typeof ordAny.deliveryFee === 'number' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#5c6f63' }}>
                <span>رسوم التوصيل</span>
                <strong>{ordAny.deliveryFee === 0 ? 'مجاني' : formatPrice(ordAny.deliveryFee)}</strong>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px', borderTop: '1px solid #e1ece4' }}>
              <span style={{ fontSize: '13.5px', fontWeight: 800, color: '#495d51' }}>الإجمالي النهائي</span>
              <strong style={{ fontSize: '19px', fontWeight: 900, color: '#174b36' }}>{formatPrice(selectedOrder.total)}</strong>
            </div>
          </div>

          <button
            type='button'
            className='button button-primary full-button'
            disabled={reorderQuery.isFetching}
            onClick={() => setReorder(selectedOrder.items.filter((item: any): item is typeof item & { productId: number } => typeof item.productId === 'number').map((item: any) => ({ productId: item.productId, quantity: item.quantity })))}
            style={{ height: '46px', borderRadius: '14px', fontSize: '14px', fontWeight: 900 }}
          >
            <ShoppingCart size={17} /> إضافة الطلب إلى السلة مجدداً
          </button>

          {!!selectedOrder.events?.length && (
            <details className='order-history' style={{ marginTop: '4px' }}>
              <summary><span>سجل تحديثات الطلب ({selectedOrder.events.length})</span><ChevronLeft size={14} /></summary>
              <ol>{selectedOrder.events.map((event: any, index: number) => <li key={index}><strong>{orderStatusLabels[event.status] || event.status}</strong><span>{event.note || 'تم تحديث حالة الطلب'}</span><small>{new Date(event.createdAt).toLocaleString('ar-YE')}</small></li>)}</ol>
            </details>
          )}
        </article>
      </main>
    );
  }

  return (
    <main className='page-shell inner-page' style={{ paddingTop: '16px' }}>
      <div className='page-title-row' style={{ marginTop: '4px', marginBottom: '14px' }}>
        <div><span className='eyebrow'>متابعة حية ومباشرة</span><h1 style={{ fontSize: '23px', fontWeight: 900, margin: '4px 0' }}>طلباتي ({orders.length})</h1><p>اضغط على أي طلب لعرض الفاتورة الكاملة وحالة التجهيز والتوصيل.</p></div>
        <span className='page-title-icon'><Package size={22} /></span>
      </div>

      {allRefs.length > 0 && (
        <section style={{ marginBottom: '14px', padding: '12px 14px', borderRadius: '16px', background: pushEnabled ? '#edf7f0' : '#174b36', color: pushEnabled ? '#174b36' : '#ffffff', border: pushEnabled ? '1px solid #b8dec6' : '1px solid #174b36', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1 1 200px' }}>
            <span style={{ width: '36px', height: '36px', borderRadius: '10px', background: pushEnabled ? '#174b36' : '#f1d897', color: pushEnabled ? '#f1d897' : '#113a28', display: 'grid', placeItems: 'center', flexShrink: 0 }}>
              {pushEnabled ? <Check size={18} /> : <BellRing size={18} />}
            </span>
            <div>
              <strong style={{ display: 'block', fontSize: '13px', color: pushEnabled ? '#174b36' : '#f9e8b8' }}>
                {pushEnabled ? 'إشعارات تتبع الطلب مفعّلة ✓' : (justOrdered ? 'تم تأكيد طلبك! فعّل الإشعارات لمتابعته' : 'فعّل إشعارات تتبع حالة طلبك')}
              </strong>
              <small style={{ fontSize: '11px', opacity: 0.9 }}>يصلك تنبيه فوري عند تجهيز طلبك أو خروجه للتوصيل.</small>
            </div>
          </div>
          <button type='button' onClick={() => void enableNotifications()} disabled={pushPending || permission === 'denied' || permission === 'unsupported'} className='small-button' style={{ background: pushEnabled ? '#ffffff' : '#f1d897', color: '#113a28', fontWeight: 800, border: 'none' }}>
            <BellRing size={14} /> {pushPending ? 'جارٍ التفعيل...' : pushEnabled ? 'تحديث' : 'تفعيل الإشعارات'}
          </button>
        </section>
      )}

      {(query.isLoading && !orders.length) ? <Loading /> : !orders.length ? (
        <EmptyState icon={Package} title={allRefs.length ? 'لا توجد طلبات نشطة حالياً' : 'لا توجد طلبات سابقة'} description='بعد إتمام طلب من هذا المتصفح، ستظهر حالته وتفاصيل فاتورته هنا مباشرة.' action='تسوق الآن' href='/products' />
      ) : (
        <div style={{ display: 'grid', gap: '12px' }}>
          {orders.map((order: any, idx: number) => {
            const isLatest = idx === 0;
            return (
              <article
                key={order.orderNumber}
                onClick={() => setSelectedOrderNumber(order.orderNumber)}
                style={{
                  padding: '15px 16px',
                  borderRadius: '18px',
                  background: '#ffffff',
                  border: isLatest ? '2px solid #174b36' : '1px solid #dbe6df',
                  boxShadow: '0 4px 12px rgba(15, 42, 28, 0.04)',
                  display: 'grid',
                  gap: '10px',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'grid', gap: '3px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', flexWrap: 'wrap' }}>
                      <strong style={{ fontSize: '14.5px', color: '#123826', fontWeight: 900 }} dir='ltr'>{order.orderNumber}</strong>
                      {isLatest && <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 8px', borderRadius: '99px', background: '#174b36', color: '#f1d897' }}>أحدث طلب</span>}
                    </div>
                    <small style={{ color: '#6c7d72', fontSize: '11px' }}>{new Date(order.createdAt).toLocaleString('ar-YE')} · {order.city} - {order.district}</small>
                  </div>
                  <span className={'status-pill status-' + order.status} style={{ fontSize: '11.5px', fontWeight: 800 }}>
                    {orderStatusLabels[order.status] || order.status}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '10px', borderTop: '1px solid #edf2ee' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', color: '#5c6f63', fontWeight: 700 }}>{order.items.length} أصناف</span>
                    <strong style={{ fontSize: '16px', color: '#174b36', fontWeight: 900 }}>{formatPrice(order.total)}</strong>
                  </div>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', fontWeight: 800, color: '#174b36', background: '#f0f7f3', padding: '6px 12px', borderRadius: '10px' }}>
                    <span>تفاصيل الطلب</span>
                    <ChevronLeft size={14} />
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}

function useGuestPushSubscriptionSync() {
  const customer = useCustomer();
  const refs = useMemo(() => customer.orders.slice(0, 50).map(({ orderNumber, idempotencyKey }) => ({ orderNumber: String(orderNumber || '').trim(), idempotencyKey: String(idempotencyKey || '').trim() })).filter(r => /^OR-[A-Z0-9]+-[A-Z0-9]{5}$/i.test(r.orderNumber) && r.idempotencyKey), [customer.orders]);
  const subscribe = trpc.commerce.orders.subscribeToStatus.useMutation();
  const publicKey = trpc.commerce.notifications.publicKey.useQuery(undefined, { enabled: false, retry: 1 });
  useEffect(() => {
    if (!refs.length || getPushPermissionState() !== 'granted') return;
    let active = true;
    void (async () => {
      try {
        let subscription = await getExistingBrowserPushSubscription();
        if (!subscription) {
          const key = publicKey.data ?? (await publicKey.refetch()).data;
          if (key) subscription = await ensureBrowserPushSubscription(key);
        }
        if (!subscription || !active) return;
        await subscribe.mutateAsync({ refs, subscription });
      } catch {}
    })();
    return () => { active = false; };
  }, [refs.length]);
}

function AccountPage() {
  const customer = useCustomer();
  const { favoriteIds } = useStore();
  const homeCatalog = trpc.commerce.catalog.home.useQuery(undefined, { staleTime: 30000, placeholderData: readLocalInstantCatalog() as any });
  const deliveryTree = useMemo(() => readPublicDeliveryTree((homeCatalog.data?.settings as any)?.deliveryTreeConfig), [homeCatalog.data?.settings]);
  const cleanedCustomerPhone = cleanYemeniPhone(customer.phone);
  const hasSavedProfile = Boolean(customer.name.trim().length >= 2 && isValidYemeniPhone(cleanedCustomerPhone));
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [accountPanel, setAccountPanel] = useState<"none" | "app_info" | "contact_options" | "contact_why">("none");
  const [name, setName] = useState(customer.name);
  const [phone, setPhone] = useState(cleanedCustomerPhone);

  const [showAddressForm, setShowAddressForm] = useState(false);
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);
  const [address, setAddress] = useState({
    label: 'المنزل',
    recipientName: customer.name,
    phone: cleanedCustomerPhone,
    city: 'صنعاء',
    district: '',
    details: '',
    isDefault: customer.addresses.length === 0,
  });

  useEffect(() => {
    const cp = cleanYemeniPhone(customer.phone);
    setName(customer.name);
    setPhone(cp);
  }, [customer.name, customer.phone]);

  const profilePhoneValid = isValidYemeniPhone(phone);
  const addressPhoneValid = isValidYemeniPhone(address.phone);

  const saveProfile = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length < 2) {
      toast.error('يرجى كتابة الاسم الكامل.');
      return;
    }
    if (!profilePhoneValid) {
      toast.error('يرجى إدخال رقم جوال يمني صحيح مكون من 9 أرقام ويبدأ بـ 77 أو 73 أو 78 أو 71 أو 70.');
      return;
    }
    const cleanP = cleanYemeniPhone(phone);
    customer.saveProfile(name.trim(), cleanP);
    setIsEditingProfile(false);
    toast.success('تم حفظ وتحديث بيانات حسابك بنجاح ✓');
  };

  const resetAddressForm = () => {
    setEditingAddressId(null);
    setShowAddressForm(false);
    setAddress({
      label: 'المنزل',
      recipientName: customer.name || name,
      phone: cleanYemeniPhone(customer.phone || phone),
      city: 'صنعاء',
      district: '',
      details: '',
      isDefault: customer.addresses.length === 0,
    });
  };

  const submitAddress = (event: FormEvent) => {
    event.preventDefault();
    if (!addressPhoneValid) {
      toast.error('يرجى إدخال رقم جوال يمني صحيح مكون من 9 أرقام ويبدأ بـ 77 أو 73 أو 78 أو 71 أو 70.');
      return;
    }
    if (!address.city.trim() || !address.district.trim()) {
      toast.error('يرجى اختيار منطقة التوصيل (المدينة والمنطقة والشارع).');
      return;
    }
    customer.saveAddress({
      ...address,
      phone: cleanYemeniPhone(address.phone),
      id: editingAddressId ?? undefined,
    });
    toast.success(editingAddressId ? 'تم تحديث العنوان المحفوظ بنجاح ✓' : 'تم حفظ العنوان الجديد بنجاح ✓');
    resetAddressForm();
  };

  const displayLetter = (customer.name || name || 'أ').trim().slice(0, 1);
  const carrierName = getYemenCarrierName(cleanedCustomerPhone);

  return (
    <main className='page-shell inner-page original-account-page'>
      <div className='page-title-row' style={{ marginBottom: '4px' }}>
        <div>
          <span className='eyebrow'>ملفك الشخصي وعناوينك</span>
          <h1>حسابي</h1>
          <p>إدارة بيانات الاستلام وعناوين التوصيل المحفوظة لإتمام طلباتك بسرعة وسهولة.</p>
        </div>
        <span className='page-title-icon'><UserRound size={22} /></span>
      </div>

      <section className='original-account-card'>
        <div className='original-account-card-head'>
          <div className='original-account-identity'>
            <span className='original-account-avatar'>{displayLetter}</span>
            <div style={{ display: 'grid', gap: '3px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h2 style={{ margin: 0, fontSize: '17px', color: '#143a28', fontWeight: 900 }}>
                  {customer.name ? customer.name : 'عميل أورجنال'}
                </h2>
                <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 8px', borderRadius: '99px', background: hasSavedProfile ? '#e8f5ee' : '#fef3c7', color: hasSavedProfile ? '#174b36' : '#92400e' }}>
                  {hasSavedProfile ? 'بيانات مكتملة ✓' : 'بانتظار استكمال البيانات'}
                </span>
              </div>
              <small style={{ color: '#6b7d72', fontSize: '11.5px' }}>
                {cleanedCustomerPhone ? ('رقم الجوال: ' + cleanedCustomerPhone) : 'أضف اسمك ورقم جوالك لتعبئة الطلبات تلقائياً'}
              </small>
            </div>
          </div>

          {!isEditingProfile && (
            <button type='button' className='original-account-edit-btn' onClick={() => setIsEditingProfile(true)}>
              <span>تعديل البيانات</span>
            </button>
          )}
        </div>

        {!isEditingProfile ? (
          <div style={{ display: 'grid', gap: '12px' }}>
            <div className='original-account-info-grid'>
              <div className='original-account-info-box'>
                <small>الاسم الكامل للمستلم</small>
                <strong>{customer.name || 'غير مضاف بعد — اضغط تعديل البيانات'}</strong>
              </div>
              <div className='original-account-info-box'>
                <small>رقم الجوال المعتمد للتوصيل</small>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <strong dir='ltr' style={{ letterSpacing: '0.6px' }}>{cleanedCustomerPhone || 'غير مضاف بعد'}</strong>
                  {carrierName && (
                    <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 8px', borderRadius: '99px', background: '#174b36', color: '#ffffff' }}>
                      {carrierName}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className='original-account-shortcuts'>
              <Link href='/orders' className='original-account-shortcut'>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px' }}><Package size={16} /><span>طلباتي السابقة والحالية</span></span>
                <span style={{ padding: '2px 8px', borderRadius: '99px', background: '#eef5f0', fontSize: '11.5px' }}>{customer.orders.length}</span>
              </Link>
              <Link href='/favorites' className='original-account-shortcut'>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '7px' }}><Heart size={16} /><span>منتجاتي المفضلة</span></span>
                <span style={{ padding: '2px 8px', borderRadius: '99px', background: '#eef5f0', fontSize: '11.5px' }}>{favoriteIds.length}</span>
              </Link>
            </div>
            {/* --- ACCOUNT_CONTACT_INFO_START --- */}
<div style={{ display: 'grid', gap: '9px', marginTop: '4px' }}>
  <button type='button' onClick={() => setAccountPanel(curr => curr === 'app_info' ? 'none' : 'app_info')} className='original-account-shortcut' style={{ width: '100%', cursor: 'pointer', padding: '12px 14px', borderRadius: '13px', background: accountPanel === 'app_info' ? '#174b36' : '#f4f9f6', color: accountPanel === 'app_info' ? '#ffffff' : '#143a28', border: '1.5px solid #174b36', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', fontWeight: 900, fontSize: '13px' }}><Leaf size={17} /><span>معلومات التطبيق</span></span>
    <span style={{ fontSize: '11px', fontWeight: 700, opacity: 0.9 }}>نبذة وتعليمات الاستخدام ←</span>
  </button>
  <div onClick={() => setAccountPanel(curr => curr === 'contact_options' ? 'none' : 'contact_options')} role='button' tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setAccountPanel(curr => curr === 'contact_options' ? 'none' : 'contact_options'); }} style={{ width: '100%', cursor: 'pointer', padding: '10px 12px', borderRadius: '13px', background: accountPanel === 'contact_options' ? '#174b36' : '#ffffff', color: accountPanel === 'contact_options' ? '#ffffff' : '#174b36', border: '1.5px solid #cfe2d6', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', boxShadow: '0 3px 10px rgba(23, 75, 54, 0.05)' }}>
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', fontWeight: 900, fontSize: '13px' }}><MessageCircle size={18} /><span>تواصل معنا</span><small style={{ fontSize: '11px', fontWeight: 700, color: accountPanel === 'contact_options' ? '#d9f2e4' : '#5c7265' }}>(مباشر · واتساب · اتصال)</small></div>
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
      <button type='button' title='لماذا تواصل معنا؟' aria-label='معلومات لماذا تواصل معنا' onClick={e => { e.stopPropagation(); setAccountPanel(curr => curr === 'contact_why' ? 'none' : 'contact_why'); }} style={{ width: '32px', height: '32px', borderRadius: '50%', border: '2px solid #e3b341', background: accountPanel === 'contact_why' ? '#e3b341' : '#fff8e1', color: '#7a4f01', fontWeight: 900, fontSize: '16px', display: 'grid', placeItems: 'center', cursor: 'pointer', boxShadow: '0 2px 8px rgba(227, 179, 65, 0.3)', flexShrink: 0 }}>!</button>
    </div>
  </div>
</div>
{accountPanel === 'app_info' && (() => {
  const sName = homeCatalog.data?.settings?.storeName || 'ORIGINAL – أورجنال';
  const infoTxt = String((homeCatalog.data?.settings as any)?.appInfoText || '').trim() || (globalThis as any).DEFAULT_APP_INFO || '';
  const activeCities = deliveryTree.cities.map(c => c.name).join('، ');
  return (
    <div style={{ padding: '15px', borderRadius: '15px', background: '#f6faf7', border: '1.5px solid #174b36', display: 'grid', gap: '10px', marginTop: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><strong style={{ fontSize: '14px', color: '#143a28', fontWeight: 900 }}>🌿 معلومات تطبيق {sName} وتعليمات الاستخدام</strong><button type='button' className='icon-button' style={{ width: '28px', height: '28px' }} onClick={() => setAccountPanel('none')}><X size={15} /></button></div>
      <div style={{ whiteSpace: 'pre-line', fontSize: '12.5px', color: '#1f3a2c', lineHeight: 1.85, background: '#ffffff', padding: '12px 14px', borderRadius: '12px', border: '1px solid #dce8df', fontWeight: 600 }}>{infoTxt}</div>
      <div style={{ display: 'grid', gap: '6px', fontSize: '11.5px', color: '#355242' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', background: '#ffffff', padding: '8px 10px', borderRadius: '10px', border: '1px solid #e1ece4' }}><MapPin size={15} color='#174b36' /><span><strong>مدن التوصيل المعتمدة:</strong> {activeCities || 'صنعاء'}</span></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', background: '#ffffff', padding: '8px 10px', borderRadius: '10px', border: '1px solid #e1ece4' }}><ShieldCheck size={15} color='#174b36' /><span><strong>هدفنا:</strong> توصيل مقاضيك الطازجة لباب بيتك بأعلى جودة والدفع نقداً عند الاستلام.</span></div>
      </div>
    </div>
  );
})()}
{accountPanel === 'contact_options' && (() => {
  const rawStorePhone = String(homeCatalog.data?.settings?.contactPhone || '770000000').trim();
  const digitsOnly = rawStorePhone.replace(/\D+/g, '');
  const waPhone = digitsOnly ? (digitsOnly.startsWith('967') ? digitsOnly : '967' + digitsOnly.replace(/^0+/, '')) : '';
  const waLink = waPhone ? (['ht', 'tps://wa.me/'].join('') + waPhone) : '';
  return (
    <div style={{ padding: '15px', borderRadius: '15px', background: '#f6faf7', border: '1.5px solid #174b36', display: 'grid', gap: '10px', marginTop: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><strong style={{ fontSize: '14px', color: '#143a28', fontWeight: 900 }}>📞 خيارات التواصل مع المتجر</strong><button type='button' className='icon-button' style={{ width: '28px', height: '28px' }} onClick={() => setAccountPanel('none')}><X size={15} /></button></div>
      <div style={{ display: 'grid', gap: '8px' }}>
        <Link href='/assistant' className='original-account-shortcut' style={{ background: '#ffffff', borderColor: '#174b36', padding: '12px 14px' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', fontWeight: 900, color: '#174b36' }}><Bot size={18} /><span>التواصل المباشر (محادثة إدارة المتجر داخل التطبيق)</span></span><ArrowLeft size={16} /></Link>
        {waLink && (<a href={waLink} target='_blank' rel='noreferrer' className='original-account-shortcut' style={{ background: '#eef8f2', borderColor: '#25d366', color: '#0f5132', padding: '12px 14px' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', fontWeight: 900 }}><MessageCircle size={18} /><span>تواصل واتساب</span></span><span style={{ fontSize: '11.5px', fontWeight: 800 }}>فتح واتساب ←</span></a>)}
        <a href={'tel:' + rawStorePhone} className='original-account-shortcut' style={{ background: '#ffffff', borderColor: '#bfd6c8', padding: '12px 14px' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', fontWeight: 900, color: '#143a28' }}><Truck size={18} /><span>الاتصال بالمتجر</span></span><strong dir='ltr' style={{ fontSize: '13px', color: '#174b36' }}>{rawStorePhone}</strong></a>
      </div>
    </div>
  );
})()}
{accountPanel === 'contact_why' && (() => {
  const whyTxt = String((homeCatalog.data?.settings as any)?.contactWhyText || '').trim() || (globalThis as any).DEFAULT_CONTACT_WHY || '';
  return (
    <div style={{ padding: '15px', borderRadius: '15px', background: '#fffdf6', border: '2px solid #e3b341', display: 'grid', gap: '10px', marginTop: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><strong style={{ fontSize: '14px', color: '#7a4f01', fontWeight: 900, display: 'inline-flex', alignItems: 'center', gap: '7px' }}><span style={{ width: '24px', height: '24px', borderRadius: '50%', background: '#e3b341', color: '#ffffff', display: 'grid', placeItems: 'center', fontSize: '14px', fontWeight: 900 }}>!</span><span>لماذا تواصل معنا؟</span></strong><button type='button' className='icon-button' style={{ width: '28px', height: '28px' }} onClick={() => setAccountPanel('none')}><X size={15} /></button></div>
      <div style={{ whiteSpace: 'pre-line', fontSize: '12.5px', color: '#2b3a30', lineHeight: 1.85, background: '#ffffff', padding: '12px 14px', borderRadius: '12px', border: '1px solid #f0dfa8', fontWeight: 600 }}>{whyTxt}</div>
      <button type='button' className='button button-primary' style={{ minHeight: '38px', fontSize: '12.5px' }} onClick={() => setAccountPanel('contact_options')}><span>انتقل إلى خيارات التواصل الآن</span><ArrowLeft size={15} /></button>
    </div>
  );
})()}
{/* --- ACCOUNT_CONTACT_INFO_END --- */}
                      </div>
        ) : (
          <form className='form-stack' onSubmit={saveProfile} style={{ gap: '12px', background: '#f8fbf9', padding: '14px', borderRadius: '14px', border: '1px solid #dce8df' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '13.5px', color: '#174b36' }}>تحديث البيانات الشخصية</strong>
              <small style={{ fontSize: '11px', color: '#64766b' }}>تُحفظ تلقائياً للطلبات القادمة</small>
            </div>
            <div className='form-grid' style={{ gap: '10px' }}>
              <label style={{ fontWeight: 800, fontSize: '12px', color: '#1a3a29' }}>
                <span>الاسم الكامل *</span>
                <input required minLength={2} maxLength={160} autoComplete='name' value={name} onChange={event => setName(event.target.value)} placeholder='اكتب اسمك الكامل هنا...' style={{ background: '#ffffff', fontWeight: 700 }} />
              </label>
              <label style={{ fontWeight: 800, fontSize: '12px', color: '#1a3a29' }}>
                <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>رقم الجوال اليمني (9 أرقام) *</span>
                  <small style={{ fontSize: '10px', fontWeight: 800, color: profilePhoneValid ? '#174b36' : '#b43c2f' }}>
                    {profilePhoneValid ? ('✓ ' + getYemenCarrierName(phone)) : ('77 / 73 / 78 / 71 / 70 (' + phone.length + '/9)')}
                  </small>
                </span>
                <input required type='tel' inputMode='numeric' maxLength={9} dir='ltr' value={phone} onChange={event => setPhone(cleanYemeniPhone(event.target.value))} placeholder='77XXXXXXX' style={{ background: '#ffffff', textAlign: 'left', fontWeight: 800, fontSize: '14.5px', letterSpacing: '0.6px', borderColor: phone && !profilePhoneValid ? '#d9534f' : undefined }} />
              </label>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <button type='button' className='button button-quiet' onClick={() => { setName(customer.name); setPhone(cleanedCustomerPhone); setIsEditingProfile(false); }}>إلغاء</button>
              <button type='submit' className='button button-primary' disabled={name.trim().length < 2 || !profilePhoneValid} style={{ minWidth: '150px' }}><Check size={15} /> حفظ البيانات</button>
            </div>
          </form>
        )}
      </section>

      <section className='original-account-card'>
        <div className='original-account-card-head'>
          <div className='original-account-identity'>
            <span style={{ width: '40px', height: '40px', borderRadius: '12px', background: '#edf6f0', color: '#174b36', display: 'grid', placeItems: 'center', flexShrink: 0 }}><MapPin size={19} /></span>
            <div>
              <h2 style={{ margin: 0, fontSize: '16px', color: '#143a28', fontWeight: 900 }}>عناوين التوصيل المحفوظة ({customer.addresses.length})</h2>
              <small style={{ color: '#6b7d72', fontSize: '11.5px' }}>اختر أي عنوان محفوظ بنقرة واحدة عند تأكيد الطلب</small>
            </div>
          </div>
          {!showAddressForm && (
            <button type='button' className='original-account-edit-btn' onClick={() => { setEditingAddressId(null); setAddress({ label: 'المنزل', recipientName: customer.name || name, phone: cleanedCustomerPhone || phone, city: 'صنعاء', district: '', details: '', isDefault: customer.addresses.length === 0 }); setShowAddressForm(true); }}>
              <Plus size={14} /><span>إضافة عنوان</span>
            </button>
          )}
        </div>

        {!customer.addresses.length && !showAddressForm ? (
          <div style={{ textAlign: 'center', padding: '20px 14px', borderRadius: '14px', background: '#f8fbf9', border: '1px dashed #cbdcd0', display: 'grid', gap: '8px', justifyItems: 'center' }}>
            <MapPin size={24} color='#5d7567' />
            <div style={{ fontSize: '12.5px', color: '#4c6255', fontWeight: 700 }}>لا توجد عناوين محفوظة حتى الآن</div>
            <button type='button' className='original-account-edit-btn' onClick={() => setShowAddressForm(true)}>+ إضافة أول عنوان توصيل</button>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '10px' }}>
            {customer.addresses.map(item => (
              <div key={item.id} style={{ padding: '12px 14px', borderRadius: '14px', background: item.isDefault ? '#f4f9f6' : '#ffffff', border: item.isDefault ? '1.5px solid #174b36' : '1px solid #dde8e0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'grid', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '7px', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '14px', color: '#143a28', fontWeight: 900 }}>{item.label}</strong>
                    {item.isDefault && <span style={{ fontSize: '9.5px', fontWeight: 800, padding: '2px 7px', borderRadius: '99px', background: '#174b36', color: '#ffffff' }}>الافتراضي ✓</span>}
                  </div>
                  <div style={{ fontSize: '12px', color: '#2b4737', fontWeight: 700 }}>{item.recipientName} · <span dir='ltr' style={{ color: '#174b36', fontWeight: 800 }}>{cleanYemeniPhone(item.phone)}</span></div>
                  <div style={{ fontSize: '11.5px', color: '#5b6f62' }}>{item.city} – {item.district.replace('—', '–')}{item.details ? (' · ' + item.details) : ''}</div>
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {!item.isDefault && <button type='button' className='small-button' onClick={() => { customer.setDefaultAddress(item.id); toast.success('تم تعيينه كعنوان افتراضي ✓'); }}>تعيين كافتراضي</button>}
                  <button type='button' className='small-button' onClick={() => { setEditingAddressId(item.id); setAddress({ label: item.label, recipientName: item.recipientName, phone: cleanYemeniPhone(item.phone), city: item.city, district: item.district, details: item.details, isDefault: item.isDefault }); setShowAddressForm(true); }}>تعديل</button>
                  <button type='button' className='icon-button' aria-label='حذف العنوان' onClick={() => { customer.removeAddress(item.id); toast.success('تم حذف العنوان المحفوظ.'); if (editingAddressId === item.id) resetAddressForm(); }}><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showAddressForm && (
          <form className='form-stack' onSubmit={submitAddress} style={{ marginTop: '6px', padding: '14px', borderRadius: '14px', background: '#f8fbf9', border: '1px solid #dce8df', gap: '10px' }}>
            <strong style={{ fontSize: '13.5px', color: '#174b36' }}>{editingAddressId ? 'تعديل العنوان المحفوظ' : 'إضافة عنوان توصيل جديد'}</strong>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {['المنزل', 'العمل', 'منزل العائلة', 'استراحة'].map(preset => (
                <button key={preset} type='button' className={'small-button' + (address.label === preset ? ' selected' : '')} style={{ minHeight: '28px', padding: '3px 10px', fontSize: '11.5px' }} onClick={() => setAddress({ ...address, label: preset })}>{preset}</button>
              ))}
            </div>
            <div className='form-grid' style={{ gap: '10px' }}>
              <label>تسمية العنوان *<input required maxLength={80} value={address.label} onChange={event => setAddress({ ...address, label: event.target.value })} placeholder='المنزل، العمل...' style={{ background: '#ffffff' }} /></label>
              <label>اسم المستلم *<input required minLength={2} maxLength={160} autoComplete='name' value={address.recipientName} onChange={event => setAddress({ ...address, recipientName: event.target.value })} style={{ background: '#ffffff' }} /></label>
              <label>
                <span style={{ display: 'flex', justifyContent: 'space-between' }}><span>رقم الجوال اليمني (9 أرقام) *</span><small style={{ fontSize: '10px', fontWeight: 800, color: addressPhoneValid ? '#174b36' : '#b43c2f' }}>{address.phone.length}/9</small></span>
                <input required type='tel' inputMode='numeric' maxLength={9} dir='ltr' value={address.phone} onChange={event => setAddress({ ...address, phone: cleanYemeniPhone(event.target.value) })} placeholder='77XXXXXXX' style={{ background: '#ffffff', textAlign: 'left', fontWeight: 800 }} />
              </label>
            </div>
            <ThreeStepLocationPicker tree={deliveryTree} city={address.city} district={address.district} phone={address.phone} subtotal={0} onChangeLocation={(nextCity, nextDist) => setAddress(curr => ({ ...curr, city: nextCity, district: nextDist }))} />
            <label>أقرب معلم للعنوان *<input required maxLength={300} value={address.details} onChange={event => setAddress({ ...address, details: event.target.value })} placeholder='مثال: بجوار جامع...، أمام صيدلية...' style={{ background: '#ffffff' }} /></label>
            <label className='checkbox-row'><input type='checkbox' checked={address.isDefault} onChange={event => setAddress({ ...address, isDefault: event.target.checked })} /><span>تعيين كعنوان افتراضي للطلبات القادمة</span></label>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button type='button' className='button button-quiet' onClick={resetAddressForm}>إلغاء</button>
              <button type='submit' className='button button-primary' disabled={!addressPhoneValid || !address.city || !address.district}><Check size={15} /> {editingAddressId ? 'تحديث العنوان' : 'حفظ العنوان'}</button>
            </div>
          </form>
        )}
      </section>
    </main>
  );
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
  ownerMsgId?: string;
};

const ASSISTANT_HISTORY_KEY = "original-assistant-history-v5";
const CHAT_SESSION_KEY = "original-chat-session-id-v4";
const SEEN_OWNER_IDS_KEY = "original-seen-owner-ids-v4";

function readSeenOwnerIds(): Set<string> {
  try {
    const raw = JSON.parse(localStorage.getItem(SEEN_OWNER_IDS_KEY) ?? "[]");
    return new Set(Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string") : []);
  } catch {
    return new Set();
  }
}

function saveSeenOwnerIds(ids: Set<string>) {
  try {
    localStorage.setItem(SEEN_OWNER_IDS_KEY, JSON.stringify([...ids].slice(-200)));
  } catch {}
}

function getOrCreateChatSessionId(): string {
  try {
    let sid = localStorage.getItem(CHAT_SESSION_KEY);
    if (!sid) {
      sid = "chat-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(CHAT_SESSION_KEY, sid);
    }
    return sid;
  } catch {
    return "chat-guest";
  }
}

const assistantGreeting: AssistantMessage = {
  role: "assistant",
  text: "يا هلا بك في أورجنال! 🌿 حياك الله، إيش تحب أجهز لك اليوم؟\nتريد مقاضي الصباح، ولا سلة خضروات ومقاضي للمطبخ والبيت، ولا أقترح لك وصفة طبخة اقتصادية سريعة؟",
  suggestedQuestions: [
    "🌅 مقاضي الصباح والفطور",
    "🍅 سلة المطبخ اليومية",
    "📦 مقاضي البيت والأسبوع",
    "🍳 وصفة طبخة اقتصادية",
  ],
};

function readAssistantHistory(): AssistantMessage[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(ASSISTANT_HISTORY_KEY) ?? "null");
    if (!Array.isArray(saved)) return [assistantGreeting];
    const history = saved.flatMap(item => {
      if (!item || typeof item !== "object") return [];
      const row = item as Record<string, unknown>;
      if ((row.role !== "user" && row.role !== "assistant") || typeof row.text !== "string") return [];
      const cleanText = row.text.replace(/^(?:👨‍💼\s*)?إدارة المتجر\s*:\s*/i, "").slice(0, 1800);
      return [{
        role: row.role,
        text: cleanText,
        ...(typeof row.contextText === "string" ? { contextText: row.contextText.slice(0, 1800) } : {}),
        ...(typeof row.ownerMsgId === "string" ? { ownerMsgId: row.ownerMsgId } : {}),
        ...(row.cartAction && typeof row.cartAction === "object" ? { cartAction: row.cartAction as AssistantCartAction } : {}),
        ...(Array.isArray(row.suggestedQuestions) ? { suggestedQuestions: row.suggestedQuestions.filter((x): x is string => typeof x === "string") } : {}),
      } as AssistantMessage];
    }).slice(-32);
    return history.length ? history : [assistantGreeting];
  } catch { return [assistantGreeting]; }
}

function assistantHistoryText(message: AssistantMessage) {
  return [message.text, message.contextText].filter(Boolean).join("\n").slice(0, 1800);
}

function buildSmartPresetReply(
  query: string,
  catalog: PublicProduct[],
  categories: HomeData["categories"],
  turnIndex: number,
): { text: string; items: PublicProduct[]; suggestions: string[] } | null {
  if (!catalog.length) return null;
  const norm = (s: string) => s.replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").toLowerCase().trim();
  const q = norm(query);
  const findByKeywords = (kws: string[]) => catalog.filter(p => {
    const np = norm(p.name);
    return kws.some(k => np.includes(norm(k)));
  });
  const pickOne = (kws: string[], offset = 0): PublicProduct | null => {
    const matches = findByKeywords(kws);
    if (!matches.length) return null;
    return matches[(turnIndex + offset) % matches.length];
  };
  const uniqueProducts = (arr: Array<PublicProduct | null | undefined>) => {
    const seen = new Set<number>();
    const out: PublicProduct[] = [];
    for (const item of arr) {
      if (item && !seen.has(item.id)) {
        seen.add(item.id);
        out.push(item);
      }
    }
    return out;
  };

  if (/(?:مقاضي الصباح|سله الصباح|تشكيله صباحيه|فطور|صباح)/.test(q)) {
    const variant = turnIndex % 3;
    let items: PublicProduct[] = [];
    let desc = "";
    if (variant === 0) {
      items = uniqueProducts([pickOne(["فول"]), pickOne(["طماطم"]), pickOne(["خيار"]), pickOne(["نعنع", "جرجير", "كبزر"], 1), pickOne(["قشطه", "زبادي", "جبن"])]);
      desc = "صباح الخيرات! 🌅 رتبت لك «سلة الصباح والفطور» (فول وخضار صباحية طازجة مع القشطة/الألبان) 👇";
    } else if (variant === 1) {
      items = uniqueProducts([pickOne(["قشطه", "زبادي"]), pickOne(["خيار"]), pickOne(["طماطم"]), pickOne(["جرجير", "خس", "نعنع"], 2), pickOne(["ليمون"])]);
      desc = "أحلى صباح يا غالي! 🌅 هذي «سلة فطور صباحي خفيف ومنعش» بخضروات الصباح الطازجة والألبان 👇";
    } else {
      items = uniqueProducts([pickOne(["طماطم"]), pickOne(["بصل"]), pickOne(["بسباس"]), pickOne(["كبزر", "بقدونس"]), pickOne(["فول", "تونه"])]);
      desc = "يا صباح النشاط! 🌅 جهزت لك «مقاضي كشنة وفطور الصباح اليمني» طازجة واقتصادية 👇";
    }
    if (items.length >= 2) {
      return {
        text: desc + "\nاعتمد السلة كاملة أو أضف أي صنف بمفرده، أو اضغط «🌅 تشكيلة صباحية أخرى»!",
        items,
        suggestions: ["🌅 تشكيلة صباحية أخرى", "🍅 سلة المطبخ اليومية", "🍳 وصفة طبخة اقتصادية", "عرض السلة"],
      };
    }
  }

  if (/(?:سله المطبخ|مقاضي المطبخ|تشكيله مطبخ|سله خضروات|سله يوميه|خضروات يوميه)/.test(q)) {
    const variant = turnIndex % 3;
    const extraVeg = variant === 0 ? ["كوسه", "باميه"] : variant === 1 ? ["باذنجان", "جزر"] : ["باميه", "ملوخيه", "فجل"];
    const items = uniqueProducts([
      pickOne(["طماطم"]),
      pickOne(["بطاط"]),
      pickOne(["بصل ابيض", "بصل"], variant),
      pickOne(extraVeg, variant),
      pickOne(["بسباس", "ثوم", "كبزر"], variant),
      pickOne(["ليمون", "خيار"], variant),
    ]).slice(0, 5);
    if (items.length >= 2) {
      return {
        text: "أبشر يا غالي! 🍅 رتبت لك «سلة المطبخ والخضروات اليومية» بأهم أساسيات الطبخ الطازجة 👇\nاعتمدها كاملة أو اختر الصنف اللي ناقصك، أو جرب تشكيلة ثانية!",
        items,
        suggestions: ["🍅 تشكيلة مطبخ أخرى", "📦 مقاضي البيت والأسبوع", "🥗 سلة سلطة وورقيات", "🍳 وصفة طبخة اقتصادية"],
      };
    }
  }

  if (/(?:سله سلطه|ورقيات|سلطه خضراء)/.test(q)) {
    const items = uniqueProducts([
      pickOne(["خيار"]),
      pickOne(["طماطم"]),
      pickOne(["ليمون"]),
      pickOne(["خس", "جرجير", "ملفوف"], turnIndex),
      pickOne(["كبزر", "بقدونس", "نعنع", "فجل"], turnIndex + 1),
    ]).slice(0, 5);
    if (items.length >= 2) {
      return {
        text: "يا هلا! 🥗 هذي «سلة السلطة والورقيات الطازجة» لوجبة صحية تفتح النفس 👇",
        items,
        suggestions: ["🌅 مقاضي الصباح والفطور", "🍅 سلة المطبخ اليومية", "🍳 وصفة طبخة اقتصادية", "عرض السلة"],
      };
    }
  }

  if (/(?:مقاضي البيت|مقاضي الاسبوع|تشكيله اسبوعيه|سله الاسبوع|سله اقتصاديه)/.test(q)) {
    const items = uniqueProducts([
      pickOne(["بطاط"]),
      pickOne(["طماطم"]),
      pickOne(["بصل ابيض", "بصل احمر"], turnIndex),
      pickOne(["ثوم"]),
      pickOne(["كوسه", "جزر", "باذنجان", "باميه"], turnIndex),
      pickOne(["فول", "تونه", "قشطه", "زبادي"], turnIndex),
    ]).slice(0, 6);
    if (items.length >= 2) {
      return {
        text: "على عيني! 📦 رتبت لك «سلة مقاضي البيت والأسبوع الاقتصادية» تجمع أساسيات الخضار والمؤونة بسعر ممتاز 👇",
        items,
        suggestions: ["📦 تشكيلة أسبوعية أخرى", "🌅 مقاضي الصباح والفطور", "🍅 سلة المطبخ اليومية", "عرض السلة"],
      };
    }
  }

  if (/^(?:🍳\s*)?(?:وصفه طبخه اقتصاديه|وصفه اقتصاديه|اقترح لي طبخه او وصفه اليوم|وصفه ثانيه|طبخه ثانيه|وصفه خضروات)$/.test(q)) {
    const recipeIdx = turnIndex % 4;
    if (recipeIdx === 0) {
      const items = uniqueProducts([pickOne(["بطاط"]), pickOne(["طماطم"]), pickOne(["بصل"]), pickOne(["ثوم"]), pickOne(["بسباس", "كبزر"])]);
      return {
        text: "🍲 طبخة مقترحة: «صينية بطاط يمنية بالخضار والثوم البلدي»\n👩‍🍳 قطّع البطاط والطماطم والبصل حلقات، وتبّلها بالثوم والبسباس الأخضر واطبخها على نار هادئة 20 دقيقة 👇",
        items,
        suggestions: ["🍳 وصفة ثانية", "🍅 سلة المطبخ اليومية", "🌅 مقاضي الصباح والفطور", "عرض السلة"],
      };
    }
    if (recipeIdx === 1) {
      const items = uniqueProducts([pickOne(["فول"]), pickOne(["طماطم"]), pickOne(["بصل"]), pickOne(["بسباس"]), pickOne(["كبزر"])]);
      return {
        text: "🍲 طبخة مقترحة: «قلابة فول يمني بالخلطة الطازجة»\n👩‍🍳 احمس البصل والطماطم والبسباس الأخضر، ثم أضف الفول ورشة كبزرة طازجة على الوجه في 5 دقائق 👇",
        items,
        suggestions: ["🍳 وصفة ثانية", "🌅 مقاضي الصباح والفطور", "🥗 سلة سلطة وورقيات", "عرض السلة"],
      };
    }
    if (recipeIdx === 2) {
      const items = uniqueProducts([pickOne(["كوسه"]), pickOne(["باذنجان", "باميه"]), pickOne(["بطاط"]), pickOne(["طماطم"]), pickOne(["بصل"])]);
      return {
        text: "🍲 طبخة مقترحة: «إدام خضار مشكل طازج (مشكل فرن)»\n👩‍🍳 شوّح البصل والطماطم وأضف الكوسة والباذنجان والبطاط على نار هادئة لغداء صحي واقتصادي يكفي العائلة 👇",
        items,
        suggestions: ["🍳 وصفة ثانية", "📦 مقاضي البيت والأسبوع", "🥗 سلة سلطة وورقيات", "عرض السلة"],
      };
    }
    const items = uniqueProducts([pickOne(["خيار"]), pickOne(["طماطم"]), pickOne(["ليمون"]), pickOne(["جرجير", "خس"]), pickOne(["بسباس"]), pickOne(["كبزر"])]).slice(0, 5);
    return {
      text: "🥗 وصفة مقترحة: «سلطة خضراء يمنية مع سحاوق طماطم وبسباس»\n👩‍🍳 افرم الخيار والطماطم والجرجير مع عصرة ليمون، واخلط الطماطم مع البسباس والكبزرة لألذ سحاوق يمني 👇",
      items,
      suggestions: ["🍳 وصفة ثانية", "🍅 سلة المطبخ اليومية", "🌅 مقاضي الصباح والفطور", "عرض السلة"],
    };
  }

  const matchedCategory = categories.find(c => norm(c.name) === q.replace(/^[^\p{L}\p{N}]+/gu, "").trim());
  if (matchedCategory) {
    const catProds = catalog.filter(p => p.categoryId === matchedCategory.id);
    if (catProds.length > 0) {
      const start = (turnIndex * 4) % catProds.length;
      const rotated = [...catProds.slice(start), ...catProds.slice(0, start)].slice(0, 5);
      return {
        text: "يا هلا بك! اخترت لك 5 أصناف مميزة وطازجة من قسم «" + matchedCategory.name + "» 👇\nتقدر تضيف أي صنف بمفرده أو تضغط لعرض دفعة أخرى من القسم:",
        items: rotated,
        suggestions: ["🔄 عرض المزيد من " + matchedCategory.name, "🌅 مقاضي الصباح والفطور", "🍅 سلة المطبخ اليومية", "عرض السلة"],
      };
    }
  }
  if (q.startsWith(norm("🔄 عرض المزيد من "))) {
    const catName = q.replace(norm("🔄 عرض المزيد من "), "").trim();
    const mc = categories.find(c => norm(c.name).includes(catName) || catName.includes(norm(c.name)));
    if (mc) {
      const catProds = catalog.filter(p => p.categoryId === mc.id);
      const start = ((turnIndex + 1) * 5) % Math.max(1, catProds.length);
      const rotated = [...catProds.slice(start), ...catProds.slice(0, start)].slice(0, 5);
      return {
        text: "تفضل يا غالي! هذي دفعة ثانية من أصناف قسم «" + mc.name + "» 👇",
        items: rotated,
        suggestions: ["🔄 عرض المزيد من " + mc.name, "🍅 سلة المطبخ اليومية", "📦 مقاضي البيت والأسبوع", "عرض السلة"],
      };
    }
  }

  return null;
}

function AssistantPage() {
  const { add, cart, setQuantity, favoriteIds } = useStore();
  const homeCatalog = trpc.commerce.catalog.home.useQuery();
  const [, navigate] = useLocation();
  const [sessionId, setSessionId] = useState<string>(getOrCreateChatSessionId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>(readAssistantHistory);
  const messagesRef = useRef<HTMLDivElement>(null);
  const appliedActionsRef = useRef(new Set<string>());
  const turnCounterRef = useRef<number>(Math.floor(Math.random() * 10));
  const seenOwnerIdsRef = useRef<Set<string>>(readSeenOwnerIds());
  const retryRef = useRef<{ request: string; history: Array<{ role: "user" | "assistant"; text: string }> } | null>(null);
  const mutation = trpc.commerce.assistant.recipe.useMutation();

  useEffect(() => {
    for (const m of messages) {
      if (m.ownerMsgId) seenOwnerIdsRef.current.add(m.ownerMsgId);
    }
    saveSeenOwnerIds(seenOwnerIdsRef.current);
  }, []);

  const pollQuery = trpc.commerce.assistant.pollMessages.useQuery(
    { sessionId },
    { refetchInterval: 2500, staleTime: 0, refetchOnMount: "always", refetchOnWindowFocus: true, retry: false }
  );

  useEffect(() => {
    const ownerMsgs = pollQuery.data?.ownerMessages;
    if (!ownerMsgs || !ownerMsgs.length) return;
    setMessages(current => {
      const existingInState = new Set(current.map(m => m.ownerMsgId).filter(Boolean));
      const unseen = ownerMsgs.filter(m => m.id && !existingInState.has(m.id) && !seenOwnerIdsRef.current.has(m.id));
      if (!unseen.length) return current;
      for (const m of unseen) seenOwnerIdsRef.current.add(m.id);
      saveSeenOwnerIds(seenOwnerIdsRef.current);
      toast.success("💬 وصلتك رسالة جديدة من إدارة المتجر!");
      return [
        ...current,
        ...unseen.map(m => ({
          role: "assistant" as const,
          text: m.text.replace(/^(?:👨‍💼\s*)?إدارة المتجر\s*:\s*/i, "").trim(),
          ownerMsgId: m.id,
        })),
      ].slice(-32);
    });
  }, [pollQuery.data, pollQuery.dataUpdatedAt]);

  const displayedMessages = messages;

  useEffect(() => {
    const saved = displayedMessages.slice(-32).map(message => ({
      role: message.role,
      text: message.text,
      ...(message.contextText ? { contextText: message.contextText } : {}),
      ...(message.ownerMsgId ? { ownerMsgId: message.ownerMsgId } : {}),
      ...(message.cartAction ? { cartAction: message.cartAction } : {}),
      ...(message.suggestedQuestions?.length ? { suggestedQuestions: message.suggestedQuestions } : {}),
    }));
    try { localStorage.setItem(ASSISTANT_HISTORY_KEY, JSON.stringify(saved)); } catch {}
  }, [displayedMessages]);

  useEffect(() => {
    const node = messagesRef.current;
    if (node) node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [displayedMessages.length, mutation.isPending]);

  const startNewConversation = () => {
    if (mutation.isPending) return;
    retryRef.current = null;
    appliedActionsRef.current.clear();
    setInput("");
    const newSid = "chat-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
    try {
      localStorage.setItem(CHAT_SESSION_KEY, newSid);
      localStorage.removeItem(ASSISTANT_HISTORY_KEY);
    } catch {}
    setSessionId(newSid);
    setMessages([assistantGreeting]);
  };

  const updateActionStatus = (actionId: string, status: "confirmed" | "cancelled") => {
    setMessages(current => current.map(message => {
      if (message.cartAction?.id === actionId) {
        return { ...message, cartAction: { ...message.cartAction, status }, contextText: (message.contextText ?? message.text) + "\nحالة طلب السلة: " + (status === "confirmed" ? "أكد العميل التغيير" : "رفض العميل التغيير") + "." };
      }
      return message;
    }));
  };

  const addSingleAssistantItem = (item: AssistantProductLine) => {
    const current = cart.find(line => line.id === item.productId);
    const qty = item.quantity || item.minQuantity || 1;
    const total = (current?.quantity ?? 0) + qty;
    if (item.stock !== null && total > item.stock) {
      toast.error("الكمية المطلوبة غير متوفرة حالياً في المخزون.");
      return;
    }
    add({ id: item.productId, name: item.name, price: item.price, unit: item.unit, stock: item.stock, minQuantity: item.minQuantity, quantityStep: item.quantityStep }, qty);
    toast.success("تمت إضافة «" + item.name + "» إلى السلة بنجاح 🛒");
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
    if (changed) toast.success(type === "add" ? "تم اعتماد وإضافة " + changed + " صنف إلى السلة بنجاح 🛒" : "تم حذف " + changed + " صنف من السلة.");
    if (skipped) toast.error("تغيّرت السلة أو الكمية المتاحة؛ راجع السلة قبل إتمام الطلب.");
  };

  const cancelCartChange = (actionId: string) => {
    if (appliedActionsRef.current.has(actionId)) return;
    appliedActionsRef.current.add(actionId);
    updateActionStatus(actionId, "cancelled");
    toast("تم إلغاء الإضافة للسلة.");
  };

  const sendText = (rawText: string, _prevAssistantText = "") => {
    const trimmed = rawText.trim();
    if (mutation.isPending || !trimmed) return;

    if (/^(?:عرض السلة|السلة|شوف السلة|تأكيد الطلب|إتمام الطلب|اتمام الطلب|سلة المشتريات|إنهاء الطلب|انهاء الطلب)$/i.test(trimmed)) {
      navigate("/cart");
      return;
    }
    if (/^(?:تصفح الأقسام|عرض الأصناف|عرض القائمة|الأقسام)$/i.test(trimmed)) {
      navigate("/categories");
      return;
    }
    if (/^(?:تصفح المنتجات|تصفح المتجر|كل المنتجات)$/i.test(trimmed)) {
      navigate("/products");
      return;
    }

    const catalogProducts: PublicProduct[] = (homeCatalog.data?.products ?? []) as PublicProduct[];
    const catalogCategories = (homeCatalog.data?.categories ?? []) as HomeData["categories"];
    turnCounterRef.current += 1;

    // Dynamic AI conversation handled by invokeLLM
    const preset = null;

    const norm = (s: string) => s.replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").toLowerCase().trim();
    const cleanTarget = norm(trimmed.replace(/^(?:أضف|اضف|إضافة|اضافة|اريد|أريد|ابغى|أبغى|عطني|أعطني|اعطني)\s+/i, ""));
    const matchedProd = catalogProducts.find(p => {
      const np = norm(p.name);
      return cleanTarget.length >= 3 && (np === cleanTarget || (trimmed.startsWith("أضف") && (np.includes(cleanTarget) || cleanTarget.includes(np))));
    });

    if (matchedProd && trimmed.length <= 40) {
      const qty = matchedProd.minQuantity || 1;
      const actId = "act-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);
      setInput("");
      setMessages(current => [
        ...current,
        { role: "user" as const, text: trimmed },
        {
          role: "assistant" as const,
          text: "جهزت لك «" + matchedProd.name + "» (" + formatPrice(matchedProd.price) + ") في البطاقة بالأسفل 👇 اضغط «✅ اعتمد الإضافة»:",
          cartAction: {
            id: actId,
            type: "add" as const,
            status: "pending" as const,
            items: [{
              productId: matchedProd.id,
              name: matchedProd.name,
              price: matchedProd.price,
              unit: matchedProd.unit,
              quantity: qty,
              stock: matchedProd.stock,
              minQuantity: matchedProd.minQuantity,
              quantityStep: matchedProd.quantityStep,
            }],
          },
          suggestedQuestions: ["🌅 مقاضي الصباح والفطور", "🍅 سلة المطبخ اليومية", "عرض السلة"],
        },
      ].slice(-32));
      return;
    }

    const updatedCart = cart.map(line => ({ productId: line.id, quantity: line.quantity }));
    const history = displayedMessages
      .filter(m => !m.ownerMsgId && !m.text.includes("إدارة المتجر"))
      .slice(-4)
      .map(message => ({ role: message.role, text: assistantHistoryText(message) }));
    setMessages(current => [...current, { role: "user" as const, text: trimmed }].slice(-32));
    retryRef.current = { request: trimmed, history };
    setInput("");

    let cName = "";
    let cPhone = "";
    try {
      const d = JSON.parse(localStorage.getItem("original-customer-browser-v1") || "{}");
      cName = d.name || d.addresses?.[0]?.recipientName || "";
      cPhone = d.phone || d.addresses?.[0]?.phone || "";
    } catch {}

    mutation.mutate({
      request: trimmed,
      history,
      cart: updatedCart,
      favoriteProductIds: favoriteIds,
      sessionId,
      customerName: cName,
      customerPhone: cPhone,
    }, {
      onSuccess: (result: any) => {
        retryRef.current = null;
        void pollQuery.refetch();
        let pendingAction: AssistantCartAction | undefined = undefined;
        if (result.cartAction && (result.cartAction.type === "add" || result.cartAction.type === "remove") && Array.isArray(result.cartAction.items) && result.cartAction.items.length > 0) {
          pendingAction = {
            id: "act-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6),
            type: result.cartAction.type,
            items: result.cartAction.items,
            status: "pending",
          };
        } else if (Array.isArray(result.ingredients) && result.ingredients.length > 0) {
          pendingAction = {
            id: "act-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6),
            type: "add",
            items: result.ingredients,
            status: "pending",
          };
        }
        const cleanReply = String(result.message || "")
          .replace(/^(?:👨‍💼\s*)?إدارة المتجر\s*:\s*/i, "")
          .replace(/\[\s*(?:أضف|اضف|إضافة|اضافة|add|مقادير|سلة)\s*:[^\]]+\]/gi, "")
          .trim();
        setMessages(current => [...current, {
          role: "assistant" as const,
          text: cleanReply,
          recipe: result.recipe,
          ingredients: result.ingredients,
          missingIngredients: result.missingIngredients,
          cartAction: pendingAction,
          suggestedQuestions: Array.isArray(result.suggestedQuestions) ? result.suggestedQuestions : [],
        }].slice(-32));
      },
      onError: () => {
        toast.error("يرجى المحاولة مرة أخرى.");
        setInput(trimmed);
      },
    });
  };

  const send = (event: FormEvent) => {
    event.preventDefault();
    sendText(input);
  };

  return (
    <main className="page-shell inner-page assistant-page">
      <section className="chat-panel">
        <div className="chat-head">
          <span className="chat-avatar"><Sparkles size={17} /></span>
          <div><strong>مساعد وشيف أورجنال الذكي</strong><small>سلات يومية · مقاضي الصباح · وصفات اقتصادية</small></div>
          <span className="online-dot" />
          <button type="button" className="assistant-new-chat" disabled={mutation.isPending} onClick={startNewConversation}>محادثة جديدة</button>
        </div>
        <div className="chat-messages" ref={messagesRef}>
          {displayedMessages.map((message, index) => {
            const totalActionPrice = message.cartAction?.items.reduce((s, it) => s + it.price * it.quantity, 0) ?? 0;
            return (
              <div key={index + "-" + message.role + "-" + (message.ownerMsgId || "")} className={"chat-message " + (message.role === "user" ? "from-user" : "from-assistant")} style={message.ownerMsgId ? { border: "1.5px solid #e0a800", background: "#fffdf5" } : undefined}>
                {message.ownerMsgId && (
                  <div style={{ fontSize: "11px", fontWeight: 800, color: "#9a6700", marginBottom: "4px", paddingBottom: "4px", borderBottom: "1px solid #f2e2a8" }}>
                    👨‍💼 رد مباشر من إدارة المتجر
                  </div>
                )}
                <p style={{ whiteSpace: "pre-line", margin: 0, lineHeight: 1.65 }}>{message.text}</p>
                {message.cartAction && message.cartAction.items.length > 0 && (
                  <div style={{ marginTop: "10px", padding: "11px 12px", borderRadius: "14px", background: "#f3faf6", border: "1.5px solid #b8dec8", boxShadow: "0 4px 12px rgba(15, 60, 40, 0.06)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", fontWeight: 800, color: "#123b2a", marginBottom: "8px" }}>
                      <span>{message.cartAction.items.length > 1 ? "🛒 الأصناف والمقادير المقترحة للسلة:" : "🛒 تأكيد إضافة الصنف للسلة:"}</span>
                      <span style={{ color: "#174b36", background: "#e2f2e9", padding: "2px 8px", borderRadius: "99px", fontSize: "11px" }}>الإجمالي: {formatPrice(totalActionPrice)}</span>
                    </div>
                    <div style={{ display: "grid", gap: "6px", marginBottom: "10px" }}>
                      {message.cartAction.items.map(item => (
                        <div key={item.productId} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", padding: "6px 9px", borderRadius: "10px", background: "#ffffff", border: "1px solid #dfece4", fontSize: "11.5px", color: "#1e3f2f" }}>
                          <div>
                            <strong>{item.name}</strong>
                            <small style={{ display: "block", color: "#5c7467", fontSize: "10.5px" }}>{item.quantity} × {formatPrice(item.price)} ({item.unit})</small>
                          </div>
                          <button
                            type="button"
                            onClick={() => addSingleAssistantItem(item)}
                            style={{ padding: "5px 10px", borderRadius: "8px", border: "1px solid #174b36", background: "#f2f9f5", color: "#174b36", fontSize: "11px", fontWeight: 800, cursor: "pointer", whiteSpace: "nowrap" }}
                          >
                            + أضف بمفرده
                          </button>
                        </div>
                      ))}
                    </div>
                    {message.cartAction.status === "pending" ? (
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          type="button"
                          onClick={() => applyConfirmedChange(message.cartAction!.id, message.cartAction!.type, message.cartAction!.items)}
                          style={{ flex: 1, padding: "8px 12px", borderRadius: "10px", border: "none", background: "#174b36", color: "#ffffff", fontSize: "12px", fontWeight: 800, cursor: "pointer", boxShadow: "0 3px 10px rgba(23, 75, 54, 0.2)" }}
                        >
                          {message.cartAction.items.length > 1 ? ("✅ اعتمد وإضافة الكل للسلة (" + formatPrice(totalActionPrice) + ")") : ("✅ نعم، اعتمد الإضافة للسلة (" + formatPrice(totalActionPrice) + ")")}
                        </button>
                        <button
                          type="button"
                          onClick={() => cancelCartChange(message.cartAction!.id)}
                          style={{ padding: "8px 12px", borderRadius: "10px", border: "1px solid #cbd5e1", background: "#ffffff", color: "#475569", fontSize: "11.5px", fontWeight: 700, cursor: "pointer" }}
                        >
                          إلغاء
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11.5px", fontWeight: 800, color: message.cartAction.status === "confirmed" ? "#15803d" : "#64748b" }}>
                        <span>{message.cartAction.status === "confirmed" ? "✅ تمت الإضافة إلى السلة بنجاح!" : "تم إلغاء الإضافة"}</span>
                        {message.cartAction.status === "confirmed" && (
                          <button type="button" onClick={() => navigate("/cart")} style={{ padding: "4px 10px", borderRadius: "8px", border: "none", background: "#174b36", color: "#fff", fontSize: "11px", fontWeight: 800, cursor: "pointer" }}>
                            فتح السلة 🛒
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {message.role === "assistant" && message.text.includes("770731619") && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard?.writeText("770731619");
                        toast.success("تم نسخ رقم المالك 770731619 بنجاح!");
                      }}
                      style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "10px", border: "1px solid #0f5c3a", background: "#f2f9f5", color: "#0f5c3a", fontSize: "0.78rem", fontWeight: 700, cursor: "pointer" }}
                    >
                      <Copy size={13} /> نسخ الرقم: 770731619
                    </button>
                    <a
                      href="tel:770731619"
                      style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "10px", border: "1px solid #d5e6dc", background: "#ffffff", color: "#0f5c3a", fontSize: "0.78rem", fontWeight: 700, textDecoration: "none" }}
                    >
                      📞 اتصال مباشر
                    </a>
                  </div>
                )}
                {message.role === "assistant" && message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "9px" }}>
                    {message.suggestedQuestions.map((q, qIdx) => (
                      <button
                        key={qIdx}
                        type="button"
                        disabled={mutation.isPending}
                        onClick={() => sendText(q, message.text)}
                        style={{ padding: "6px 12px", borderRadius: "999px", border: "1px solid #cfe2d6", background: "#f3f9f5", color: "#0f5c3a", fontSize: "0.76rem", fontWeight: 700, cursor: "pointer" }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {mutation.isPending && (
            <div className="chat-message from-assistant" style={{ opacity: 0.75 }}>
              <p>يجهز لك الرد والاقتراحات الآن...</p>
            </div>
          )}
        </div>
        <form className="chat-input" onSubmit={send}>
          <input maxLength={1200} value={input} onChange={event => setInput(event.target.value)} placeholder="اطلب سلة الصباح، مقاضي المطبخ، أو وصفة اقتصادية..." aria-label="رسالة للمساعد" disabled={mutation.isPending} />
          <button disabled={mutation.isPending || !input.trim()} aria-label="إرسال"><ArrowLeft size={18} /></button>
        </form>
      </section>
    </main>
  );
}

function Loading() { return <div className="loading-state"><LoaderCircle size={22} className="spin" /><span>لحظة، نحدّث المعلومات...</span></div>; }
function LoadError({ onRetry }: { onRetry: () => void }) { return <div className="error-state"><span className="error-symbol">!</span><strong>تعذر تحميل البيانات</strong><p>تحقق من اتصالك ثم حاول مجددًا. لم نفترض وجود بيانات غير مؤكدة.</p><button className="button button-outline" onClick={onRetry}>إعادة المحاولة</button></div>; }

function shouldShowFooterDescription(description: string | null | undefined) {
  const text = description?.trim().replace(/\s+/g, " ");
  if (!text) return false;
  return text !== "كل ماتحتاجه باب بيتك بضغطه زر" && text !== "كل ما تحتاجه باب بيتك بضغطه زر";
}

type StoreRewardCfg = {
  rewardMode: "custom_gift" | "free_delivery" | "discount_percent" | "discount_fixed";
  giftName: string;
  fixedDiscount: number;
  endsAt: string;
  audience: "all" | "new_customers" | "returning_customers" | "vip_customers" | "specific_phones";
  allowedPhones: string;
  placement: "everywhere" | "home_and_cart" | "cart_only";
};

function unpackStoreRewardCfg(rawMsg?: string | null, fallbackType?: string): { cleanMessage: string; cfg: StoreRewardCfg } {
  const defaultCfg: StoreRewardCfg = {
    rewardMode: fallbackType === "discount_percent" ? "discount_percent" : "free_delivery",
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

function formatCountdownLeft(ms: number): string {
  if (ms <= 0) return "";
  const totalSec = Math.floor(ms / 1000);
  const days = Math.floor(totalSec / 86400);
  const hrs = Math.floor((totalSec % 86400) / 3600);
  const mins = Math.floor((totalSec % 3600) / 60);
  const secs = totalSec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  if (days > 0) return days + " يوم و " + pad(hrs) + ":" + pad(mins) + ":" + pad(secs);
  return pad(hrs) + ":" + pad(mins) + ":" + pad(secs);
}

function GamifiedRewardBar({ settings, location }: { settings: Record<string, string | undefined>; location: string }) {
  const { cart } = useStore();
  const customer = useCustomer();
  const [, navigate] = useLocation();
  const enabled = settings?.rewardEnabled === "true";
  const threshold = Number(settings?.rewardsThreshold || 0);
  const { cleanMessage, cfg } = useMemo(() => unpackStoreRewardCfg(settings?.rewardsMessage, settings?.rewardType), [settings?.rewardsMessage, settings?.rewardType]);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!enabled || !cfg.endsAt) return;
    const timer = window.setInterval(() => setNowMs(Date.now()), 10000);
    return () => window.clearInterval(timer);
  }, [enabled, cfg.endsAt]);

  if (!enabled || !Number.isFinite(threshold) || threshold <= 0) return null;

  const endMs = cfg.endsAt ? new Date(cfg.endsAt).getTime() : 0;
  if (endMs && Number.isFinite(endMs) && nowMs > endMs) return null;
  const countdownText = endMs && Number.isFinite(endMs) ? formatCountdownLeft(endMs - nowMs) : "";

  const orderCount = customer.orders?.length || 0;
  if (cfg.audience === "new_customers" && orderCount > 0) return null;
  if (cfg.audience === "returning_customers" && orderCount < 1) return null;
  if (cfg.audience === "vip_customers" && orderCount < 3) return null;
  if (cfg.audience === "specific_phones") {
    const allowed = cfg.allowedPhones.split(/[\s,،;]+/).map(s => s.replace(/\D/g, "")).filter(Boolean);
    const myPhones = [customer.phone, ...(customer.addresses || []).map(a => a.phone)].map(s => String(s || "").replace(/\D/g, "")).filter(Boolean);
    const matched = allowed.some(ap => myPhones.some(mp => mp.endsWith(ap) || ap.endsWith(mp)));
    if (!matched) return null;
  }

  const isHome = location === "/";
  const isCart = location === "/cart";
  const isCatalog = location.startsWith("/products") || location.startsWith("/categories");
  const showMainCard =
    cfg.placement === "everywhere" ? (isHome || isCart || isCatalog) :
    cfg.placement === "home_and_cart" ? (isHome || isCart) :
    isCart;

  const subtotal = cart.reduce((sum, line) => sum + line.price * line.quantity, 0);
  const remaining = Math.max(0, threshold - subtotal);
  const pct = Math.min(100, Math.max(0, Math.round((subtotal / threshold) * 100)));
  const unlocked = subtotal >= threshold;

  const giftLabel = cfg.giftName || (
    cfg.rewardMode === "free_delivery" ? "توصيل مجاني بالكامل 🛵" :
    cfg.rewardMode === "discount_percent" ? ("خصم فوري " + (settings?.rewardValue || "10") + "% 🏷️") :
    cfg.rewardMode === "discount_fixed" ? ("خصم نقدي " + formatPrice(cfg.fixedDiscount || Number(settings?.rewardValue || 0)) + " 💸") :
    "هدية مجانية من أورجنال 🎁"
  );

  const headline = unlocked
    ? ("🎉 مبروك! فتحت الهدية: «" + giftLabel + "» — تُضاف تلقائياً مع طلبك!")
    : subtotal === 0
    ? ("🎁 عرض حماسي! تسوّق بقيمة " + formatPrice(threshold) + " واحصل فوراً على «" + giftLabel + "»")
    : pct >= 60
    ? ("⚡ اقتربت جداً! باقي لك " + formatPrice(remaining) + " فقط لتربح «" + giftLabel + "»!")
    : ("🔥 أضف منتجات بقيمة " + formatPrice(remaining) + " لفتح الهدية: «" + giftLabel + "»");

  const showFloatingMini = cfg.placement === "everywhere" && !isCart && subtotal > 0 && !location.startsWith("/assistant") && !location.startsWith("/orders") && !location.startsWith("/account");

  return (
    <>
      {showMainCard && (
        <div className="page-shell" style={{ paddingTop: "10px", paddingBottom: "4px" }}>
          <section
            style={{
              position: "relative",
              overflow: "hidden",
              borderRadius: "20px",
              padding: "14px 16px",
              background: unlocked
                ? "linear-gradient(135deg, #10462f 0%, #1d6b47 55%, #b5851f 100%)"
                : "linear-gradient(135deg, #0e3322 0%, #185138 60%, #113c29 100%)",
              color: "#ffffff",
              border: unlocked ? "2px solid #f7dc8b" : "1.5px solid rgba(241, 216, 151, 0.45)",
              boxShadow: unlocked ? "0 14px 32px rgba(24, 81, 56, 0.28)" : "0 10px 24px rgba(14, 51, 34, 0.18)",
              transition: "all 0.35s ease",
            }}
          >
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: "1 1 220px" }}>
                <span
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "12px",
                    background: unlocked ? "#f7dc8b" : "rgba(241, 216, 151, 0.18)",
                    color: unlocked ? "#103b28" : "#f7dc8b",
                    display: "grid",
                    placeItems: "center",
                    fontSize: "19px",
                    flexShrink: 0,
                    boxShadow: unlocked ? "0 4px 14px rgba(247, 220, 139, 0.45)" : "none",
                  }}
                >
                  {unlocked ? "🏆" : "🎁"}
                </span>
                <div style={{ lineHeight: 1.4 }}>
                  <strong style={{ display: "block", fontSize: "13px", color: "#fff9e6" }}>{headline}</strong>
                  {cleanMessage && <small style={{ display: "block", fontSize: "11px", color: "#d7ecdf", opacity: 0.95 }}>{cleanMessage}</small>}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                {countdownText && (
                  <span style={{ fontSize: "10.5px", fontWeight: 800, padding: "3px 9px", borderRadius: "99px", background: "rgba(0,0,0,0.28)", color: "#ffe596", border: "1px solid rgba(255,229,150,0.35)" }} dir="ltr">
                    ⏳ {countdownText}
                  </span>
                )}
                <span style={{ fontSize: "11px", fontWeight: 800, padding: "3px 10px", borderRadius: "99px", background: unlocked ? "#f7dc8b" : "rgba(255,255,255,0.14)", color: unlocked ? "#0f3826" : "#f7dc8b" }}>
                  {unlocked ? "مكتمل 100% ✨" : (pct + "%")}
                </span>
              </div>
            </div>

            <div style={{ height: "11px", borderRadius: "99px", background: "rgba(255,255,255,0.16)", padding: "2px", overflow: "hidden" }}>
              <div
                style={{
                  width: Math.max(subtotal > 0 ? 6 : 0, pct) + "%",
                  height: "100%",
                  borderRadius: "99px",
                  background: unlocked
                    ? "linear-gradient(90deg, #ffe58f 0%, #4ade80 50%, #f7dc8b 100%)"
                    : "linear-gradient(90deg, #f3c65f 0%, #ffe699 65%, #6ee7b7 100%)",
                  transition: "width 0.45s cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "7px", fontSize: "11px", color: "#d8eee1" }}>
              <span>سلتك الآن: <b style={{ color: "#ffffff" }}>{formatPrice(subtotal)}</b></span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>الهدف: <b style={{ color: "#f7dc8b" }}>{formatPrice(threshold)}</b></span>
                {!isCart && subtotal > 0 && (
                  <button
                    type="button"
                    onClick={() => navigate("/cart")}
                    style={{ padding: "3px 10px", borderRadius: "99px", border: "none", background: "#f7dc8b", color: "#0e3322", fontSize: "10.5px", fontWeight: 800, cursor: "pointer" }}
                  >
                    {unlocked ? "استلم هديتك في السلة 🎁" : "عرض السلة 🛒"}
                  </button>
                )}
              </div>
            </div>
          </section>
        </div>
      )}

      {showFloatingMini && (
        <div
          onClick={() => navigate("/cart")}
          style={{
            position: "fixed",
            left: "12px",
            right: "12px",
            bottom: "74px",
            zIndex: 45,
            maxWidth: "560px",
            margin: "0 auto",
            padding: "9px 13px",
            borderRadius: "16px",
            background: unlocked ? "linear-gradient(135deg, #114a32, #1e6e4a)" : "rgba(15, 54, 37, 0.96)",
            color: "#ffffff",
            border: unlocked ? "1.5px solid #f7dc8b" : "1px solid rgba(247, 220, 139, 0.4)",
            boxShadow: "0 10px 26px rgba(0, 0, 0, 0.25)",
            cursor: "pointer",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", fontSize: "11.5px", fontWeight: 800, marginBottom: "5px" }}>
            <span style={{ color: "#fff8e1" }}>
              {unlocked ? ("🎉 مبروك! ربحت «" + giftLabel + "» — اضغط لإتمام الطلب") : ("🔥 باقي " + formatPrice(remaining) + " لتربح «" + giftLabel + "»")}
            </span>
            <span style={{ color: "#f7dc8b", fontSize: "11px", flexShrink: 0 }}>{pct}%</span>
          </div>
          <div style={{ height: "6px", borderRadius: "99px", background: "rgba(255,255,255,0.18)", overflow: "hidden" }}>
            <div style={{ width: Math.max(6, pct) + "%", height: "100%", borderRadius: "99px", background: "linear-gradient(90deg, #f3c65f, #4ade80)", transition: "width 0.4s ease" }} />
          </div>
        </div>
      )}
    </>
  );
}





const INSTANT_CACHE_KEY = "original-catalog-instant-v2";
function readLocalInstantCatalog(): HomeData {
  try {
    if (typeof window !== "undefined" && (window as any).__INITIAL_CATALOG__) {
      const initCat = (window as any).__INITIAL_CATALOG__;
      if (initCat && Array.isArray(initCat.products)) {
        try { localStorage.setItem(INSTANT_CACHE_KEY, JSON.stringify(initCat)); } catch {}
        return initCat;
      }
    }
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem(INSTANT_CACHE_KEY) : null;
    if (saved) {
      const p = JSON.parse(saved);
      if (p && Array.isArray(p.products)) return p;
    }
  } catch {}
  return { categories: [], products: [], banners: [], offers: [], settings: {} };
}
const INSTANT_CACHE_KEY = "original-instant-catalog-v5";
function readLocalInstantCatalog(): HomeData {
  try {
    const w = window as any;
    if (w.__INITIAL_CATALOG__ && Array.isArray(w.__INITIAL_CATALOG__.products) && w.__INITIAL_CATALOG__.products.length > 0) return w.__INITIAL_CATALOG__ as HomeData;
    const raw = localStorage.getItem(INSTANT_CACHE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.products)) return parsed as HomeData;
    }
  } catch {}
  return { categories: [], products: [], banners: [], offers: [], settings: {} };
}
function computeStorePauseStatus(settings?: Record<string, string>): { paused: boolean; message: string } {
  if (!settings) return { paused: false, message: '' };
  if (settings.orderPaused === 'true') return { paused: true, message: settings.pausedMessage || 'استقبال الطلبات متوقف مؤقتًا.' };
  if (settings.autoScheduleEnabled === 'true') {
    const cStr = String(settings.autoCloseTime || '').trim();
    const oStr = String(settings.autoOpenTime || '').trim();
    const cm = cStr.match(/^(\d{1,2}):(\d{2})$/);
    const om = oStr.match(/^(\d{1,2}):(\d{2})$/);
    if (cm && om) {
      const cMins = Number(cm[1]) * 60 + Number(cm[2]);
      const oMins = Number(om[1]) * 60 + Number(om[2]);
      if (cMins !== oMins) {
        const yemenNow = new Date(Date.now() + 3 * 3600 * 1000);
        const curMins = yemenNow.getUTCHours() * 60 + yemenNow.getUTCMinutes();
        const isClosed = cMins > oMins ? (curMins >= cMins || curMins < oMins) : (curMins >= cMins && curMins < oMins);
        if (isClosed) {
          const oh = Number(om[1]);
          const period = oh >= 12 ? 'مساءً' : 'صباحاً';
          const h12 = oh % 12 === 0 ? 12 : oh % 12;
          return { paused: true, message: settings.pausedMessage || ('🌙 المتجر مغلق حالياً خارج أوقات الدوام — يفتح تلقائياً الساعة ' + h12 + ':' + om[2] + ' ' + period) };
        }
      }
    }
  }
  return { paused: false, message: '' };
}

export default function Home() {
  const storeCtx = useStore();
  const customerForPrefetch = useCustomer();
  const bgRefs = useMemo(() => customerForPrefetch.orders.slice(0, 50).map(({ orderNumber, idempotencyKey }) => ({ orderNumber: String(orderNumber || '').trim(), idempotencyKey: String(idempotencyKey || '').trim() })).filter(r => r.orderNumber && r.idempotencyKey), [customerForPrefetch.orders]);
  const bgPhone = cleanYemeniPhone(customerForPrefetch.phone || customerForPrefetch.addresses[0]?.phone || '');
  const bgValidPhone = isValidYemeniPhone(bgPhone) ? bgPhone : undefined;
  const [bgOrdersEnabled, setBgOrdersEnabled] = useState(false);
  useEffect(() => { const t = setTimeout(() => setBgOrdersEnabled(true), 1200); return () => clearTimeout(t); }, []);
  const bgOrdersPrefetch = trpc.commerce.orders.trackMany.useQuery({ refs: bgRefs, ...(bgValidPhone ? { phone: bgValidPhone } : {}) } as any, { enabled: bgOrdersEnabled && (bgRefs.length > 0 || Boolean(bgValidPhone)), retry: 0, staleTime: 15000 });
  useEffect(() => { if (bgOrdersPrefetch.data && Array.isArray(bgOrdersPrefetch.data) && bgOrdersPrefetch.data.length > 0) { try { localStorage.setItem('original-orders-track-cache-v1', JSON.stringify(bgOrdersPrefetch.data)); } catch {} } }, [bgOrdersPrefetch.data]);
  const lastCatalogSigRef = useRef("");
  const [activeAiProduct, setActiveAiProduct] = useState<PublicProduct | null>(null);
  useGuestPushSubscriptionSync();
  const [location, navigate] = useLocation();
  const [instantData, setInstantData] = useState<HomeData>(() => readLocalInstantCatalog());
  const home = trpc.commerce.catalog.home.useQuery(undefined, { retry: 1, staleTime: 25000, refetchInterval: 30000, refetchOnMount: "always", refetchOnWindowFocus: true, placeholderData: instantData.products?.length ? instantData : undefined });
  useEffect(() => {
    try {
      const w = window as any;
      if (w.__isRestoringFromProduct && w.__navReturnState) {
        const y = Number(w.__navReturnState.scrollY || 0);
        w.__isRestoringFromProduct = false;
        const go = () => { try { window.scrollTo({ top: y, left: 0, behavior: "instant" as ScrollBehavior }); document.documentElement.scrollTop = y; document.body.scrollTop = y; } catch {} };
        go(); requestAnimationFrame(go); setTimeout(go, 45); return;
      }
      window.scrollTo({ top: 0, left: 0, behavior: "instant" as ScrollBehavior }); document.documentElement.scrollTop = 0; document.body.scrollTop = 0;
    } catch {}
  }, [location]);
  useEffect(() => {
    if (home.data && Array.isArray(home.data.products)) {
      const sig = home.data.products.length + ":" + (home.data.products[0]?.id || 0) + ":" + (home.data.products[home.data.products.length - 1]?.id || 0) + ":" + (home.data.categories?.length || 0);
      if (lastCatalogSigRef.current === sig) return;
      lastCatalogSigRef.current = sig;
      setInstantData(home.data as HomeData);
      storeCtx.syncCatalogProducts?.(home.data.products as any);
      try { (window as any).__INITIAL_CATALOG__ = home.data; localStorage.setItem(INSTANT_CACHE_KEY, JSON.stringify(home.data)); } catch {}
    }
  }, [home.data]);
  const data = ((home.data && home.data.products ? home.data : instantData) ?? { categories: [], products: [], banners: [], offers: [], settings: {} }) as HomeData;
  const openProduct = (id: number) => {
    try {
      const w = window as any;
      if (!window.location.pathname.startsWith("/product/")) {
        w.__navReturnState = { returnPath: (window.location.pathname + window.location.search) || "/", scrollY: window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0 };
      }
      w.__isRestoringFromProduct = false;
      window.scrollTo({ top: 0, left: 0, behavior: "instant" as ScrollBehavior }); document.documentElement.scrollTop = 0; document.body.scrollTop = 0;
    } catch {}
    navigate("/product/" + id);
  };
  const handleBackFromProduct = () => {
    try { const w = window as any; w.__isRestoringFromProduct = true; navigate(w.__navReturnState?.returnPath || "/"); } catch { navigate("/"); }
  };
  const currentNav = location.startsWith("/categories") ? "/categories" : location.startsWith("/products") ? "/products" : location.startsWith("/assistant") ? "/assistant" : location.startsWith("/account") ? "/account" : "/";
  const productPath = location.startsWith("/product/");
  const productId = productPath ? Number(location.split("/")[2]) : 0;
  const content = useMemo(() => {
    if (productPath && Number.isInteger(productId)) return <ProductDetail id={productId} allProducts={data.products} onSelectProduct={openProduct} onBack={handleBackFromProduct} onAiRecipe={setActiveAiProduct} />;
    if (location === "/products" || location.startsWith("/products?")) return <ProductListPage data={data} onOpen={openProduct} onAiRecipe={setActiveAiProduct} />;
    if (location === "/categories") return <CategoriesPage data={data} />;
    if (location === "/cart") return <CartPage />;
    if (location === "/favorites") return <FavoritesPage allProducts={data.products} onOpen={openProduct} onAiRecipe={setActiveAiProduct} />;
    if (location === "/orders") return <OrdersPage />;
    if (location === "/account") return <AccountPage />;
    if (location === "/assistant") return <AssistantPage />;
    return <HomePage data={data} onOpen={openProduct} onAiRecipe={setActiveAiProduct} />;
  }, [location, productId, productPath, data]);
  return <div className="store-app" dir="rtl"><Header data={data} onSearch={text => navigate("/products" + (text ? "?search=" + encodeURIComponent(text) : ""))} />{!location.startsWith("/assistant") && !location.startsWith("/orders") && !location.startsWith("/account") && <GamifiedRewardBar settings={data.settings} location={location} />}{home.isError && !data.products?.length && !data.categories?.length && <div className="connection-strip"><span>الاتصال بالخدمة غير متاح مؤقتًا</span><button onClick={() => void home.refetch()}>إعادة المحاولة</button></div>}{home.isError && !data.products?.length && !data.categories?.length ? <main className="page-shell inner-page"><LoadError onRetry={() => void home.refetch()} /></main> : content}{!location.startsWith("/assistant") && <footer className="store-footer"><div className="footer-brand"><span className="brand-mark"><Leaf size={22} strokeWidth={1.8} /></span><span><b>ORIGINAL</b><small>{data.settings.storeName === "ORIGINAL – أورجنال" || !data.settings.storeName ? "أورجنال" : data.settings.storeName}</small></span></div>{shouldShowFooterDescription(data.settings.storeDescription) && <span>{data.settings.storeDescription}</span>}<small>© {new Date().getFullYear()} {data.settings.storeName || "ORIGINAL"}</small></footer>}{activeAiProduct && <AiRecipeModal product={activeAiProduct} onClose={() => setActiveAiProduct(null)} />}<BottomNav active={currentNav} /></div>;
}
