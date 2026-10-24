import React, { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "./api.js";

const C = { forecast: "#2F5BEA", actual: "#0C8F72", buffer: "#D9822B", grid: "#D5DDE1", ink: "#14232E" };
const mw = (v) => (v == null ? "n/a" : `${Math.round(v).toLocaleString("en-GB")} MW`);
const hhmm = (iso) => iso.slice(11, 16);

function useLoad(fn, deps) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let live = true;
    set((s) => ({ ...s, loading: true, error: null }));
    fn().then((data) => live && set({ data, error: null, loading: false }))
        .catch((error) => live && set({ data: null, error: error.message, loading: false }));
    return () => { live = false; };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return state;
}

function Figure({ label, value, hint }) {
  return (
    <div className="figure">
      <div className="figure-value">{value}</div>
      <div className="figure-label">{label}</div>
      {hint && <div className="figure-hint">{hint}</div>}
    </div>
  );
}

function Panel({ title, note, children }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {note && <p className="note">{note}</p>}
      <div className="chart-box">{children}</div>
    </section>
  );
}

const axis = { tick: { fill: "#5B6B76", fontSize: 12 }, stroke: C.grid };
const tip = { contentStyle: { border: `1px solid ${C.grid}`, borderRadius: 4, fontSize: 13 } };

export default function App() {
  const meta = useLoad(api.meta, []);
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("09:00");

  useEffect(() => {
    if (meta.data) setCutoff(meta.data.default_cutoff_time);
  }, [meta.data]);

  const params = { cutoff_time: cutoff };
  const day = useLoad(() => api.forecast({ delivery_date: date, ...params }), [date, cutoff]);
  const month = useLoad(
    () => (meta.data ? api.metrics({ start: meta.data.delivery_start, end: meta.data.delivery_end, ...params }) : Promise.resolve(null)),
    [meta.data, cutoff],
  );
  const horizon = useLoad(api.horizon, []);

  const buffer = month.data?.summary?.shortfall_p90_mw;
  const points = useMemo(
    () => (day.data?.points ?? []).map((p) => ({
      t: hhmm(p.startTime), forecast: p.forecast, actual: p.actual,
      planning: buffer != null ? Math.max(0, p.forecast - buffer) : null,
    })),
    [day.data, buffer],
  );
  const d = day.data?.metrics;

  return (
    <div className="shell">
      <aside className="rail">
        <h1>Wind cover</h1>
        <p className="rail-sub">How much wind can you count on when you buy day-ahead?</p>
        <label>Delivery day
          <input type="date" value={date} min={meta.data?.delivery_start} max={meta.data?.delivery_end}
                 onChange={(e) => e.target.value && setDate(e.target.value)} />
        </label>
        <label>Buying cutoff (UK time, day before)
          <input type="time" value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
        </label>
        <p className="rail-help">
          Each half-hour uses the latest forecast published at or before the cutoff, which is what you would
          have seen when placing the order.
        </p>
      </aside>

      <main>
        <header className="lede">
          {buffer != null ? (
            <h2>
              Across January deliveries, wind came in more than {mw(buffer)} below the forecast
              you saw at {cutoff}, about 1 half-hour in 10.
            </h2>
          ) : <h2>Loading the January accuracy picture…</h2>}
          <p>Holding back that margin from the forecast gives a planning level you can lean on.</p>
        </header>

        <Panel title={`Wind on ${date}`} note={day.data ? `Forecast cut off ${day.data.cutoff.replace("T", " ").slice(0, 16)} UTC` : ""}>
          {day.error ? <p className="error">{day.error}</p> : (
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={points} margin={{ left: 8, right: 16, top: 8 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="t" interval={5} {...axis} />
                <YAxis {...axis} width={56} tickFormatter={(v) => `${v / 1000}GW`} />
                <Tooltip {...tip} formatter={(v) => mw(v)} />
                <Legend />
                <Line name="Forecast at cutoff" dataKey="forecast" stroke={C.forecast} dot={false} strokeWidth={2} />
                <Line name="Actual" dataKey="actual" stroke={C.actual} dot={false} strokeWidth={2} />
                <Line name="Planning level" dataKey="planning" stroke={C.buffer} dot={false} strokeDasharray="5 4" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </Panel>

        {d?.n > 0 && (
          <div className="figures">
            <Figure label="Average miss" value={mw(d.mae_mw)} hint="MAE" />
            <Figure label="Typical swing" value={mw(d.rmse_mw)} hint="RMSE, penalises big misses" />
            <Figure label="Lean" value={`${d.bias_mw >= 0 ? "+" : ""}${Math.round(d.bias_mw)} MW`}
                    hint={d.bias_mw >= 0 ? "wind beat forecast" : "wind fell short"} />
            <Figure label="Miss vs output" value={`${d.nmae_pct?.toFixed(1)}%`} hint="MAE ÷ average wind" />
            <Figure label="Cover for this day" value={mw(d.shortfall_p90_mw)} hint="P90 shortfall" />
          </div>
        )}

        <h2 className="section-title">January accuracy</h2>
        {month.data && (
          <div className="figures">
            <Figure label="Average miss" value={mw(month.data.summary.mae_mw)} hint="MAE" />
            <Figure label="Typical swing" value={mw(month.data.summary.rmse_mw)} hint="RMSE" />
            <Figure label="Lean" value={`${Math.round(month.data.summary.bias_mw)} MW`} hint="mean of actual − forecast" />
            <Figure label="Miss vs output" value={`${month.data.summary.nmae_pct?.toFixed(1)}%`} hint="nMAE" />
            <Figure label="Cover to hold" value={mw(buffer)} hint="P90 shortfall" />
          </div>
        )}

        <div className="grid">
          <Panel title="Miss by delivery day" note="Mean absolute error per day (MW).">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={month.data?.daily ?? []}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="delivery_date" tickFormatter={(v) => v.slice(8)} {...axis} />
                <YAxis {...axis} width={48} />
                <Tooltip {...tip} formatter={(v) => mw(v)} />
                <Bar dataKey="mae_mw" name="MAE" fill={C.forecast} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
          <Panel title="Miss by how early the forecast was made" note="Hours before delivery. Later forecasts are sharper.">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={horizon.data ?? []}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="bucket" tickFormatter={(v) => `${v}h`} {...axis} />
                <YAxis {...axis} width={48} />
                <Tooltip {...tip} formatter={(v) => mw(v)} labelFormatter={(v) => `${v}-${v + 6}h ahead`} />
                <Line dataKey="mae_mw" name="MAE" stroke={C.forecast} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>
          <Panel title="Miss by hour of day" note="Mean absolute error and lean by delivery hour (UTC).">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={month.data?.by_hour ?? []}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="hour" {...axis} />
                <YAxis {...axis} width={48} />
                <Tooltip {...tip} formatter={(v) => mw(v)} />
                <ReferenceLine y={0} stroke={C.ink} />
                <Bar dataKey="mae_mw" name="MAE" fill={C.forecast} />
                <Bar dataKey="bias_mw" name="Lean" fill={C.buffer} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
          <Panel title="Miss by wind level" note="Grouped by the forecast level at cutoff.">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={month.data?.by_wind_level ?? []}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="level" {...axis} />
                <YAxis {...axis} width={48} />
                <Tooltip {...tip} formatter={(v) => mw(v)} />
                <ReferenceLine y={0} stroke={C.ink} />
                <Bar dataKey="mae_mw" name="MAE" fill={C.forecast} />
                <Bar dataKey="bias_mw" name="Lean" fill={C.buffer} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </div>
        <footer>Source: Elexon BMRS (FUELHH wind actuals, WINDFOR wind forecasts). Error = actual − forecast.</footer>
      </main>
    </div>
  );
}
