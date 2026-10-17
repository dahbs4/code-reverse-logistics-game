import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Game, WeeklyOutlook, WeeklyPlan } from './types'
import { compact, num } from './types'
import { api } from './store'

export default function WeeklyPlanning({game,onCommit,onDirty}:{game:Game;onCommit:(game:Game)=>void;onDirty:(dirty:boolean)=>void}) {
 const [plan,setPlan]=useState<WeeklyPlan>({...game.weekly_plan})
 const [projection,setProjection]=useState<WeeklyOutlook|null>(game.weekly_outlook)
 const [pending,setPending]=useState(false)
 const [saving,setSaving]=useState(false)
 const [error,setError]=useState('')
 const [saved,setSaved]=useState(false)
 const valid=Number.isInteger(plan.IND)&&Number.isInteger(plan.EAST)&&plan.IND>=0&&plan.IND<=1000000&&plan.EAST>=0&&plan.EAST<=500000
 useEffect(()=>{
  let alive=true;setSaved(false);setError('');setPending(true)
  if(!valid){setPending(false);return}
  const timer=setTimeout(()=>{api<WeeklyOutlook>(`/games/${game.id}/preview`,plan).then(value=>{if(alive){setProjection(value);setPending(false)}}).catch(e=>{if(alive){setError(e.message);setPending(false)}})},250)
  return()=>{alive=false;clearTimeout(timer)}
 },[game.id,game.hour,plan.IND,plan.EAST,valid])
 async function save(){setSaving(true);setError('');try{onCommit(await api<Game>(`/games/${game.id}/action`,plan));setSaved(true)}catch(e){setError((e as Error).message)}finally{setSaving(false)}}
 useEffect(()=>{onDirty(plan.IND!==game.weekly_plan.IND||plan.EAST!==game.weekly_plan.EAST);return()=>onDirty(false)},[plan.IND,plan.EAST,game.weekly_plan.IND,game.weekly_plan.EAST,onDirty])
 const ready=valid&&!pending&&!error
 const week=projection?.next_week
 const chart=projection?.weeks.map(w=>({week:w.week,backlog:w.ending_backlog,removals:w.forecast,processing:w.projected_processed}))||[]
 return <>
  <section className="panel weekly-plan"><div className="panel-heading"><div><h2>Plan your weekly units</h2><p>Set each site's processing target. The outlook updates as you change the plan.</p></div><span className="tag">UNITS / WEEK</span></div>
   <div className="weekly-inputs">{(['IND','EAST'] as const).map(site=><label className="weekly-field" key={site}><strong>{site==='IND'?'Indianapolis':'East Coast'}</strong><input aria-label={`${site==='IND'?'Indianapolis':'East Coast'} planned units per week`} type="number" min={0} max={site==='IND'?1000000:500000} step={10000} value={plan[site]} onChange={e=>setPlan(p=>({...p,[site]:Number(e.target.value)}))}/><span>Typical {num(week?.sites[site].normal||0)} · Maximum {num(site==='IND'?1000000:500000)}</span></label>)}</div>
   {!valid&&<p role="alert" className="padding bad">Enter whole units: Indianapolis 0–1,000,000; East Coast 0–500,000.</p>}
   {error&&<p role="alert" className="error">{error}</p>}
   <div className="weekly-save"><p className="muted">{pending?'Updating outlook…':saved?'Weekly plan saved. Advance one week when ready.':'This plan repeats for future weeks until you change it.'}</p><button className="primary" onClick={save} disabled={!ready||saving||game.terminal.done}>{saving?'Saving…':'Save weekly plan'}</button></div>
  </section>
  {week&&<section className="panel"><div className="panel-heading"><div><h3>Week {week.week} outlook</h3><p>Starting backlog + forecast removals − projected processing = ending backlog</p></div><span className="tag">{ready?'FORECAST':'UPDATING'}</span></div><div className={'weekly-summary '+(!ready?'updating':'')} aria-busy={!ready}>
   {[['Starting backlog',week.starting_backlog],['Forecast removals',week.forecast],['Projected processing',week.projected_processed],['Projected ending backlog',week.ending_backlog]].map(([label,value])=><div key={String(label)}><span>{label}</span><strong>{num(Number(value))}</strong></div>)}
  </div><div className="table-wrap"><table><thead><tr><th>Site</th><th>Planned units</th><th>Projected processing</th><th>Projected backlog</th></tr></thead><tbody>{(['IND','EAST'] as const).map(site=><tr key={site}><td>{site==='IND'?'Indianapolis':'East Coast'}</td><td>{num(week.sites[site].planned)}</td><td>{num(week.sites[site].projected_processed)}</td><td>{num(week.sites[site].ending_backlog)}</td></tr>)}</tbody></table></div><p className="padding muted small">Processing is limited by available freight and scenario capacity. Targets above East Coast's typical rate automatically include surge labor costs. Routing stays fixed. Forecasts are estimates; removal actuals vary each week.</p></section>}
  {projection&&<section className="panel"><div className="panel-heading"><div><h3>Where this plan takes you</h3><p>Projected year-end backlog <strong data-testid="projected-year-end">{num(projection.year_end_backlog)} units</strong> · Uses the latest removal forecast and your weekly plan for every remaining week.</p></div></div><div className={'chart tall '+(!ready?'updating':'')}><ResponsiveContainer width="100%" height="100%"><LineChart data={chart}><CartesianGrid stroke="#233040" vertical={false}/><XAxis dataKey="week" tickFormatter={n=>`W${n}`} minTickGap={24} stroke="#8291a6"/><YAxis tickFormatter={compact} width={60} stroke="#8291a6"/><Tooltip contentStyle={{background:'#172130',border:'1px solid #354153'}} labelFormatter={n=>`Week ${n}`} formatter={(n:number)=>num(n)}/><Line dataKey="backlog" name="Projected ending backlog" stroke="#68d9b5" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div><details className="score-rules"><summary>Weekly outlook details</summary><div className="table-wrap annual-table"><table><thead><tr><th>Week</th><th>Forecast removals</th><th>Planned units</th><th>Projected processing</th><th>Ending backlog</th></tr></thead><tbody>{projection.weeks.map(w=><tr key={w.week}><td>{w.week}</td><td>{num(w.forecast)}</td><td>{num(w.planned)}</td><td>{num(w.projected_processed)}</td><td>{num(w.ending_backlog)}</td></tr>)}</tbody></table></div></details></section>}
 </>
}
