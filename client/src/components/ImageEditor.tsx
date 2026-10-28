import { useEffect, useRef, useState } from "react";
import { Check, Crop, ImagePlus, LoaderCircle, Maximize2, Move, RotateCcw, RotateCw, Sparkles, Square, Wand2, X } from "lucide-react";

type Props = {
  aspect: number;
  title: string;
  format?: "webp" | "png";
  initialSource?: string;
  initialTool?: "crop" | "lasso";
  onSave: (dataUrl: string) => void;
  onCancel: () => void;
};

type CropBox = { x: number; y: number; w: number; h: number };
type DragKind = "move" | "nw" | "ne" | "sw" | "se" | "n" | "s" | "e" | "w";
type Pt = { x: number; y: number };

function performSmartLassoCutout(
  img: HTMLImageElement,
  lassoNorm: Pt[],
  sensitivity: number,
  addShadow: boolean,
  autoCenter: boolean
): { resultDataUrl: string; contourNorm: Pt[] } {
  const maxWork = 460;
  const natW = img.naturalWidth || img.width || 500;
  const natH = img.naturalHeight || img.height || 500;
  const scale = Math.min(1, maxWork / Math.max(natW, natH));
  const W = Math.max(64, Math.round(natW * scale));
  const H = Math.max(64, Math.round(natH * scale));

  const srcCanvas = document.createElement("canvas");
  srcCanvas.width = W;
  srcCanvas.height = H;
  const sctx = srcCanvas.getContext("2d")!;
  sctx.drawImage(img, 0, 0, W, H);
  const imgData = sctx.getImageData(0, 0, W, H);
  const data = imgData.data;

  const polyCanvas = document.createElement("canvas");
  polyCanvas.width = W;
  polyCanvas.height = H;
  const pctx = polyCanvas.getContext("2d")!;
  pctx.fillStyle = "#ffffff";
  pctx.beginPath();
  const pts = lassoNorm.length >= 3
    ? lassoNorm.map(p => ({ x: p.x * W, y: p.y * H }))
    : [
        { x: W * 0.05, y: H * 0.05 },
        { x: W * 0.95, y: H * 0.05 },
        { x: W * 0.95, y: H * 0.95 },
        { x: W * 0.05, y: H * 0.95 },
      ];
  pctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) pctx.lineTo(pts[i].x, pts[i].y);
  pctx.closePath();
  pctx.fill();
  const polyData = pctx.getImageData(0, 0, W, H).data;

  const N = W * H;
  const insideLasso = new Uint8Array(N);
  let minX = W, minY = H, maxX = 0, maxY = 0;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const idx = y * W + x;
      if (polyData[idx * 4] > 128) {
        insideLasso[idx] = 1;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }

  if (maxX - minX < 12 || maxY - minY < 12) {
    insideLasso.fill(0);
    minX = Math.round(W * 0.05); maxX = Math.round(W * 0.95);
    minY = Math.round(H * 0.05); maxY = Math.round(H * 0.95);
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) insideLasso[y * W + x] = 1;
    }
  }

  type ColorSample = { r: number; g: number; b: number; x: number; y: number };
  const bgSamples: ColorSample[] = [];
  const boundaryIndices: number[] = [];
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const idx = y * W + x;
      if (!insideLasso[idx]) continue;
      if (!insideLasso[idx - 1] || !insideLasso[idx + 1] || !insideLasso[idx - W] || !insideLasso[idx + W]) {
        boundaryIndices.push(idx);
      }
    }
  }

  const sampleStep = Math.max(1, Math.floor(boundaryIndices.length / 48));
  for (let i = 0; i < boundaryIndices.length; i += sampleStep) {
    const idx = boundaryIndices[i];
    const x = idx % W;
    const y = (idx / W) | 0;
    const p = idx * 4;
    bgSamples.push({ r: data[p], g: data[p + 1], b: data[p + 2], x, y });
  }

  const corners = [0, W - 1, (H - 1) * W, (H - 1) * W + W - 1];
  for (const idx of corners) {
    const p = idx * 4;
    bgSamples.push({ r: data[p], g: data[p + 1], b: data[p + 2], x: idx % W, y: (idx / W) | 0 });
  }

  function colorDist(r1: number, g1: number, b1: number, r2: number, g2: number, b2: number): number {
    const dr = r1 - r2;
    const dg = g1 - g2;
    const db = b1 - b2;
    const rmean = (r1 + r2) * 0.5;
    return Math.sqrt((2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db) * 0.55;
  }

  function minBgDist(r: number, g: number, b: number, x: number, y: number): number {
    let best = 9999;
    for (let i = 0; i < bgSamples.length; i++) {
      const s = bgSamples[i];
      const spatialPenalty = (Math.abs(x - s.x) + Math.abs(y - s.y)) / (W + H) * 18;
      const d = colorDist(r, g, b, s.r, s.g, s.b) + spatialPenalty;
      if (d < best) best = d;
    }
    return best;
  }

  const fgSamples: ColorSample[] = [];
  const cx = (minX + maxX) * 0.5;
  const cy = (minY + maxY) * 0.5;
  const rx = Math.max(8, (maxX - minX) * 0.28);
  const ry = Math.max(8, (maxY - minY) * 0.28);
  const fgStep = Math.max(2, Math.round(Math.min(rx, ry) / 6));
  for (let y = Math.max(0, Math.round(cy - ry)); y <= Math.min(H - 1, Math.round(cy + ry)); y += fgStep) {
    for (let x = Math.max(0, Math.round(cx - rx)); x <= Math.min(W - 1, Math.round(cx + rx)); x += fgStep) {
      const idx = y * W + x;
      if (!insideLasso[idx]) continue;
      const p = idx * 4;
      const r = data[p], g = data[p + 1], b = data[p + 2];
      if (minBgDist(r, g, b, x, y) > 26) {
        fgSamples.push({ r, g, b, x, y });
      }
    }
  }

  function minFgDist(r: number, g: number, b: number): number {
    if (fgSamples.length === 0) return 80;
    let best = 9999;
    for (let i = 0; i < fgSamples.length; i++) {
      const s = fgSamples[i];
      const d = colorDist(r, g, b, s.r, s.g, s.b);
      if (d < best) best = d;
    }
    return best;
  }

  const isBg = new Uint8Array(N);
  const queue = new Int32Array(N);
  let qHead = 0, qTail = 0;

  for (let i = 0; i < N; i++) {
    if (!insideLasso[i]) isBg[i] = 1;
  }
  for (const idx of boundaryIndices) {
    const x = idx % W;
    const y = (idx / W) | 0;
    const p = idx * 4;
    const dBg = minBgDist(data[p], data[p + 1], data[p + 2], x, y);
    if (dBg < sensitivity * 1.15) {
      isBg[idx] = 1;
      queue[qTail++] = idx;
    }
  }

  const bgThreshold = sensitivity;
  const stepThreshold = Math.max(14, sensitivity * 0.48);
  const dirs = [-1, 1, -W, W, -W - 1, -W + 1, W - 1, W + 1];

  while (qHead < qTail) {
    const curr = queue[qHead++];
    const cp = curr * 4;
    const cr = data[cp], cg = data[cp + 1], cb = data[cp + 2];

    for (let d = 0; d < 8; d++) {
      const nxt = curr + dirs[d];
      if (nxt < 0 || nxt >= N || isBg[nxt] || !insideLasso[nxt]) continue;
      const nx = nxt % W;
      const ny = (nxt / W) | 0;
      if (Math.abs(nx - (curr % W)) > 1) continue;

      const np = nxt * 4;
      const nr = data[np], ng = data[np + 1], nb = data[np + 2];

      const stepDist = colorDist(cr, cg, cb, nr, ng, nb);
      if (stepDist > stepThreshold) continue;

      const dBg = minBgDist(nr, ng, nb, nx, ny);
      const dFg = minFgDist(nr, ng, nb);
      if (dBg <= bgThreshold && dBg <= dFg * 1.15) {
        isBg[nxt] = 1;
        queue[qTail++] = nxt;
      }
    }
  }

  const fgMask = new Uint8Array(N);
  for (let i = 0; i < N; i++) fgMask[i] = isBg[i] ? 0 : 1;

  const tempMask = new Uint8Array(N);
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const i = y * W + x;
      tempMask[i] = (fgMask[i] || fgMask[i - 1] || fgMask[i + 1] || fgMask[i - W] || fgMask[i + W]) ? 1 : 0;
    }
  }
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const i = y * W + x;
      fgMask[i] = (tempMask[i] && tempMask[i - 1] && tempMask[i + 1] && tempMask[i - W] && tempMask[i + W]) ? 1 : 0;
    }
  }

  const extVisited = new Uint8Array(N);
  qHead = 0; qTail = 0;
  for (let x = 0; x < W; x++) {
    extVisited[x] = 1; queue[qTail++] = x;
    const b = (H - 1) * W + x;
    extVisited[b] = 1; queue[qTail++] = b;
  }
  for (let y = 1; y < H - 1; y++) {
    const l = y * W; extVisited[l] = 1; queue[qTail++] = l;
    const r = y * W + W - 1; extVisited[r] = 1; queue[qTail++] = r;
  }
  while (qHead < qTail) {
    const curr = queue[qHead++];
    const nbs = [curr - 1, curr + 1, curr - W, curr + W];
    for (let k = 0; k < 4; k++) {
      const nb = nbs[k];
      if (nb >= 0 && nb < N && !extVisited[nb] && !fgMask[nb]) {
        extVisited[nb] = 1;
        queue[qTail++] = nb;
      }
    }
  }
  for (let i = 0; i < N; i++) {
    if (!extVisited[i]) fgMask[i] = 1;
  }

  const compId = new Int32Array(N);
  const compSizes: number[] = [0];
  let currentComp = 0;
  let maxCompSize = 0;
  for (let i = 0; i < N; i++) {
    if (fgMask[i] && !compId[i]) {
      currentComp++;
      let size = 0;
      qHead = 0; qTail = 0;
      compId[i] = currentComp;
      queue[qTail++] = i;
      while (qHead < qTail) {
        const c = queue[qHead++];
        size++;
        const nbs = [c - 1, c + 1, c - W, c + W];
        for (let k = 0; k < 4; k++) {
          const nb = nbs[k];
          if (nb >= 0 && nb < N && fgMask[nb] && !compId[nb]) {
            compId[nb] = currentComp;
            queue[qTail++] = nb;
          }
        }
      }
      compSizes[currentComp] = size;
      if (size > maxCompSize) maxCompSize = size;
    }
  }
  for (let i = 0; i < N; i++) {
    if (fgMask[i] && compSizes[compId[i]] < maxCompSize * 0.08) {
      fgMask[i] = 0;
    }
  }

  const floatAlpha = new Float32Array(N);
  for (let i = 0; i < N; i++) floatAlpha[i] = fgMask[i] ? 255 : 0;

  const blurH = new Float32Array(N);
  const blurV = new Float32Array(N);
  for (let y = 0; y < H; y++) {
    const row = y * W;
    for (let x = 0; x < W; x++) {
      const xm2 = Math.max(0, x - 2), xm1 = Math.max(0, x - 1), xp1 = Math.min(W - 1, x + 1), xp2 = Math.min(W - 1, x + 2);
      blurH[row + x] = (floatAlpha[row + xm2] + 4 * floatAlpha[row + xm1] + 6 * floatAlpha[row + x] + 4 * floatAlpha[row + xp1] + floatAlpha[row + xp2]) / 16;
    }
  }
  for (let y = 0; y < H; y++) {
    const ym2 = Math.max(0, y - 2) * W, ym1 = Math.max(0, y - 1) * W, y0 = y * W, yp1 = Math.min(H - 1, y + 1) * W, yp2 = Math.min(H - 1, y + 2) * W;
    for (let x = 0; x < W; x++) {
      const rawA = (blurH[ym2 + x] + 4 * blurH[ym1 + x] + 6 * blurH[y0 + x] + 4 * blurH[yp1 + x] + blurH[yp2 + x]) / 16;
      const norm = Math.max(0, Math.min(1, (rawA - 110) / 135));
      blurV[y0 + x] = norm * norm * (3 - 2 * norm);
    }
  }

  let bMinX = W, bMinY = H, bMaxX = 0, bMaxY = 0;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (blurV[y * W + x] > 0.15) {
        if (x < bMinX) bMinX = x;
        if (x > bMaxX) bMaxX = x;
        if (y < bMinY) bMinY = y;
        if (y > bMaxY) bMaxY = y;
      }
    }
  }
  if (bMaxX <= bMinX || bMaxY <= bMinY) {
    bMinX = 0; bMinY = 0; bMaxX = W - 1; bMaxY = H - 1;
  }

  const contourNorm: Pt[] = [];
  const pcx = (bMinX + bMaxX) * 0.5;
  const pcy = (bMinY + bMaxY) * 0.5;
  const maxR = Math.hypot(W, H);
  for (let a = 0; a < 48; a++) {
    const ang = (a / 48) * Math.PI * 2;
    const dx = Math.cos(ang);
    const dy = Math.sin(ang);
    let lastFgR = 12;
    for (let r = 4; r < maxR; r += 2) {
      const tx = Math.round(pcx + dx * r);
      const ty = Math.round(pcy + dy * r);
      if (tx < 0 || tx >= W || ty < 0 || ty >= H) break;
      if (blurV[ty * W + tx] > 0.35) lastFgR = r + 3;
    }
    contourNorm.push({
      x: Math.max(0.02, Math.min(0.98, (pcx + dx * lastFgR) / W)),
      y: Math.max(0.02, Math.min(0.98, (pcy + dy * lastFgR) / H)),
    });
  }

  const hiCutCanvas = document.createElement("canvas");
  hiCutCanvas.width = W;
  hiCutCanvas.height = H;
  const hctx = hiCutCanvas.getContext("2d")!;
  const cutImgData = hctx.createImageData(W, H);
  const cdata = cutImgData.data;

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const a = blurV[i];
      if (a <= 0.004) continue;
      const p = i * 4;
      let r = data[p], g = data[p + 1], b = data[p + 2];
      if (a < 0.92) {
        const ix = Math.max(0, Math.min(W - 1, Math.round(x + (pcx - x) * 0.08)));
        const iy = Math.max(0, Math.min(H - 1, Math.round(y + (pcy - y) * 0.08)));
        const ip = (iy * W + ix) * 4;
        if (blurV[iy * W + ix] > 0.9) {
          r = Math.round(r * a + data[ip] * (1 - a));
          g = Math.round(g * a + data[ip + 1] * (1 - a));
          b = Math.round(b * a + data[ip + 2] * (1 - a));
        }
      }
      cdata[p] = r;
      cdata[p + 1] = g;
      cdata[p + 2] = b;
      cdata[p + 3] = Math.round(a * 255);
    }
  }
  hctx.putImageData(cutImgData, 0, 0);

  const outSize = 600;
  const outCanvas = document.createElement("canvas");
  outCanvas.width = outSize;
  outCanvas.height = outSize;
  const octx = outCanvas.getContext("2d")!;

  octx.fillStyle = "#ffffff";
  octx.fillRect(0, 0, outSize, outSize);

  const bw = Math.max(16, bMaxX - bMinX + 1);
  const bh = Math.max(16, bMaxY - bMinY + 1);

  if (autoCenter) {
    const pad = Math.round(outSize * 0.08);
    const avail = outSize - pad * 2;
    const fitScale = Math.min(avail / bw, avail / bh);
    const dw = Math.round(bw * fitScale);
    const dh = Math.round(bh * fitScale);
    const dx = Math.round((outSize - dw) * 0.5);
    const dy = Math.round((outSize - dh) * 0.5);

    if (addShadow) {
      octx.save();
      octx.shadowColor = "rgba(15, 38, 26, 0.16)";
      octx.shadowBlur = 18;
      octx.shadowOffsetY = 8;
      octx.drawImage(hiCutCanvas, bMinX, bMinY, bw, bh, dx, dy, dw, dh);
      octx.restore();
    } else {
      octx.drawImage(hiCutCanvas, bMinX, bMinY, bw, bh, dx, dy, dw, dh);
    }
  } else {
    if (addShadow) {
      octx.save();
      octx.shadowColor = "rgba(15, 38, 26, 0.16)";
      octx.shadowBlur = 18;
      octx.shadowOffsetY = 8;
      octx.drawImage(hiCutCanvas, 0, 0, W, H, 0, 0, outSize, outSize);
      octx.restore();
    } else {
      octx.drawImage(hiCutCanvas, 0, 0, W, H, 0, 0, outSize, outSize);
    }
  }

  let outUrl = outCanvas.toDataURL("image/webp", 0.88);
  if (!outUrl.startsWith("data:image/webp")) {
    outUrl = outCanvas.toDataURL("image/jpeg", 0.9);
  }
  return { resultDataUrl: outUrl, contourNorm };
}

export default function ImageEditor({ aspect, title, format = "webp", initialSource, initialTool = "crop", onSave, onCancel }: Props) {
  const [source, setSource] = useState<string | null>(initialSource || null);
  const [originalBeforeCutout, setOriginalBeforeCutout] = useState<string | null>(initialSource || null);
  const [activeTool, setActiveTool] = useState<"crop" | "lasso">(initialTool);
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);
  const [cropMode, setCropMode] = useState<"free" | "aspect" | "full">("free");
  const [box, setBox] = useState<CropBox>({ x: 5, y: 5, w: 90, h: 90 });
  const [fitPadding, setFitPadding] = useState(false);

  const [lassoPoints, setLassoPoints] = useState<Pt[]>([]);
  const [lastLassoPoints, setLastLassoPoints] = useState<Pt[]>([]);
  const [snappedContour, setSnappedContour] = useState<Pt[]>([]);
  const [isDrawingLasso, setIsDrawingLasso] = useState(false);
  const [cutoutSensitivity, setCutoutSensitivity] = useState(46);
  const [addStudioShadow, setAddStudioShadow] = useState(true);
  const [autoCenterProduct, setAutoCenterProduct] = useState(true);
  const [cutoutApplied, setCutoutApplied] = useState(false);
  const [processingCutout, setProcessingCutout] = useState(false);

  const imgRef = useRef<HTMLImageElement | null>(null);
  const lassoContainerRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragRef = useRef<{
    kind: DragKind;
    startX: number;
    startY: number;
    startBox: CropBox;
    rectW: number;
    rectH: number;
  } | null>(null);

  useEffect(() => {
    if (!source) return;
    const im = new Image();
    im.crossOrigin = "anonymous";
    im.onload = () => {
      setImgSize({ w: im.naturalWidth || 600, h: im.naturalHeight || 600 });
      setBox({ x: 4, y: 4, w: 92, h: 92 });
    };
    im.onerror = () => {
      setImgSize({ w: 600, h: 600 });
    };
    im.src = source;
  }, [source]);

  const loadFile = (file?: File) => {
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const res = typeof reader.result === "string" ? reader.result : null;
      if (res) {
        setSource(res);
        setOriginalBeforeCutout(res);
        setCutoutApplied(false);
        setLassoPoints([]);
        setLastLassoPoints([]);
        setSnappedContour([]);
        setCropMode("free");
        setFitPadding(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const executeLassoCutout = (pointsToUse: Pt[], sens = cutoutSensitivity, shadow = addStudioShadow, center = autoCenterProduct) => {
    const baseSrc = originalBeforeCutout || source;
    if (!baseSrc) return;
    setProcessingCutout(true);
    const im = new Image();
    im.crossOrigin = "anonymous";
    im.onload = () => {
      try {
        const { resultDataUrl, contourNorm } = performSmartLassoCutout(im, pointsToUse, sens, shadow, center);
        setSnappedContour(contourNorm);
        setSource(resultDataUrl);
        setCutoutApplied(true);
        setBox({ x: 0, y: 0, w: 100, h: 100 });
        setFitPadding(true);
      } finally {
        setProcessingCutout(false);
      }
    };
    im.onerror = () => setProcessingCutout(false);
    im.src = baseSrc;
  };

  const handleLassoPointerDown = (e: React.PointerEvent) => {
    if (activeTool !== "lasso" || !lassoContainerRef.current) return;
    e.preventDefault();
    e.stopPropagation();
    if (cutoutApplied && originalBeforeCutout) {
      setSource(originalBeforeCutout);
      setCutoutApplied(false);
    }
    const rect = lassoContainerRef.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    setIsDrawingLasso(true);
    setSnappedContour([]);
    setLassoPoints([{ x, y }]);
  };

  const handleLassoPointerMove = (e: React.PointerEvent) => {
    if (!isDrawingLasso || !lassoContainerRef.current) return;
    e.preventDefault();
    e.stopPropagation();
    const rect = lassoContainerRef.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    setLassoPoints(prev => {
      const last = prev[prev.length - 1];
      if (last && Math.hypot(x - last.x, y - last.y) < 0.012) return prev;
      return [...prev, { x, y }];
    });
  };

  const handleLassoPointerUp = (e: React.PointerEvent) => {
    if (!isDrawingLasso) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDrawingLasso(false);
    if (lassoPoints.length >= 5) {
      setLastLassoPoints(lassoPoints);
      executeLassoCutout(lassoPoints, cutoutSensitivity, addStudioShadow, autoCenterProduct);
    } else {
      setLassoPoints([]);
    }
  };

  const applyMode = (mode: "free" | "aspect" | "full") => {
    setActiveTool("crop");
    setCropMode(mode);
    if (mode === "full") {
      setBox({ x: 0, y: 0, w: 100, h: 100 });
      setFitPadding(true);
      return;
    }
    setFitPadding(false);
    if (mode === "aspect" && imgSize) {
      const imgRatio = imgSize.w / imgSize.h;
      const targetRatio = aspect || 1;
      let wPct = 86;
      let hPct = 86;
      if (imgRatio > targetRatio) {
        hPct = 88;
        wPct = Math.min(96, Math.round((hPct * targetRatio) / imgRatio));
      } else {
        wPct = 88;
        hPct = Math.min(96, Math.round((wPct * imgRatio) / targetRatio));
      }
      setBox({
        x: Math.round((100 - wPct) / 2),
        y: Math.round((100 - hPct) / 2),
        w: wPct,
        h: hPct,
      });
    } else {
      setBox({ x: 6, y: 6, w: 88, h: 88 });
    }
  };

  const rotate90 = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!source) return;
    const im = new Image();
    im.crossOrigin = "anonymous";
    im.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = im.naturalHeight;
      canvas.height = im.naturalWidth;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate(Math.PI / 2);
      ctx.drawImage(im, -im.naturalWidth / 2, -im.naturalHeight / 2);
      const rotated = canvas.toDataURL("image/webp", 0.9);
      setSource(rotated);
      setOriginalBeforeCutout(rotated);
      setBox({ x: 5, y: 5, w: 90, h: 90 });
    };
    im.src = source;
  };

  const startHandleDrag = (kind: DragKind, e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = {
      kind,
      startX: e.clientX,
      startY: e.clientY,
      startBox: { ...box },
      rectW: rect.width,
      rectH: rect.height,
    };
  };

  const moveHandleDrag = (e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    e.preventDefault();
    e.stopPropagation();
    const dx = ((e.clientX - d.startX) / d.rectW) * 100;
    const dy = ((e.clientY - d.startY) / d.rectH) * 100;
    const minSize = 12;
    let { x, y, w, h } = d.startBox;

    if (d.kind === "move") {
      x = Math.max(0, Math.min(100 - w, x + dx));
      y = Math.max(0, Math.min(100 - h, y + dy));
      setBox({ x, y, w, h });
      return;
    }

    if (d.kind.includes("e")) w = Math.max(minSize, Math.min(100 - x, d.startBox.w + dx));
    if (d.kind.includes("s")) h = Math.max(minSize, Math.min(100 - y, d.startBox.h + dy));
    if (d.kind.includes("w")) {
      const maxLeftShift = d.startBox.x;
      const maxShrink = d.startBox.w - minSize;
      const shift = Math.max(-maxLeftShift, Math.min(maxShrink, dx));
      x = d.startBox.x + shift;
      w = d.startBox.w - shift;
    }
    if (d.kind.includes("n")) {
      const maxTopShift = d.startBox.y;
      const maxShrink = d.startBox.h - minSize;
      const shift = Math.max(-maxTopShift, Math.min(maxShrink, dy));
      y = d.startBox.y + shift;
      h = d.startBox.h - shift;
    }

    if (cropMode === "aspect" && imgSize) {
      const imgRatio = imgSize.w / imgSize.h;
      const targetRatio = aspect || 1;
      const desiredH = (w * imgRatio) / targetRatio;
      if (y + desiredH <= 100 && desiredH >= minSize) {
        h = desiredH;
      } else {
        h = Math.max(minSize, Math.min(100 - y, h));
        w = Math.max(minSize, Math.min(100 - x, (h * targetRatio) / imgRatio));
      }
    }

    setBox({ x, y, w, h });
  };

  const endHandleDrag = (e: React.PointerEvent) => {
    if (dragRef.current) {
      e.preventDefault();
      e.stopPropagation();
      dragRef.current = null;
    }
  };

  const handleSave = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!source) return;
    if (cutoutApplied && activeTool === "lasso") {
      onSave(source);
      return;
    }
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      const natW = image.naturalWidth || 600;
      const natH = image.naturalHeight || 600;
      const sx = Math.max(0, Math.round((box.x / 100) * natW));
      const sy = Math.max(0, Math.round((box.y / 100) * natH));
      const sw = Math.max(16, Math.min(natW - sx, Math.round((box.w / 100) * natW)));
      const sh = Math.max(16, Math.min(natH - sy, Math.round((box.h / 100) * natH)));

      const maxDim = aspect > 2 ? 840 : 540;
      let outW = maxDim;
      let outH = Math.round(maxDim / (aspect || 1));

      if (fitPadding || cropMode === "free") {
        const cropRatio = sw / sh;
        if (cropRatio >= 1) {
          outW = maxDim;
          outH = Math.max(180, Math.round(maxDim / cropRatio));
        } else {
          outH = maxDim;
          outW = Math.max(180, Math.round(maxDim * cropRatio));
        }
      }

      const canvas = document.createElement("canvas");
      canvas.width = outW;
      canvas.height = outH;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(image, sx, sy, sw, sh, 0, 0, outW, outH);

      const mime = format === "png" ? "image/png" : "image/webp";
      let data = canvas.toDataURL(mime, 0.8);
      if (!data.startsWith("data:" + mime)) {
        data = canvas.toDataURL("image/jpeg", 0.85);
      }
      onSave(data);
    };
    image.src = source;
  };

  const handleStyle = (pos: React.CSSProperties): React.CSSProperties => ({
    position: "absolute",
    width: "26px",
    height: "26px",
    borderRadius: "50%",
    background: "#f1d897",
    border: "2.5px solid #0f5c3a",
    boxShadow: "0 2px 6px rgba(0,0,0,0.35)",
    zIndex: 5,
    touchAction: "none",
    ...pos,
  });

  const activePolyPoints = isDrawingLasso ? lassoPoints : (!cutoutApplied && snappedContour.length > 0 ? snappedContour : lassoPoints);
  const svgPolyString = activePolyPoints.map(p => (p.x * 100).toFixed(2) + "," + (p.y * 100).toFixed(2)).join(" ");

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={e => e.stopPropagation()}
      onMouseDown={event => {
        if (event.target === event.currentTarget) onCancel();
      }}
      style={{ zIndex: 210 }}
    >
      <section
        className="image-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby="image-editor-title"
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">استوديو تجهيز وعزل خلفية المنتج (0 توكنز)</span>
            <h2 id="image-editor-title">{title}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={e => {
              e.preventDefault();
              e.stopPropagation();
              onCancel();
            }}
            aria-label="إغلاق"
          >
            <X size={19} />
          </button>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={event => {
            loadFile(event.currentTarget.files?.[0]);
            event.currentTarget.value = "";
          }}
        />

        {!source ? (
          <div
            className="file-drop"
            onClick={e => {
              e.preventDefault();
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            <ImagePlus size={30} strokeWidth={1.7} />
            <strong>اختر صورة من جهازك</strong>
            <span>PNG أو JPG أو WEBP · قص حر أو عزل الخلفية بالرسم الذكي</span>
          </div>
        ) : (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
              <button
                type="button"
                className={"small-button " + (activeTool === "lasso" ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  setActiveTool("lasso");
                }}
                style={{
                  background: activeTool === "lasso" ? "#174b36" : "#f2f8f4",
                  color: activeTool === "lasso" ? "#f1d897" : "#174b36",
                  border: "1.5px solid #174b36",
                  fontWeight: 900,
                }}
              >
                <Wand2 size={14} /> 🪄 عزل الخلفية بالرسم الذكي (خلفية بيضاء)
              </button>
              <button
                type="button"
                className={"small-button " + (activeTool === "crop" && cropMode === "free" && !fitPadding ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  applyMode("free");
                }}
              >
                <Crop size={14} /> قص حر
              </button>
              <button
                type="button"
                className={"small-button " + (activeTool === "crop" && cropMode === "aspect" && !fitPadding ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  applyMode("aspect");
                }}
              >
                <Square size={14} /> إطار متناسق
              </button>
              <button
                type="button"
                className={"small-button " + (activeTool === "crop" && fitPadding ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  applyMode("full");
                }}
              >
                <Maximize2 size={14} /> كامل الصورة
              </button>
              <button type="button" className="small-button" onClick={rotate90}>
                <RotateCw size={14} /> تدوير 90°
              </button>
            </div>

            {activeTool === "lasso" && (
              <div style={{ marginBottom: "10px", padding: "10px 12px", borderRadius: "12px", background: "#f2f8f4", border: "1px solid #cce0d3", display: "grid", gap: "8px" }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "12px", fontWeight: 800, color: "#144530" }}>
                    ✍️ ارسم بإصبعك دائرة أو خطاً منقطاً حول المنتج لقص ما حوله فوراً وجعل الخلفية بيضاء:
                  </span>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="small-button selected"
                      disabled={processingCutout}
                      onClick={() => {
                        const autoLoop: Pt[] = [];
                        for (let i = 0; i < 36; i++) {
                          const a = (i / 36) * Math.PI * 2;
                          autoLoop.push({ x: 0.5 + Math.cos(a) * 0.44, y: 0.5 + Math.sin(a) * 0.44 });
                        }
                        setLastLassoPoints(autoLoop);
                        executeLassoCutout(autoLoop, cutoutSensitivity, addStudioShadow, autoCenterProduct);
                      }}
                    >
                      {processingCutout ? <LoaderCircle size={13} className="spin" /> : <Sparkles size={13} />}
                      ⚡ عزل تلقائي فوري بدون رسم
                    </button>
                    {cutoutApplied && originalBeforeCutout && (
                      <button
                        type="button"
                        className="small-button"
                        onClick={() => {
                          setSource(originalBeforeCutout);
                          setCutoutApplied(false);
                          setLassoPoints([]);
                          setSnappedContour([]);
                        }}
                      >
                        <RotateCcw size={13} /> إرجاع الصورة الأصلية وإعادة الرسم
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center", justifyContent: "space-between" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "200px", fontSize: "11px", fontWeight: 800, color: "#174b36" }}>
                    <span>حساسية التعرف على حواف المنتج ({cutoutSensitivity}%):</span>
                    <input
                      type="range"
                      min="18"
                      max="82"
                      value={cutoutSensitivity}
                      onChange={e => {
                        const val = Number(e.target.value);
                        setCutoutSensitivity(val);
                        if (cutoutApplied || lastLassoPoints.length >= 3) {
                          executeLassoCutout(lastLassoPoints, val, addStudioShadow, autoCenterProduct);
                        }
                      }}
                      style={{ flex: 1 }}
                    />
                  </label>
                  <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", fontSize: "11px", fontWeight: 700, color: "#174b36" }}>
                    <label style={{ display: "inline-flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={addStudioShadow}
                        onChange={e => {
                          const v = e.target.checked;
                          setAddStudioShadow(v);
                          if (cutoutApplied) executeLassoCutout(lastLassoPoints, cutoutSensitivity, v, autoCenterProduct);
                        }}
                      />
                      ظل استوديو ناعم
                    </label>
                    <label style={{ display: "inline-flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={autoCenterProduct}
                        onChange={e => {
                          const v = e.target.checked;
                          setAutoCenterProduct(v);
                          if (cutoutApplied) executeLassoCutout(lastLassoPoints, cutoutSensitivity, addStudioShadow, v);
                        }}
                      />
                      توسيط المنتج في المربع الأبيض
                    </label>
                  </div>
                </div>
              </div>
            )}

            <div
              style={{
                background: cutoutApplied && activeTool === "lasso" ? "#ffffff" : "#122119",
                border: cutoutApplied && activeTool === "lasso" ? "2px solid #d4e2d9" : "none",
                borderRadius: "14px",
                padding: "14px",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                overflow: "hidden",
                userSelect: "none",
                touchAction: "none",
              }}
            >
              <div
                ref={lassoContainerRef}
                style={{
                  position: "relative",
                  display: "inline-block",
                  maxWidth: "100%",
                  maxHeight: "48vh",
                  lineHeight: 0,
                  touchAction: "none",
                  cursor: activeTool === "lasso" ? "crosshair" : "default",
                }}
                onPointerDown={activeTool === "lasso" ? handleLassoPointerDown : undefined}
                onPointerMove={activeTool === "lasso" ? handleLassoPointerMove : moveHandleDrag}
                onPointerUp={activeTool === "lasso" ? handleLassoPointerUp : endHandleDrag}
                onPointerCancel={activeTool === "lasso" ? handleLassoPointerUp : endHandleDrag}
              >
                <img
                  ref={imgRef}
                  src={source}
                  alt="معاينة الصورة"
                  draggable={false}
                  style={{
                    display: "block",
                    maxWidth: "100%",
                    maxHeight: "48vh",
                    width: "auto",
                    height: "auto",
                    borderRadius: "8px",
                    pointerEvents: "none",
                    userSelect: "none",
                  }}
                />

                {activeTool === "lasso" && activePolyPoints.length >= 2 && (
                  <svg
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                    style={{
                      position: "absolute",
                      inset: 0,
                      width: "100%",
                      height: "100%",
                      pointerEvents: "none",
                      overflow: "visible",
                    }}
                  >
                    <polygon
                      points={svgPolyString}
                      fill="rgba(241, 216, 151, 0.14)"
                      stroke="#174b36"
                      strokeWidth="1.2"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    />
                    <polygon
                      points={svgPolyString}
                      fill="none"
                      stroke="#f1d897"
                      strokeWidth="2.6"
                      strokeDasharray="6 5"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                    >
                      <animate attributeName="stroke-dashoffset" from="22" to="0" dur="0.7s" repeatCount="indefinite" />
                    </polygon>
                  </svg>
                )}

                {activeTool === "crop" && (
                  <div
                    onPointerDown={e => startHandleDrag("move", e)}
                    style={{
                      position: "absolute",
                      left: box.x + "%",
                      top: box.y + "%",
                      width: box.w + "%",
                      height: box.h + "%",
                      border: "2.5px solid #f1d897",
                      boxShadow: "0 0 0 9999px rgba(8, 18, 13, 0.62)",
                      cursor: "move",
                      touchAction: "none",
                      boxSizing: "border-box",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr 1fr",
                        gridTemplateRows: "1fr 1fr 1fr",
                        pointerEvents: "none",
                      }}
                    >
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)", display: "grid", placeItems: "center" }}>
                        <Move size={16} color="rgba(255,255,255,0.85)" />
                      </i>
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                      <i style={{ border: "0.5px dashed rgba(255,255,255,0.4)" }} />
                    </div>

                    <span onPointerDown={e => startHandleDrag("nw", e)} style={handleStyle({ top: "-13px", left: "-13px", cursor: "nwse-resize" })} />
                    <span onPointerDown={e => startHandleDrag("ne", e)} style={handleStyle({ top: "-13px", right: "-13px", cursor: "nesw-resize" })} />
                    <span onPointerDown={e => startHandleDrag("sw", e)} style={handleStyle({ bottom: "-13px", left: "-13px", cursor: "nesw-resize" })} />
                    <span onPointerDown={e => startHandleDrag("se", e)} style={handleStyle({ bottom: "-13px", right: "-13px", cursor: "nwse-resize" })} />
                    <span onPointerDown={e => startHandleDrag("n", e)} style={handleStyle({ top: "-11px", left: "calc(50% - 11px)", width: "22px", height: "22px", cursor: "ns-resize" })} />
                    <span onPointerDown={e => startHandleDrag("s", e)} style={handleStyle({ bottom: "-11px", left: "calc(50% - 11px)", width: "22px", height: "22px", cursor: "ns-resize" })} />
                    <span onPointerDown={e => startHandleDrag("w", e)} style={handleStyle({ left: "-11px", top: "calc(50% - 11px)", width: "22px", height: "22px", cursor: "ew-resize" })} />
                    <span onPointerDown={e => startHandleDrag("e", e)} style={handleStyle({ right: "-11px", top: "calc(50% - 11px)", width: "22px", height: "22px", cursor: "ew-resize" })} />
                  </div>
                )}
              </div>
            </div>

            <p className="subtle-note" style={{ margin: "8px 0 4px", textAlign: "center" }}>
              {activeTool === "lasso"
                ? (cutoutApplied
                    ? "✅ تم عزل المنتج على خلفية بيضاء ناعمة! يمكنك تحريك شريط الحساسية أعلاه لضبط الحواف أو الرسم مرة أخرى."
                    : "ارسم بإصبعك دائرة أو خطاً منقطاً حول المنتج وسيقوم النظام بالتعرف على أطرافه وعزل الخلفية إلى اللون الأبيض فوراً.")
                : "اسحب وسط الإطار لتحريكه إلى المكان الذي تريده، أو اسحب الدوائر الصفراء في الزوايا لتكبير وتصغير منطقة القص بحرية."}
            </p>

            <div className="modal-footer" style={{ marginTop: "10px", display: "flex", gap: "8px", justifyContent: "space-between", flexWrap: "wrap" }}>
              <button
                type="button"
                className="button button-quiet"
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                <ImagePlus size={15} /> اختيار صورة أخرى
              </button>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={e => {
                    e.preventDefault();
                    e.stopPropagation();
                    onCancel();
                  }}
                >
                  إلغاء
                </button>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={handleSave}
                >
                  <Check size={16} /> {cutoutApplied ? "اعتماد الصورة بالخلفية البيضاء" : "اعتماد وحفظ الصورة"}
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}