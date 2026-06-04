import { useMemo, useRef, useState } from "react";
import { autofill, type AutofillResponse } from "./api";

interface Row {
  key: string;
  value: string;
}

const DEFAULT_PROFILE: Row[] = [
  { key: "name", value: "王小明" },
  { key: "email", value: "ming@example.com" },
  { key: "phone", value: "0912345678" },
];

export default function App() {
  const [rows, setRows] = useState<Row[]>(DEFAULT_PROFILE);
  const [file, setFile] = useState<File | null>(null);
  const [imgUrl, setImgUrl] = useState<string>("");
  const [result, setResult] = useState<AutofillResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const imgRef = useRef<HTMLImageElement>(null);
  const [dispW, setDispW] = useState(0);

  const scale = useMemo(
    () => (result && dispW ? dispW / result.image_width : 1),
    [result, dispW]
  );

  function onPick(f: File | null) {
    setFile(f);
    setResult(null);
    setError("");
    if (f) setImgUrl(URL.createObjectURL(f));
  }

  async function run() {
    if (!file) {
      setError("請先選一張表單截圖");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const profile: Record<string, string> = {};
      rows.forEach((r) => r.key.trim() && (profile[r.key.trim()] = r.value));
      setResult(await autofill(file, profile));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen mx-auto max-w-6xl p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">AutoFillForm</h1>
        <p className="text-slate-400 text-sm">
          兩個小模型協作自動填表 · 眼睛 <b>LocateAnything-3B</b> 看圖定位 ·
          大腦 <b>Qwen3.6 35B A3B</b> 推理對應
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
        {/* 左：個資 + 上傳 */}
        <section className="space-y-4">
          <div className="rounded-xl bg-slate-900 p-4">
            <h2 className="font-semibold mb-2">個人資料</h2>
            {rows.map((r, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  className="w-28 rounded bg-slate-800 px-2 py-1 text-sm"
                  value={r.key}
                  placeholder="欄位"
                  onChange={(e) =>
                    setRows((rs) => rs.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))
                  }
                />
                <input
                  className="flex-1 rounded bg-slate-800 px-2 py-1 text-sm"
                  value={r.value}
                  placeholder="值"
                  onChange={(e) =>
                    setRows((rs) => rs.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))
                  }
                />
              </div>
            ))}
            <button
              className="text-xs text-sky-400 hover:underline"
              onClick={() => setRows((rs) => [...rs, { key: "", value: "" }])}
            >
              + 新增欄位
            </button>
          </div>

          <div className="rounded-xl bg-slate-900 p-4">
            <h2 className="font-semibold mb-2">表單截圖</h2>
            <input
              type="file"
              accept="image/*"
              className="text-sm"
              onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            />
          </div>

          <button
            onClick={run}
            disabled={loading}
            className="w-full rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-50 py-2 font-semibold"
          >
            {loading ? "分析中…" : "開始自動填表"}
          </button>
          {error && <p className="text-rose-400 text-sm">{error}</p>}
        </section>

        {/* 右：視覺化結果 */}
        <section className="space-y-4">
          <div className="relative rounded-xl bg-slate-900 p-2 overflow-auto">
            {imgUrl ? (
              <div className="relative inline-block">
                <img
                  ref={imgRef}
                  src={imgUrl}
                  className="max-w-full block rounded"
                  onLoad={() => setDispW(imgRef.current?.clientWidth ?? 0)}
                />
                {result?.plan.map((item, i) =>
                  item.bbox ? (
                    <div
                      key={i}
                      className="absolute border-2 border-emerald-400 bg-emerald-400/20 rounded-sm flex items-center px-1"
                      style={{
                        left: item.bbox.x1 * scale,
                        top: item.bbox.y1 * scale,
                        width: (item.bbox.x2 - item.bbox.x1) * scale,
                        height: (item.bbox.y2 - item.bbox.y1) * scale,
                      }}
                    >
                      <span className="text-[10px] text-emerald-50 truncate drop-shadow">
                        {item.value}
                      </span>
                    </div>
                  ) : null
                )}
              </div>
            ) : (
              <div className="h-64 grid place-items-center text-slate-500 text-sm">
                上傳表單截圖後，這裡會顯示定位與填寫結果
              </div>
            )}
          </div>

          {result && (
            <div className="rounded-xl bg-slate-900 p-4">
              <div className="flex justify-between text-xs text-slate-400 mb-2">
                <span>填寫計畫（{result.plan.length} 欄）</span>
                {result.mock && <span className="text-amber-400">MOCK 模式</span>}
              </div>
              <table className="w-full text-sm">
                <thead className="text-slate-400 text-left">
                  <tr>
                    <th className="py-1">欄位</th>
                    <th>填入值</th>
                    <th>座標</th>
                  </tr>
                </thead>
                <tbody>
                  {result.plan.map((item, i) => (
                    <tr key={i} className="border-t border-slate-800">
                      <td className="py-1">{item.label}</td>
                      <td className="text-emerald-300">{item.value}</td>
                      <td className="text-slate-500">
                        {item.point
                          ? `(${Math.round(item.point[0])}, ${Math.round(item.point[1])})`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
