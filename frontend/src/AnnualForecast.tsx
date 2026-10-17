import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Game } from './types'
import { compact, num } from './types'

export default function AnnualForecast({ game }: { game: Game }) {
 const forecast = game.annual_forecast
 if (!forecast) return <section className="panel padding"><h3>Annual forecast</h3><p>This older save has no weekly removal ledger. Start a new scenario for the 52-week campaign and annual forecast.</p></section>
 const cards = [ ['Original annual forecast', forecast.baseline_total], ['Completed removal actuals', forecast.actual_total], ['Remaining weeks forecast', forecast.remaining_forecast], ['Revised annual outlook', forecast.projected_total] ] as const
 return <section className="panel annual-forecast">
  <div className="panel-heading"><div><h3>52-week removal forecast</h3><p>Week 1 begins on the scenario start date. Actuals are units removed into the network, before transportation or processing.</p></div><span className="tag">{forecast.completed_weeks} / {forecast.weeks.length} WEEKS CLOSED</span></div>
  <div className="metrics four padding">{cards.map(([label, value]) => <div className="metric" key={label}><div className="metric-top">{label}</div><strong>{compact(value)}</strong></div>)}</div>
  <p className="padding muted small">Updated after week {forecast.completed_weeks} · Recent actual-to-baseline factor {forecast.revision_factor.toFixed(3)}× · Planning override {game.demand_override.toFixed(1)}×. Future weeks use the last four completed weeks, seasonal demand, and scheduled monthly DC removals. The current week's partial actuals do not revise future weeks.</p>
  <div className="chart tall"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={forecast.weeks} margin={{right:20}}><CartesianGrid stroke="#233040" vertical={false}/><XAxis dataKey="week" stroke="#637186" tickFormatter={n => `W${n}`} minTickGap={20}/><YAxis tickFormatter={compact} stroke="#637186" width={62}/><Tooltip contentStyle={{background:'#172130',border:'1px solid #354153',color:'#e4eaf3'}} labelFormatter={n => `Week ${n}`} formatter={(v:number) => num(v)}/><Legend/><Bar dataKey="actual" name="Completed removal actuals" fill="#68d9b5"/><Line dataKey="baseline" name="Original forecast" stroke="#778498" dot={false} strokeDasharray="4 4"/><Line dataKey="outlook" name="Actuals + revised forecast" stroke="#a49aec" dot={false} strokeWidth={2}/></ComposedChart></ResponsiveContainer></div>
  <details className="score-rules"><summary>Weekly forecast and actuals — all {forecast.weeks.length} weeks</summary><div className="table-wrap annual-table"><table><thead><tr><th>Week</th><th>Dates</th><th>Original forecast</th><th>Removal actuals</th><th>Annual outlook</th><th>Status</th></tr></thead><tbody>{forecast.weeks.map(w => <tr key={w.week}><td>{w.week}</td><td>{w.start} – {w.end}</td><td>{num(w.baseline)}</td><td>{w.actual === null ? w.status === 'in progress' ? `${num(w.actual_to_date)} so far` : '—' : num(w.actual)}</td><td>{num(w.outlook)}</td><td>{w.status}</td></tr>)}</tbody></table></div></details>
 </section>
}
