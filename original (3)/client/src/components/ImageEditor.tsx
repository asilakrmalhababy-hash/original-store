import { useRef, useState } from "react";
import { ImagePlus, Move, Scan, Sparkles, X } from "lucide-react";

type Props = { aspect: number; title: string; format?: "webp" | "png"; onSave: (dataUrl: string) => void; onCancel: () => void };
type Point = { x: number; y: number };

export default function ImageEditor({ aspect, title, format = "webp", onSave, onCancel }: Props) {
  const [source, setSource] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [blurMode, setBlurMode] = useState(false);
  const [blurRect, setBlurRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const dragStart = useRef<Point | null>(null);
  const initialOffset = useRef<Point>({ x: 0, y: 0 });
  const stageRef = useRef<HTMLDivElement>(null);

  const loadFile = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : null;
      if (!result) return;
      const image = new Image();
      image.onload = () => { setImageSize({ width: image.naturalWidth, height: image.naturalHeight }); setSource(result); setZoom(1); setOffset({ x: 0, y: 0 }); setBlurRect(null); };
      image.src = result;
    };
    reader.readAsDataURL(file);
  };

  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!source) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const bounds = event.currentTarget.getBoundingClientRect();
    const start = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    dragStart.current = start;
    initialOffset.current = offset;
    setDragging(true);
    if (blurMode) setBlurRect({ x: start.x, y: start.y, w: 0, h: 0 });
  };

  const moveDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging || !dragStart.current || !stageRef.current) return;
    const bounds = stageRef.current.getBoundingClientRect();
    const current = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    if (blurMode) {
      const start = dragStart.current;
      setBlurRect({ x: Math.min(start.x, current.x), y: Math.min(start.y, current.y), w: Math.abs(current.x - start.x), h: Math.abs(current.y - start.y) });
    } else {
      const maxX = bounds.width * (zoom - 1) / 2 + 2;
      const maxY = bounds.height * (zoom - 1) / 2 + 2;
      setOffset({
        x: Math.max(-maxX, Math.min(maxX, initialOffset.current.x + event.clientX - (bounds.left + dragStart.current.x))),
        y: Math.max(-maxY, Math.min(maxY, initialOffset.current.y + event.clientY - (bounds.top + dragStart.current.y))),
      });
    }
  };

  const save = () => {
    if (!source || !imageSize || !stageRef.current) return;
    const stage = stageRef.current.getBoundingClientRect();
    const outW = aspect > 2 ? 1440 : 900;
    const outH = Math.round(outW / aspect);
    const canvas = document.createElement("canvas");
    canvas.width = outW; canvas.height = outH;
    const context = canvas.getContext("2d");
    if (!context) return;
    const stageW = stage.width; const stageH = stage.height;
    const imageRatio = imageSize.width / imageSize.height;
    const baseW = imageRatio > aspect ? stageH * imageRatio : stageW;
    const baseH = imageRatio > aspect ? stageH : stageW / imageRatio;
    const drawW = baseW * zoom; const drawH = baseH * zoom;
    const scale = outW / stageW;
    const x = (stageW - drawW) / 2 + offset.x;
    const y = (stageH - drawH) / 2 + offset.y;
    const image = new Image();
    image.onload = () => {
      context.drawImage(image, x * scale, y * scale, drawW * scale, drawH * scale);
      if (blurRect && blurRect.w >= 8 && blurRect.h >= 8) {
        const rx = Math.max(0, Math.round(blurRect.x * scale));
        const ry = Math.max(0, Math.round(blurRect.y * scale));
        const rw = Math.min(outW - rx, Math.round(blurRect.w * scale));
        const rh = Math.min(outH - ry, Math.round(blurRect.h * scale));
        if (rw > 0 && rh > 0) {
          const patch = document.createElement("canvas"); patch.width = rw; patch.height = rh;
          const patchContext = patch.getContext("2d");
          if (patchContext) { patchContext.filter = `blur(${Math.max(10, Math.min(26, outW / 60))}px)`; patchContext.drawImage(canvas, rx, ry, rw, rh, 0, 0, rw, rh); context.drawImage(patch, rx, ry); }
        }
      }
      let data = canvas.toDataURL(format === "png" ? "image/png" : "image/webp", 0.76);
      if (!data.startsWith(format === "png" ? "data:image/png" : "data:image/webp")) data = canvas.toDataURL("image/png");
      onSave(data);
    };
    image.src = source;
  };

  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onCancel(); }}>
    <section className="image-editor" role="dialog" aria-modal="true" aria-labelledby="image-editor-title">
      <div className="modal-heading">
        <div><span className="eyebrow">تجهيز الصورة</span><h2 id="image-editor-title">{title}</h2></div>
        <button className="icon-button" onClick={onCancel} aria-label="إغلاق"><X size={19} /></button>
      </div>
      {!source ? <label className="file-drop">
        <ImagePlus size={28} strokeWidth={1.7} />
        <strong>اختر صورة من جهازك</strong>
        <span>PNG أو JPG أو WEBP · سنجهزها بالمقاس المناسب</span>
        <input type="file" accept="image/*" onChange={event => loadFile(event.currentTarget.files?.[0])} />
      </label> : <>
        <div className="crop-stage-wrap">
          <div className={`crop-stage ${blurMode ? "is-blur" : ""}`} ref={stageRef} style={{ aspectRatio: String(aspect) }} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={() => setDragging(false)} onPointerCancel={() => setDragging(false)}>
            <img className="crop-image" src={source} alt="معاينة الصورة التي اخترتها" draggable={false} style={{ width: `${Math.max(100, aspect >= imageSize!.width / imageSize!.height ? 100 : (imageSize!.width / imageSize!.height / aspect) * 100) * zoom}%`, height: "auto", transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px))` }} />
            <div className="crop-grid"><i /><i /><i /><i /></div>
            {blurRect && <div className="blur-selection" style={{ left: blurRect.x, top: blurRect.y, width: blurRect.w, height: blurRect.h }} />}
          </div>
          <div className="crop-actions">
            <span className="helper"><Move size={15} /> اسحب لتحريك الصورة</span>
            <button className={`small-button ${blurMode ? "selected" : ""}`} onClick={() => setBlurMode(value => !value)}><Scan size={15} /> {blurMode ? "أغلق أداة الطمس" : "طمس جزء"}</button>
          </div>
          {blurMode && <p className="subtle-note">اسحب مستطيلًا فوق الجزء الذي تريد طمسه.</p>}
          <label className="zoom-row"><span>تكبير</span><input type="range" min="1" max="3" step="0.01" value={zoom} onChange={event => setZoom(Number(event.target.value))} /><span>{zoom.toFixed(1)}×</span></label>
        </div>
        <div className="modal-footer"><button className="button button-quiet" onClick={() => { setSource(null); setImageSize(null); }}>تغيير الصورة</button><button className="button button-primary" onClick={save}><Sparkles size={16} /> اعتماد القص</button></div>
      </>}
    </section>
  </div>;
}
