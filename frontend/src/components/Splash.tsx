import { CSSProperties, useEffect, useRef, useState } from "react";
import { useT } from "../i18n";
import "./splash-download.css";

/* ---------------------------------------------------------------------------
   se7en Download launch animation — « le téléchargement », silent, about 2.3 s:
   a download arrow drops into a tray → the letters of SE7EN fall one after the
   other, each behind a streak of light, and bounce into place → a progress
   line underneath climbs to 100 % with its counter → a flash marks « done ».
   On exit the wordmark is pulled down into the tray, like a finished file.
   Click (or any key) to skip once the engine is ready.
   --------------------------------------------------------------------------- */

const LETTERS = ["S", "E", "7", "E", "N"];
const HOLD = 2300;
const OUT = 540;

export function Splash({ onDone, version, ready }: { onDone: () => void; version?: string; ready?: boolean }) {
  const t = useT();
  const [leaving, setLeaving] = useState(false);
  const [held, setHeld] = useState(false);
  const [pct, setPct] = useState(0);
  const done = useRef(false);
  const readyRef = useRef(ready);
  readyRef.current = ready;

  const leave = () => {
    if (done.current) return;
    done.current = true;
    setLeaving(true);
    window.setTimeout(onDone, OUT);
  };

  useEffect(() => {
    const id = window.setTimeout(() => setHeld(true), HOLD);
    // the counter follows the progress line (0 → 100 % between 0.45 s and 1.75 s, eased)
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const k = Math.min(1, Math.max(0, (now - t0 - 450) / 1300));
      setPct(Math.round(100 * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const key = () => readyRef.current && leave();
    window.addEventListener("keydown", key);
    return () => {
      window.clearTimeout(id);
      cancelAnimationFrame(raf);
      window.removeEventListener("keydown", key);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (held && ready) leave();
  }, [held, ready]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={`splash spd ${leaving ? "leaving" : ""}`} onClick={() => ready && leave()}>
      <div className="spd-rain" />
      <div className="spd-center">
        <div className="spd-arrow">
          <svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3v13" /><path d="m6 11 6 6 6-6" /><path d="M4 21h16" />
          </svg>
        </div>
        <div className="spd-word" aria-label="se7en">
          {LETTERS.map((l, i) => (
            <span key={i} className={`spd-l ${l === "7" ? "seven" : ""}`} style={{ "--i": i } as CSSProperties}>
              <i className="spd-streak" />
              {l}
            </span>
          ))}
        </div>
        <div className="spd-progress">
          <span className="spd-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="spd-meta">
          <span>DOWNLOAD</span>
          <span className="spd-pct">{pct} %</span>
        </div>
        <div className="spd-tag">{t("splash.tagline")}</div>
      </div>
      <div className="spd-foot">
        <span>v{version ?? ""}</span>
        <span>{ready ? t("splash.skip") : t("splash.init")}</span>
      </div>
    </div>
  );
}
