const fs = require("fs");

const file = "client/src/pages/Home.tsx";
let source = fs.readFileSync(file, "utf8");

const oldBlock = `  const cachedProducts = !debouncedSearch
    ? data.products.filter(product => categoryId === undefined || product.categoryId === categoryId)
    : [];
  const input = { search: debouncedSearch || undefined, categoryId, sort: "featured" as const, limit: 500 };
  const query = trpc.commerce.catalog.listProducts.useQuery(input, { retry: 1, staleTime: 0, refetchOnMount: "always", placeholderData: cachedProducts.length ? cachedProducts : undefined });`;

const newBlock = `  const [offset, setOffset] = useState(0);
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
  }, [hasMore, query.isFetching, query.isError, offset]);`;

if (!source.includes(oldBlock)) {
  console.error("لم أجد مقطع الاستعلام القديم كما هو. لم يتم تعديل الملف.");
  process.exit(1);
}

source = source.replace(oldBlock, newBlock);

const oldRender = `{(query.isLoading && !cachedProducts.length) ? <Loading /> : (query.error && !cachedProducts.length) ? <LoadError onRetry={() => void query.refetch()} /> : <ProductGrid items={(query.data && query.data.length > 0) ? query.data : cachedProducts} onOpen={onOpen} onAiRecipe={onAiRecipe} />}`;

const newRender = `{query.isLoading && loadedProducts.length === 0 ? (
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
      )}`;

if (!source.includes(oldRender)) {
  console.error("لم أجد مقطع عرض المنتجات كما هو. لم يتم حفظ أي تعديل.");
  process.exit(1);
}

source = source.replace(oldRender, newRender);

const backup = file + ".backup-infinite-" + Date.now();
fs.copyFileSync(file, backup);
fs.writeFileSync(file, source);

console.log("نجح تعديل واجهة المنتجات.");
console.log("النسخة الاحتياطية:", backup);
