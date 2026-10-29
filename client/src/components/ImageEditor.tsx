import { useEffect, useRef, useState } from "react";
import { Check, Crop, ImagePlus, Maximize2, Move, RotateCw, Square, X } from "lucide-react";

type Props = {
  aspect: number;
  title: string;
  format?: "webp" | "png";
  initialSource?: string;
  onSave: (dataUrl: string) => void;
  onCancel: () => void;
};

type CropBox = { x: number; y: number; w: number; h: number };
type DragKind = "move" | "nw" | "ne" | "sw" | "se" | "n" | "s" | "e" | "w";

export default function ImageEditor({ aspect, title, format = "webp", initialSource, onSave, onCancel }: Props) {
  const [source, setSource] = useState<string | null>(initialSource || null);
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);
  const [cropMode, setCropMode] = useState<"free" | "aspect" | "full">("free");
  const [box, setBox] = useState<CropBox>({ x: 5, y: 5, w: 90, h: 90 });
  const [fitPadding, setFitPadding] = useState(false);

  const imgRef = useRef<HTMLImageElement | null>(null);
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
        setCropMode("free");
        setFitPadding(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const applyMode = (mode: "free" | "aspect" | "full") => {
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
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      const natW = image.naturalWidth || 600;
      const natH = image.naturalHeight || 600;
      const sx = Math.max(0, Math.round((box.x / 100) * natW));
      const sy = Math.max(0, Math.round((box.y / 100) * natH));
      const sw = Math.max(16, Math.min(natW - sx, Math.round((box.w / 100) * natW)));
      const sh = Math.max(16, Math.min(natH - sy, Math.round((box.h / 100) * natH)));

      const maxDim = aspect > 2 ? 840 : 480;
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
      let data = canvas.toDataURL(mime, 0.78);
      if (!data.startsWith("data:" + mime)) {
        data = canvas.toDataURL("image/jpeg", 0.82);
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

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={e => e.stopPropagation()}
      onMouseDown={event => {
        if (event.target === event.currentTarget) onCancel();
      }}
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
            <span className="eyebrow">تجهيز وقص الصورة بحرية</span>
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
            <span>PNG أو JPG أو WEBP · حدد المكان الذي تريد قصه بحرية تامة</span>
          </div>
        ) : (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
              <button
                type="button"
                className={"small-button " + (cropMode === "free" && !fitPadding ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  applyMode("free");
                }}
              >
                <Crop size={14} /> قص حر (اختر أي مكان)
              </button>
              <button
                type="button"
                className={"small-button " + (cropMode === "aspect" && !fitPadding ? "selected" : "")}
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
                className={"small-button " + (fitPadding ? "selected" : "")}
                onClick={e => {
                  e.preventDefault();
                  e.stopPropagation();
                  applyMode("full");
                }}
              >
                <Maximize2 size={14} /> كامل الصورة بدون قص
              </button>
              <button type="button" className="small-button" onClick={rotate90}>
                <RotateCw size={14} /> تدوير 90°
              </button>
            </div>

            <div
              style={{
                background: "#122119",
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
                style={{
                  position: "relative",
                  display: "inline-block",
                  maxWidth: "100%",
                  maxHeight: "48vh",
                  lineHeight: 0,
                  touchAction: "none",
                }}
                onPointerMove={moveHandleDrag}
                onPointerUp={endHandleDrag}
                onPointerCancel={endHandleDrag}
              >
                <img
                  ref={imgRef}
                  src={source}
                  alt="معاينة القص"
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
              </div>
            </div>

            <p className="subtle-note" style={{ margin: "8px 0 4px", textAlign: "center" }}>
              اسحب وسط الإطار لتحريكه إلى المكان الذي تريده، أو اسحب الدوائر الصفراء في الزوايا لتكبير وتصغير منطقة القص بحرية.
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
                  <Check size={16} /> اعتماد القص
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}