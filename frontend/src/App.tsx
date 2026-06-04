import { useEffect, useMemo, useRef, useState } from "react";
import { autofillStream, type DetectedText, type FillItem, type StreamEvent } from "./api";

interface Row {
  key: string;
  value: string;
}

const DEFAULT_PROFILE: Row[] = [
  { key: "full name", value: "王小明" },
  { key: "email", value: "ming@example.com" },
  { key: "phone", value: "0912345678" },
  { key: "address", value: "台北市信義路100號" },
];

function mmss(sec: number) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** 打字機效果：逐字顯示 value。 */
function Typed({ value }: { value: string }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0);
    const id = setInterval(() => setN((x) => (x >= value.length ? x : x + 1)), 45);
    return () => clearInterval(id);
  }, [value]);
  return <>{value.slice(0, n)}</>;
}

export default function App() {
  const [rows, setRows] = useState<Row[]>(DEFAULT_PROFILE);
  const [showProfile, setShowProfile] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [imgUrl, setImgUrl] = useState("");

  const [running, setRunning] = useState(false);
  const [meta, setMeta] = useState<StreamEvent & { event: "meta" } | null>(null);
  const [texts, setTexts] = useState<DetectedText[]>([]);
  const [filled, setFilled] = useState<FillItem[]>([]);
  const [locating, setLocating] = useState<{ index: number; label: string } | null>(null);
  const [thinking, setThinking] = useState("");
  const [tokens, setTokens] = useState({ in: 0, out: 0 });
  const [phase, setPhase] = useState("待命");
  const [turn, setTurn] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");

  const imgRef = useRef<HTMLImageElement>(null);
  const [dispW, setDispW] = useState(0);
  const thinkRef = useRef<HTMLDivElement>(null);
  const startRef = useRef(0);

  const scale = useMemo(
    () => (meta && dispW ? dispW / meta.image_width : 1),
    [meta, dispW]
  );

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (thinkRef.current) thinkRef.current.scrollTop = thinkRef.current.scrollHeight;
  }, [thinking]);

  function onPick(f: File | null) {
    setFile(f);
    setTexts([]);
    setFilled([]);
    setLocating(null);
    setThinking("");
    setMeta(null);
    setError("");
    if (f) setImgUrl(URL.createObjectURL(f));
  }

  // 目前正在定位的欄位 → 對應到偵測到的標籤框，做藍色高亮
  const locatingBox = useMemo(() => {
    if (!locating) return null;
    const lab = locating.label.toLowerCase();
    return (
      texts.find((t) => lab.includes(t.text.toLowerCase()) || t.text.toLowerCase().includes(lab)) ??
      null
    );
  }, [locating, texts]);

  function handleEvent(ev: StreamEvent) {
    switch (ev.event) {
      case "meta":
        setMeta(ev);
        break;
      case "eyes_detect":
        if (ev.status === "start") setPhase("👁 眼睛掃描表單…");
        else {
          setTexts(ev.texts);
          setPhase(`👁 偵測到 ${ev.texts.length} 個元素`);
        }
        break;
      case "brain":
        if (ev.status === "start") setPhase("🧠 大腦推理對應…");
        else if (ev.status === "thinking") setThinking((t) => t + ev.text);
        else if (ev.status === "content") setThinking((t) => t + ev.text);
        else if (ev.status === "tokens") setTokens({ in: ev.input_tokens, out: ev.output_tokens });
        else if (ev.status === "done") setPhase(`🧠 規劃完成，共 ${ev.fills.length} 欄`);
        break;
      case "locate":
        if (ev.status === "start") {
          setLocating({ index: ev.index, label: ev.label });
          setTurn(ev.index + 1);
          setPhase(`📍 定位「${ev.label}」(${ev.index + 1}/${ev.total})`);
        } else {
          setFilled((f) => [...f, ev.item]);
        }
        break;
      case "complete":
        setLocating(null);
        setPhase("✅ 完成");
        break;
    }
  }

  async function run() {
    if (!file) {
      setError("請先上傳表單截圖");
      return;
    }
    setRunning(true);
    setError("");
    setShowProfile(false);
    setTexts([]);
    setFilled([]);
    setThinking("");
    setTokens({ in: 0, out: 0 });
    setTurn(0);
    setElapsed(0);
    startRef.current = Date.now();
    try {
      const profile: Record<string, string> = {};
      rows.forEach((r) => r.key.trim() && (profile[r.key.trim()] = r.value));
      await autofillStream(file, profile, handleEvent);
    } catch (e) {
      setError((e as Error).message);
      setPhase("⚠ 發生錯誤");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* 標題列 */}
      <header className="flex items-center justify-between px-5 py-2 bg-slate-900 border-b border-slate-800">
        <h1 className="text-sm font-semibold tracking-wide text-slate-200">
          LLM Vision-Reasoning-ToolCall · 自動填表展示
        </h1>
        <span className="text-sm text-slate-400">👁 LocateAnything-3B + 🧠 Qwen3.6 35B A3B</span>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-4 p-4">
        {/* 左：表單即時展示 */}
        <section className="rounded-xl bg-slate-100 p-3 overflow-auto relative">
          {/* 工具列 */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <label className="cursor-pointer rounded bg-slate-800 text-slate-100 text-sm px-3 py-1.5 hover:bg-slate-700">
              選擇表單截圖
              <input type="file" accept="image/*" className="hidden"
                onChange={(e) => onPick(e.target.files?.[0] ?? null)} />
            </label>
            <button onClick={() => setShowProfile((s) => !s)}
              className="rounded bg-slate-200 text-slate-700 text-sm px-3 py-1.5 hover:bg-slate-300">
              {showProfile ? "收起個資" : "編輯個資"}
            </button>
            <button onClick={run} disabled={running || !file}
              className="rounded bg-sky-600 text-white text-sm font-semibold px-4 py-1.5 hover:bg-sky-500 disabled:opacity-40">
              {running ? "填表中…" : "開始填表"}
            </button>
            {error && <span className="text-rose-600 text-sm">{error}</span>}
          </div>

          {/* 個資編輯 */}
          {showProfile && (
            <div className="mb-3 rounded-lg bg-white border border-slate-200 p-3">
              <p className="text-xs text-slate-500 mb-2">個人資料（系統會自動對應到表單欄位）</p>
              {rows.map((r, i) => (
                <div key={i} className="flex gap-2 mb-1.5">
                  <input className="w-32 rounded border border-slate-200 px-2 py-1 text-sm text-slate-700"
                    value={r.key} placeholder="欄位"
                    onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))} />
                  <input className="flex-1 rounded border border-slate-200 px-2 py-1 text-sm text-slate-700"
                    value={r.value} placeholder="值"
                    onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                </div>
              ))}
              <button className="text-xs text-sky-600 hover:underline"
                onClick={() => setRows((rs) => [...rs, { key: "", value: "" }])}>+ 新增欄位</button>
            </div>
          )}

          {/* 表單影像 + 疊層 */}
          {imgUrl ? (
            <div className="relative inline-block">
              <img ref={imgRef} src={imgUrl} className="max-w-full block rounded shadow"
                onLoad={() => setDispW(imgRef.current?.clientWidth ?? 0)} />

              {/* 偵測到的元素：淡框 */}
              {texts.map((t, i) => (
                <div key={`t${i}`} className="absolute border border-slate-400/40 rounded-sm transition-opacity"
                  style={{ left: t.bbox.x1 * scale, top: t.bbox.y1 * scale,
                           width: (t.bbox.x2 - t.bbox.x1) * scale, height: (t.bbox.y2 - t.bbox.y1) * scale }} />
              ))}

              {/* 目前定位中的欄位：藍色脈動高亮 + 標註 */}
              {locatingBox && (
                <div className="absolute border-2 border-sky-500 bg-sky-400/20 rounded animate-pulse"
                  style={{ left: locatingBox.bbox.x1 * scale, top: locatingBox.bbox.y1 * scale,
                           width: (locatingBox.bbox.x2 - locatingBox.bbox.x1) * scale,
                           height: (locatingBox.bbox.y2 - locatingBox.bbox.y1) * scale }}>
                  <span className="absolute -top-5 left-0 text-[11px] bg-sky-600 text-white px-1 rounded whitespace-nowrap">
                    locating: {locating?.label}
                  </span>
                </div>
              )}

              {/* 已填欄位：綠框 + 打字機填入值 */}
              {filled.map((it, i) =>
                it.bbox ? (
                  <div key={`f${i}`} className="absolute border-2 border-emerald-500 bg-emerald-300/30 rounded-sm flex items-center px-1"
                    style={{ left: it.bbox.x1 * scale, top: it.bbox.y1 * scale,
                             width: (it.bbox.x2 - it.bbox.x1) * scale, height: (it.bbox.y2 - it.bbox.y1) * scale }}>
                    <span className="text-[11px] font-medium text-emerald-900 truncate">
                      <Typed value={it.value} />
                    </span>
                  </div>
                ) : null
              )}
            </div>
          ) : (
            <div className="h-80 grid place-items-center text-slate-400 text-sm">
              上傳表單截圖後按「開始填表」，這裡會即時展示定位與填入過程
            </div>
          )}
        </section>

        {/* 右：模型面板 */}
        <aside className="space-y-3">
          {/* 模型 + 計時 + token */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
            <div className="text-lg font-bold leading-tight text-slate-100">
              Qwen3.6 35B A3B
              <span className="text-slate-500"> + </span>
              LocateAnything-3B
            </div>
            <div className="text-3xl font-mono mt-1 text-sky-400">{mmss(elapsed)}</div>
            <div className="grid grid-cols-2 gap-2 mt-3">
              <div className="rounded-lg bg-slate-800 p-2">
                <div className="text-[10px] text-slate-400">INPUT TOKENS</div>
                <div className="text-xl font-mono text-slate-100">{tokens.in.toLocaleString()}</div>
              </div>
              <div className="rounded-lg bg-slate-800 p-2">
                <div className="text-[10px] text-slate-400">OUTPUT TOKENS</div>
                <div className="text-xl font-mono text-slate-100">{tokens.out.toLocaleString()}</div>
              </div>
            </div>
            {meta?.mock && <div className="mt-2 text-[11px] text-amber-400">MOCK 模式（未載入真實模型）</div>}
          </div>

          {/* 縮圖 + 偵測框 */}
          {imgUrl && meta && (
            <div className="rounded-xl bg-slate-900 border border-slate-800 p-3">
              <div className="text-[11px] text-slate-400 mb-1">偵測縮圖</div>
              <div className="relative inline-block">
                <img src={imgUrl} className="w-full rounded" />
                <svg className="absolute inset-0 w-full h-full" viewBox={`0 0 ${meta.image_width} ${meta.image_height}`} preserveAspectRatio="none">
                  {texts.map((t, i) => (
                    <rect key={i} x={t.bbox.x1} y={t.bbox.y1} width={t.bbox.x2 - t.bbox.x1} height={t.bbox.y2 - t.bbox.y1}
                      fill="none" stroke="#38bdf8" strokeWidth={3} />
                  ))}
                  {filled.map((it, i) => it.bbox && (
                    <rect key={`f${i}`} x={it.bbox.x1} y={it.bbox.y1} width={it.bbox.x2 - it.bbox.x1} height={it.bbox.y2 - it.bbox.y1}
                      fill="rgba(16,185,129,0.3)" stroke="#10b981" strokeWidth={3} />
                  ))}
                </svg>
              </div>
            </div>
          )}

          {/* ASSISTANT 思考串流 */}
          <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400">ASSISTANT · Turn {turn}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${running ? "bg-rose-600 text-white animate-pulse" : "bg-slate-700 text-slate-300"}`}>
                {running ? "STREAMING" : "IDLE"}
              </span>
            </div>
            <div className="text-sm text-sky-300 mb-2">{phase}</div>
            <div className="text-[10px] text-slate-500 mb-1">THINKING STREAM</div>
            <div ref={thinkRef} className="h-72 overflow-auto rounded bg-slate-950 p-2 text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap font-mono">
              {thinking || (running ? "Waiting for model stream…" : "（按「開始填表」後，這裡顯示大腦的即時推理）")}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
