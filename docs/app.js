/* Delhi Gold Tracker dashboard — reads the committed JSON, no build step. */
(function () {
  "use strict";

  const INR = (n) =>
    n === null || n === undefined
      ? "₹—"
      : "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });

  const VERDICT_META = {
    "STRONG BUY": { cls: "verdict-buy", icon: "trending_down" },
    "BUY": { cls: "verdict-buy", icon: "trending_down" },
    "ACCUMULATE": { cls: "verdict-buy", icon: "shopping_cart" },
    "WAIT": { cls: "verdict-wait", icon: "hourglass_top" },
    "HOLD": { cls: "verdict-hold", icon: "trending_flat" },
  };

  function fmtChangePct(pct) {
    if (pct === null || pct === undefined) return { text: "No prior data", cls: "flat", icon: "remove" };
    if (pct > 0.001) return { text: `+${pct.toFixed(2)}% vs yesterday`, cls: "up", icon: "arrow_upward" };
    if (pct < -0.001) return { text: `${pct.toFixed(2)}% vs yesterday`, cls: "down", icon: "arrow_downward" };
    return { text: "Unchanged", cls: "flat", icon: "remove" };
  }

  /** Walk history backward from the end to find the last two non-null values for `key`,
   *  and return the % change between them. Handles 18K, which can have gaps. */
  function dayOverDayPct(records, key) {
    const vals = records.filter((r) => r[key] !== null && r[key] !== undefined);
    if (vals.length < 2) return null;
    const today = vals[vals.length - 1][key];
    const prev = vals[vals.length - 2][key];
    if (!prev) return null;
    return ((today - prev) / prev) * 100;
  }

  function setChangeBadge(el, pct) {
    const c = fmtChangePct(pct);
    el.className = "karat-card__change " + c.cls;
    el.innerHTML = `<span class="material-icons" aria-hidden="true">${c.icon}</span> ${c.text}`;
  }

  function renderChart(history) {
    const points = history.slice(-90).filter((r) => r.k24 !== null && r.k24 !== undefined);

    const titleEl = document.getElementById("chart-title");
    const n = points.length;
    titleEl.textContent = `24K price — last ${n} day${n === 1 ? "" : "s"}`;

    const ctx = document.getElementById("price-chart").getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: points.map((r) => r.date.slice(5)), // MM-DD
        datasets: [
          {
            label: "24K ₹/g",
            data: points.map((r) => r.k24),
            borderColor: "#D9008D",
            backgroundColor: "rgba(217, 0, 141, 0.08)",
            fill: true,
            tension: 0.25,
            pointRadius: 0,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            ticks: { callback: (v) => "₹" + Number(v).toLocaleString("en-IN") },
            grid: { color: "#E8E4F0" },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  function wireEstimator(rate22k) {
    const gramsInput = document.getElementById("grams-input");
    const makingInput = document.getElementById("making-charge-input");
    const out = document.getElementById("estimator-value");

    function recompute() {
      const grams = parseFloat(gramsInput.value) || 0;
      const makingPct = (parseFloat(makingInput.value) || 0) / 100;
      if (!rate22k) {
        out.textContent = "₹—";
        return;
      }
      const subtotal = rate22k * grams * (1 + makingPct);
      const total = subtotal * 1.03; // 3% GST
      out.textContent = INR(Math.round(total));
    }

    gramsInput.addEventListener("input", recompute);
    makingInput.addEventListener("input", recompute);
    recompute();
  }

  async function main() {
    let latest, history;
    try {
      [latest, history] = await Promise.all([
        fetch("data/latest.json", { cache: "no-store" }).then((r) => r.json()),
        fetch("data/history.json", { cache: "no-store" }).then((r) => r.json()),
      ]);
    } catch (e) {
      document.getElementById("last-updated").textContent = "Failed to load data";
      return;
    }

    const records = (history && history.records) || [];
    if (!latest || !latest.record || records.length === 0) {
      document.getElementById("empty-state").hidden = false;
      document.getElementById("last-updated").textContent = "No data yet";
      return;
    }

    document.getElementById("empty-state").hidden = true;
    document.getElementById("app-content").hidden = false;

    const record = latest.record;
    const sig = latest.signal || { verdict: "HOLD", reasons: [], confidence: "low" };

    // Last-updated
    const updatedEl = document.getElementById("last-updated");
    if (latest.updated_at_utc) {
      const d = new Date(latest.updated_at_utc);
      const ist = d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });
      updatedEl.textContent = `Updated ${ist} IST`;
    }

    // Stale banner
    document.getElementById("stale-banner").classList.toggle("visible", !!record.stale);

    // Verdict
    const meta = VERDICT_META[sig.verdict] || VERDICT_META.HOLD;
    const banner = document.getElementById("verdict-banner");
    banner.className = "verdict-banner " + meta.cls;
    banner.querySelector(".material-icons").textContent = meta.icon;
    document.getElementById("verdict-label").textContent = sig.verdict + (sig.confidence === "low" ? " (low confidence)" : "");
    const reasonsEl = document.getElementById("verdict-reasons");
    reasonsEl.innerHTML = "";
    (sig.reasons || []).forEach((r) => {
      const li = document.createElement("li");
      li.textContent = r;
      reasonsEl.appendChild(li);
    });

    // Karat cards
    document.getElementById("price-24k").textContent = INR(record.k24);
    document.getElementById("price-22k").textContent = INR(record.k22);
    document.getElementById("price-18k").textContent = record.k18 != null ? INR(record.k18) : "—";

    setChangeBadge(document.getElementById("change-24k"), dayOverDayPct(records, "k24"));
    setChangeBadge(document.getElementById("change-22k"), dayOverDayPct(records, "k22"));
    setChangeBadge(document.getElementById("change-18k"), dayOverDayPct(records, "k18"));

    // Chart
    renderChart(records);

    // Estimator
    wireEstimator(record.k22);

    // Source meta
    document.getElementById("meta-source").textContent = record.primary_source || "—";
    document.getElementById("meta-spread").textContent =
      record.spread_pct != null ? record.spread_pct.toFixed(2) + "%" : "—";
    document.getElementById("meta-premium").textContent =
      record.india_premium != null ? (record.india_premium * 100 - 100).toFixed(1) + "% over spot" : "—";
    document.getElementById("meta-fx").textContent = record.usd_inr != null ? record.usd_inr.toFixed(2) : "—";
  }

  main();
})();
