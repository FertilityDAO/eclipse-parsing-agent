/* ══════════════════════════════════════════════ S2g · THE LIVING GLOBE
   Every path drawn here is real traced geometry from outputs/path_index.json —
   the same artifact engine.path() serves. The frontend computes no eclipse
   science whatsoever: it projects and animates numbers the engine produced.
   The hero path is chosen by the editorial ladder, server-side, and arrives
   pre-selected in the payload. */
const GB = JSON.parse(document.getElementById("globedata").textContent);
const RAD = Math.PI / 180, R_KM = 6371.0088;

/* phase boundaries, ms from sequence start */
const T = {
  globeIn: 500, accIn: 1300, accOut: 5900, traced: 6100,
  yours: 6900, yoursHold: 8500, hero: 8700,
  ctrA: 8900, ctrB: 10200, zoomA: 10300, zoomB: 12200,
  hold: 12200, cut: 13300, end: 13750
};

const clamp01 = v => (v < 0 ? 0 : v > 1 ? 1 : v);
const seg = (t, a, b) => clamp01((t - a) / (b - a));
const easeIO = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const lerp = (a, b, t) => a + (b - a) * t;
const yearLabel = y => (y < 0 ? `${-y} BCE` : `${y} CE`);

/* orthographic — the only projection that reads as a globe rather than a
   flat map, and it handles antimeridian crossings for free. */
function ortho(lam0, phi0, R, cx, cy){
  const sp = Math.sin(phi0 * RAD), cp = Math.cos(phi0 * RAD);
  return (lon, lat) => {
    const l = (lon - lam0) * RAD, p = lat * RAD;
    const sinp = Math.sin(p), cosp = Math.cos(p), cosl = Math.cos(l);
    if (sp * sinp + cp * cosp * cosl < 0) return null;       // far side
    return [cx + R * cosp * Math.sin(l), cy - R * (cp * sinp - sp * cosp * cosl)];
  };
}

function strokePath(x, pts, P, colour, wpx, alpha){
  if (alpha <= .004) return;
  x.strokeStyle = colour; x.globalAlpha = alpha;
  x.lineWidth = Math.max(.7, wpx); x.lineCap = "round"; x.lineJoin = "round";
  x.beginPath();
  let pen = false;
  for (let i = 0; i < pts.length; i++){
    const q = P(pts[i][0], pts[i][1]);
    if (!q){ pen = false; continue; }
    if (pen) x.lineTo(q[0], q[1]); else { x.moveTo(q[0], q[1]); pen = true; }
  }
  x.stroke(); x.globalAlpha = 1;
}

let gbRAF = 0, gbTimers = [];
function stopGlobe(){
  cancelAnimationFrame(gbRAF); gbRAF = 0;
  gbTimers.forEach(clearTimeout); gbTimers = [];
}

function runGlobe(){
  stopGlobe();
  const cv = $("globeCanvas"), x = cv.getContext("2d");
  const H = { year: $("gbYear"), lab: $("gbYearLab"), cap: $("gbCaption"),
              cnt: $("gbCount"), note: $("gbNote") };

  const place = D.input.place_short;
  const hero = GB.hero[key];
  const touched = GB.touched[key] || [];
  const obs = D.shadow_map.observer;                 // [lon, lat]
  const everCount = touched.length;

  H.note.textContent =
    `Showing a ${GB.meta.sample_shown}-path sample of ${GB.meta.traced_total.toLocaleString("en-GB")} traced paths · ` +
    `NASA Five Millennium Canon · geometry not recomputed in the browser`;

  let W = 0, Ht = 0, dpr = 1, minDim = 800;
  const sizeIt = () => {
    const r = cv.getBoundingClientRect();
    dpr = Math.min(2, devicePixelRatio || 1);
    W = r.width; Ht = r.height; minDim = Math.min(W, Ht);
    cv.width = Math.round(W * dpr); cv.height = Math.round(Ht * dpr);
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  sizeIt();
  const onResize = () => sizeIt();
  addEventListener("resize", onResize);

  /* Zoom so the decisive relationship reads at the same visual size for every
     archetype: a near miss spans ~30% of the short edge, a hit shows its band
     at ~42%. Small-angle: screen distance ≈ R·θ. */
  const R0 = () => minDim * 0.34;
  const R1 = () => {
    // For a miss, frame the gap AND the near edge of the band: at 31 km Tokyo's
    // 116 km band is nearly 4x its miss, and framing the gap alone pushes both
    // band edges off-screen — which reads as a hit. Frame dist + half-band.
    const km = hero.hit ? hero.w : (hero.dist_km + hero.w / 2);
    const target = minDim * (hero.hit ? 0.42 : 0.38);
    return Math.min(90000, Math.max(R0() * 1.6, target / Math.max(km / R_KM, 1e-5)));
  };

  const heroColour = () => (hero.side === "past" ? "#E0A144" : "#8FB2CC");
  const start = performance.now();
  let capState = -1;

  const setCap = (n, count, text) => {
    if (capState === n) return;
    capState = n;
    H.cnt.textContent = count || "";
    H.cnt.classList.toggle("is-in", !!count);
    H.cap.textContent = text || "";
    H.cap.classList.toggle("is-in", !!text);
  };

  function frame(now){
    const t = now - start;
    x.clearRect(0, 0, W, Ht);

    /* ---- camera ---- */
    const drift = seg(t, T.globeIn, T.ctrA) * 26;               // slow spin
    const cE = easeIO(seg(t, T.ctrA, T.ctrB));
    const lam0 = lerp(obs[0] - 58 + drift, obs[0], cE);
    const phi0 = lerp(Math.max(-32, Math.min(32, obs[1] * .35)) + 6, obs[1], cE);
    const R = lerp(R0(), R1(), easeIO(seg(t, T.zoomA, T.zoomB)));
    const cx = W / 2, cy = Ht / 2;
    const P = ortho(lam0, phi0, R, cx, cy);
    const kmPx = R / R_KM;                                       // km → px
    const fadeIn = seg(t, 0, T.globeIn);

    /* ---- the sphere ---- */
    const sphereA = fadeIn * (1 - easeIO(seg(t, T.zoomA, T.zoomB)) * .82);
    x.globalAlpha = sphereA;
    const grd = x.createRadialGradient(cx - R * .3, cy - R * .35, R * .05, cx, cy, R);
    grd.addColorStop(0, "#141726"); grd.addColorStop(1, "#0A0B12");
    x.fillStyle = grd;
    x.beginPath(); x.arc(cx, cy, R, 0, 7); x.fill();
    x.strokeStyle = "#2A2D42"; x.lineWidth = 1; x.stroke();
    x.globalAlpha = 1;

    /* graticule — 30° meridians and parallels, hairline */
    for (let lo = -180; lo < 180; lo += 30){
      const pts = []; for (let la = -90; la <= 90; la += 3) pts.push([lo, la]);
      strokePath(x, pts, P, "#22243A", 1, sphereA * .85);
    }
    for (let la = -60; la <= 60; la += 30){
      const pts = []; for (let lo = -180; lo <= 180; lo += 3) pts.push([lo, la]);
      strokePath(x, pts, P, "#22243A", 1, sphereA * .85);
    }

    /* ---- context paths: 5,000 years accumulating, oldest first ---- */
    const accP = seg(t, T.accIn, T.accOut);
    const shown = Math.floor(accP * GB.context.length);
    const ctxAlpha = lerp(.16, .035, easeIO(seg(t, T.yours, T.yoursHold)))
                   * (1 - easeIO(seg(t, T.zoomA, T.zoomB)) * .9);
    for (let i = 0; i < shown; i++){
      const p = GB.context[i];
      const a = ctxAlpha * clamp01((accP * GB.context.length - i) / 3);
      strokePath(x, p.c, P, "#C9CBE0", Math.max(.7, p.w * kmPx), a);
    }

    /* ---- the ones that actually touched this exact point ---- */
    const tA = easeIO(seg(t, T.yours, T.yoursHold))
             * (1 - easeIO(seg(t, T.hero, T.ctrB)) * .88);
    if (tA > .004){
      touched.forEach((p, i) => {
        if (p.id === hero.id) return;
        strokePath(x, p.c, P, "#E0A144", Math.max(1, p.w * kmPx), tA * .8);
      });
    }

    /* ---- the hero: the path the ladder made the verdict ---- */
    const hA = easeIO(seg(t, T.hero, T.ctrB));
    if (hA > .004){
      const wpx = Math.max(1.4, hero.w * kmPx);
      // future geometry is drawn hollow-dashed; past is solid. A thing that has
      // happened is solid, a thing that has not is not yet.
      if (hero.side === "future"){
        x.setLineDash([Math.max(6, wpx * .5), Math.max(5, wpx * .42)]);
        strokePath(x, hero.c, P, heroColour(), wpx, hA * .5);
        x.setLineDash([]);
        strokePath(x, hero.c, P, heroColour(), Math.max(1.2, wpx * .1), hA);
      } else {
        strokePath(x, hero.c, P, heroColour(), wpx, hA * .34);
        strokePath(x, hero.c, P, heroColour(), Math.max(1.2, wpx * .1), hA);
      }
    }

    /* ---- the birthplace: appears, then never moves again ---- */
    const oA = easeIO(seg(t, T.yours, T.yours + 450));
    const o = P(obs[0], obs[1]);
    if (o && oA > .004){
      // miss line, once we are close enough to read it
      const mA = easeIO(seg(t, T.zoomA + 500, T.zoomB));
      if (!hero.hit && hero.near && mA > .004){
        const n = P(hero.near[0], hero.near[1]);
        if (n){
          x.setLineDash([3, 5]); x.globalAlpha = mA;
          x.strokeStyle = heroColour(); x.lineWidth = 1.5;
          x.beginPath(); x.moveTo(o[0], o[1]); x.lineTo(n[0], n[1]); x.stroke();
          x.setLineDash([]);
          x.fillStyle = heroColour();
          x.font = `500 ${Math.max(13, minDim * .032)}px ui-monospace,Menlo,Consolas,monospace`;
          x.textAlign = "center"; x.textBaseline = "bottom";
          x.fillText(`${Math.round(hero.dist_km).toLocaleString("en-GB")} km`,
                     (o[0] + n[0]) / 2, (o[1] + n[1]) / 2 - 10);
          x.globalAlpha = 1;
        }
      }
      x.globalAlpha = oA;
      x.strokeStyle = "#F2F0EA"; x.lineWidth = 1;
      x.beginPath(); x.arc(o[0], o[1], 13 + (1 - oA) * 22, 0, 7); x.stroke();
      x.fillStyle = "#F2F0EA";
      x.beginPath(); x.arc(o[0], o[1], 4, 0, 7); x.fill();
      x.globalAlpha = 1;
    }

    /* ---- HUD ---- */
    if (t < T.accIn){
      H.year.style.opacity = 0; setCap(0, "", "");
    } else if (t < T.accOut){
      H.year.style.opacity = 1;
      const p = GB.context[Math.min(GB.context.length - 1, shown)];
      H.year.firstChild.nodeValue = yearLabel(p ? p.y : GB.meta.year_range[0]);
      H.lab.textContent = "sweeping the canon";
      setCap(1, "", `${GB.meta.catalog_total.toLocaleString("en-GB")} solar eclipses across five thousand years`);
    } else if (t < T.yours){
      H.year.style.opacity = 0;
      setCap(2, GB.meta.traced_total.toLocaleString("en-GB"),
             "paths of totality, traced from Besselian elements");
    } else if (t < T.hero){
      setCap(3, String(everCount),
             `have crossed ${place} in five thousand years`);
    } else if (t < T.zoomA + 600){
      setCap(4, "", hero.hit
        ? (hero.side === "future"
            ? `${hero.id.slice(0, 4)} — the one that reaches your birthplace`
            : `${hero.id.slice(0, 4)} — the one that reached your birthplace`)
        : `${hero.id.replace(/^-/, "").slice(0, 4)} — the one that came nearest`);
    } else {
      setCap(5, "", hero.hit
        ? (hero.side === "future"
            ? "Your birthplace sits inside the band. You would need to be standing there."
            : "Your birthplace sits inside the band.")
        : `The band passed ${Math.round(hero.dist_km).toLocaleString("en-GB")} km from the point where you were born.`);
    }

    /* ---- M5, preserved: the cut is 400 ms of nothing ---- */
    if (t >= T.cut){
      x.globalAlpha = clamp01((t - T.cut) / 400);
      x.fillStyle = "#06060B"; x.fillRect(0, 0, W, Ht);
      x.globalAlpha = 1;
      H.cap.classList.remove("is-in"); H.cnt.classList.remove("is-in");
    }

    if (t >= T.end){
      removeEventListener("resize", onResize);
      stopGlobe(); show("s3"); return;
    }
    gbRAF = requestAnimationFrame(frame);
  }

  /* reduced motion: one static composite of the final relationship, held. */
  if (reduced()){
    const R = R1(), cx = W / 2, cy = Ht / 2;
    const P = ortho(obs[0], obs[1], R, cx, cy), kmPx = R / R_KM;
    x.clearRect(0, 0, W, Ht);
    touched.forEach(p => strokePath(x, p.c, P, "#E0A144", Math.max(1, p.w * kmPx), .18));
    const wpx = Math.max(1.4, hero.w * kmPx);
    strokePath(x, hero.c, P, heroColour(), wpx, .34);
    strokePath(x, hero.c, P, heroColour(), Math.max(1.2, wpx * .1), 1);
    const o = P(obs[0], obs[1]);
    if (o){
      if (!hero.hit && hero.near){
        const n = P(hero.near[0], hero.near[1]);
        if (n){
          x.setLineDash([3, 5]); x.strokeStyle = heroColour(); x.lineWidth = 1.5;
          x.beginPath(); x.moveTo(o[0], o[1]); x.lineTo(n[0], n[1]); x.stroke(); x.setLineDash([]);
          x.fillStyle = heroColour();
          x.font = `500 ${Math.max(13, minDim * .032)}px ui-monospace,Menlo,Consolas,monospace`;
          x.textAlign = "center"; x.textBaseline = "bottom";
          x.fillText(`${Math.round(hero.dist_km).toLocaleString("en-GB")} km`,
                     (o[0] + n[0]) / 2, (o[1] + n[1]) / 2 - 10);
        }
      }
      x.strokeStyle = "#F2F0EA"; x.lineWidth = 1;
      x.beginPath(); x.arc(o[0], o[1], 13, 0, 7); x.stroke();
      x.fillStyle = "#F2F0EA"; x.beginPath(); x.arc(o[0], o[1], 4, 0, 7); x.fill();
    }
    H.year.style.opacity = 0;
    setCap(9, String(everCount), hero.hit
      ? `of ${GB.meta.traced_total.toLocaleString("en-GB")} traced paths have crossed ${place}. This is the one the verdict rests on.`
      : `of ${GB.meta.traced_total.toLocaleString("en-GB")} traced paths have crossed ${place}. The nearest came ${Math.round(hero.dist_km).toLocaleString("en-GB")} km away.`);
    gbTimers.push(setTimeout(() => { removeEventListener("resize", onResize); show("s3"); }, 2600));
    return;
  }

  gbRAF = requestAnimationFrame(frame);
}
