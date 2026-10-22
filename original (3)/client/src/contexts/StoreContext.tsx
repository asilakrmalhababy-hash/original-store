import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type StoreProduct = {
  id: number; name: string; price: number; unit: string; imageUrl?: string | null;
  minQuantity?: number; quantityStep?: number; stock?: number | null;
};
export type CartLine = StoreProduct & { quantity: number };
type StoreContextValue = {
  cart: CartLine[];
  favoriteIds: number[];
  isFavorite: (id: number) => boolean;
  toggleFavorite: (id: number) => void;
  add: (product: StoreProduct, quantity?: number) => void;
  setQuantity: (id: number, quantity: number) => void;
  remove: (id: number) => void;
  clear: () => void;
};

const StoreContext = createContext<StoreContextValue | null>(null);
const CART_STORAGE_KEY = "original-store-cart-v1";
const FAVORITES_STORAGE_KEY = "original-store-favorites-v1";

function readCart(): CartLine[] {
  try {
    const value = localStorage.getItem(CART_STORAGE_KEY);
    if (!value) return [];
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is CartLine => item && Number.isInteger(item.id) && Number.isInteger(item.quantity) && item.quantity > 0 && typeof item.name === "string" && Number.isInteger(item.price));
  } catch { return []; }
}

function readFavorites(): number[] {
  try {
    const value = localStorage.getItem(FAVORITES_STORAGE_KEY);
    if (!value) return [];
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    return [...new Set(parsed.filter((id): id is number => Number.isInteger(id) && id > 0))].slice(0, 500);
  } catch { return []; }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<CartLine[]>(readCart);
  const [favoriteIds, setFavoriteIds] = useState<number[]>(readFavorites);
  useEffect(() => {
    try { localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart)); } catch { /* storage can be unavailable */ }
  }, [cart]);
  useEffect(() => {
    try { localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favoriteIds)); } catch { /* storage can be unavailable */ }
  }, [favoriteIds]);

  const value = useMemo<StoreContextValue>(() => ({
    cart,
    favoriteIds,
    isFavorite: id => favoriteIds.includes(id),
    toggleFavorite: id => setFavoriteIds(current => current.includes(id) ? current.filter(value => value !== id) : [...current, id].slice(-500)),
    add: (product, quantity = product.minQuantity ?? 1) => setCart(current => {
      const found = current.find(line => line.id === product.id);
      if (!found) return [...current, { ...product, quantity }];
      return current.map(line => line.id === product.id ? { ...line, ...product, quantity: line.quantity + quantity } : line);
    }),
    setQuantity: (id, quantity) => setCart(current => quantity <= 0 ? current.filter(line => line.id !== id) : current.map(line => line.id === id ? { ...line, quantity } : line)),
    remove: id => setCart(current => current.filter(line => line.id !== id)),
    clear: () => setCart([]),
  }), [cart, favoriteIds]);

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const context = useContext(StoreContext);
  if (!context) throw new Error("useStore must be used inside StoreProvider");
  return context;
}
