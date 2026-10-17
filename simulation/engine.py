"""Conserved category lots, deterministic random state, and hourly capacity budgets."""
import copy
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from .models import Action
from .forecast import annual_forecast, initialize_forecast, expected_removals

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'scenarios/defaults.json').read_text())
SCENARIOS = json.loads((ROOT/'scenarios/scenarios.json').read_text())
STATES = ('upstream','tender','pickup','transit','yard','receiving','staging')

def rng_for(s):
    r = random.Random()
    def tuples(x): return tuple(tuples(v) for v in x) if isinstance(x, list) else x
    r.setstate(tuples(s['rng']))
    return r

def lot(s, origin, site, category, units, state, born=None, **kw):
    if units <= 0: return
    s['serial'] += 1
    x = dict(id=s['serial'], origin=origin, site=site, category=category, units=units,
             state=state, born=s['hour'] if born is None else born, ready=s['hour'], **kw)
    s['lots'].append(x)
    return x

def new_game(scenario='stable', seed=42, difficulty='standard', name='National recovery plan', config=None):
    c = copy.deepcopy(config or CONFIG)
    sc = copy.deepcopy(next(x for x in SCENARIOS if x['id']==scenario))
    r = random.Random(seed)
    s = dict(version=1,name=name,seed=seed,scenario=sc,config=c,difficulty=difficulty,hour=0,serial=0,
             rng=r.getstate(),lots=[],generated=0,disposed=0,initial=0,costs=dict(transport=0,labor=0,overtime=0,storage=0,investment=0),
             revenue=0,dispositions={k:0 for k in c['disposition_mix']},plans={},routing={},history=[],events=[],decisions=[],loads=[],
             totals=dict(tendered=0,accepted=0,rejected=0,received=0,staged=0,processed=0,on_time=0,processing_effort=0,processing_capacity=0),demand_override=1)
    for site, cfg in c['sites'].items():
        s['plans'][site] = dict(**{k:cfg[k] for k in ('receiving','warehouse','processing','dispatch','appointments')},
            overtime=0,temporary=0,hold=False,expedite=False,supplemental=0,carrier='Value Freight',priority='Oldest first',invest=False)
    for i in range(c['dc_count']):
        origin=f'DC-{i+1:02}'
        site='IND' if i < round(c['dc_count']*c['sites']['IND']['share']) else 'EAST'
        s['routing'][origin]=site
        for category, share in c['category_mix'].items():
            units=round(c['weekly_units']/7/c['dc_count']*share*c['sites'][site]['upstream_days'])
            lot(s,origin,site,category,units,'upstream',born=-24*c['sites'][site]['upstream_days'])
    for site,cfg in c['sites'].items():
        for cat,share in c['category_mix'].items():
            lot(s,'INITIAL',site,cat,round(c['weekly_units']/7*cfg['share']*cfg['yard_days']*share),'yard',born=-48)
            lot(s,'INITIAL',site,cat,round(c['weekly_units']/7*cfg['share']*share/2),'staging',born=-24)
    s['initial']=sum(x['units'] for x in s['lots'])
    s['removal_baseline']=initialize_forecast(c,sc['start_date'],difficulty)
    s['removal_actuals']=[0]*len(s['removal_baseline'])
    s['site_processed']={site:0 for site in s['plans']}
    s['rng']=r.getstate()
    snapshot(s,0)
    invariant(s)
    return s

def date(s, hour=None):
    return datetime.fromisoformat(s['scenario']['start_date'])+timedelta(hours=s['hour'] if hour is None else hour)

def seasonal(s, hour=None):
    d=date(s,hour); c=s['config']
    if (d.month==12 and d.day>=c['holiday_start']) or (d.month==1 and d.day<=7): return c['holiday_multiplier']
    return c['seasonality'].get(str(d.month),1)

def inventory(s, site=None):
    sums={k:0 for k in STATES}
    for x in s['lots']:
        if site is None or x['site']==site: sums[x['state']]+=x['units']
    return sums

def validate_action(s, action):
    a=Action.model_validate(action).model_dump()
    for site,p in a['sites'].items():
        if sum(p[k] for k in ('receiving','warehouse','processing'))+p['temporary']>s['config']['sites'][site]['max_workers']:
            raise ValueError(f'{site}: labor exceeds available roster; reallocate or reduce staffing')
    if any(dc not in s['routing'] for dc in a['routing']): raise ValueError('Unknown DC routing origin')
    return a

def apply_action(s, action):
    a=validate_action(s,action)
    before={k:inventory(s,k) for k in s['plans']}
    for site,p in a['sites'].items():
        if p['invest']:
            s['config']['sites'][site]['equipment']+=s['config']['equipment_increment']
            s['costs']['investment']+=s['config']['equipment_cost']
        s['plans'][site]={**p,'invest':False}
    for dc,site in a['routing'].items():
        s['routing'][dc]=site
        for x in s['lots']:
            if x['origin']==dc and x['state']=='upstream': x['site']=site
    s['demand_override']=a['demand_override']
    s['decisions'].append(dict(hour=s['hour'],action=a,before=before,after={k:inventory(s,k) for k in s['plans']},cost=sum(s['costs'].values()),score=scorecard(s)['overall']))

def capacity(s,site,department,r=None):
    c=s['config'];p=s['plans'][site];cfg=c['sites'][site]
    staff=p[department]+(p['temporary'] if department=='processing' else 0)
    hours=c['effective_hours']*(1+p['overtime']/8)
    factor=cfg['equipment']
    if department=='processing' and site=='IND': factor*=s['scenario']['equipment_factor']
    for e in s['events']:
        if e['start']<=s['hour']<e['end'] and e['site']==site:
            if e['kind']=='Equipment failure' and department=='processing': factor*=e['magnitude']
            if e['kind']=='Labor shortage': factor*=e['magnitude']
    attendance=c['attendance'] if r is None else max(0,min(1,r.gauss(c['attendance'],0.025)))
    return int(staff*c['productivity'][department]*hours*attendance*factor)

def weekly_throughput(s, site, hour=None):
    """Physical units, separate from labor's category-adjusted effort budget."""
    cfg=s['config']['sites'][site]
    defaults=CONFIG['sites'][site]
    normal=cfg.get('weekly_throughput', defaults['weekly_throughput'])
    if site=='EAST' and date(s,hour).month in (6,7):
        normal=cfg.get('summer_weekly_throughput',defaults['summer_weekly_throughput'])
    maximum=cfg.get('max_weekly_throughput',defaults['max_weekly_throughput'])
    return dict(normal=normal,maximum=maximum,operating=min(maximum,round(normal*(1+s['plans'][site]['overtime']/8))))

def move(s,x,amount,state):
    amount=min(x['units'],max(0,int(amount)))
    if amount<=0:return
    x['units']-=amount
    return lot(s,x['origin'],x['site'],x['category'],amount,state,born=x['born'])

def hour_step(s):
    c=s['config'];r=rng_for(s);h=s['hour'];s['hour']+=1
    if h%24==0:
        if r.random()<c['event_probability']*24:
            kind=r.choice(['Carrier disruption','Equipment failure','Labor shortage','Demand spike','Trailer shortage','Appointment congestion'])
            duration=r.randint(*c['event_duration'])
            s['events'].append(dict(kind=kind,site=r.choice(list(s['plans'])),start=h,end=h+duration,magnitude=c['event_magnitude'],recovery='Automatically clears at end hour'))
    # Hourly synthetic generation, consolidated into daily lots by origin/category.
    upstream={(x['origin'],x['category']):x for x in s['lots'] if x['state']=='upstream' and x['born']//24==h//24}
    for dc,site in s['routing'].items():
        spike=1
        if any(e['kind']=='Demand spike' and e['site']==site and e['start']<=h<e['end'] for e in s['events']):spike=1/c['event_magnitude']
        for cat,share in c['category_mix'].items():
            pulse=c['monthly_removal_multiplier'] if cat=='DC Salvage' and date(s,h).day==c['monthly_removal_day'] else 1
            n=round(c['weekly_units']/168/c['dc_count']*share*seasonal(s,h)*pulse*spike*r.uniform(.8,1.2)*(1.1 if s['difficulty']=='hard' else 1))
            s['generated']+=n
            if 'removal_actuals' in s:s['removal_actuals'][h//168]+=n
            if n<=0:continue
            key=(dc,cat)
            if key in upstream: upstream[key]['units']+=n
            else:upstream[key]=lot(s,dc,site,cat,n,'upstream',born=h)
    active=[e for e in s['events'] if e['start']<=h<e['end']]
    for site,p in s['plans'].items():
        cfg=c['sites'][site]; carrier=c['carriers'][p['carrier']]
        # Per-day release slots distributed across hours, with active trailers occupying capacity.
        available=p['dispatch']+p['supplemental']
        if any(e['kind']=='Trailer shortage' and e['site']==site for e in active):available=int(available*c['event_magnitude'])
        slots=((h%24+1)*available//24)-(h%24*available//24)
        occupied=sum(1 for x in s['lots'] if x['site']==site and x['state'] in ('tender','pickup','transit','yard'))
        slots=min(slots,max(0,cfg['trailers']+p['supplemental']-occupied))
        upstream_lots=sorted([x for x in s['lots'] if x['site']==site and x['state']=='upstream' and x['units']>0],key=lambda x:(0 if p['priority']=='Oldest first' or x['category']==p['priority'] else 1,x['born']))
        if not p['hold']:
            for x in upstream_lots:
                while slots>0 and x['units']>0:
                    shipment=move(s,x,c['trailer_units'],'tender');shipment.update(ready=s['hour']+r.randint(*c['tender_delay']),carrier=p['carrier'],expedite=p['expedite'])
                    s['totals']['tendered']+=1;slots-=1
                if slots<=0:break
        # Tender acceptance, pickup and transit must all complete in order.
        for x in list(s['lots']):
            if x['site']!=site or x['ready']>s['hour'] or x['units']==0: continue
            if x['state']=='tender':
                acceptance=c['carriers'][x['carrier']]['acceptance']*s['scenario']['acceptance_factor']
                if any(e['kind']=='Carrier disruption' and e['site']==site for e in active):acceptance*=c['event_magnitude']
                if r.random()<acceptance:
                    x.update(state='pickup',ready=s['hour']+r.randint(*c['pickup_delay']));s['totals']['accepted']+=1
                else:
                    x.update(state='upstream',ready=s['hour']+1);s['totals']['rejected']+=1
            elif x['state']=='pickup':
                transit=max(1,round(r.randint(*c['transit_hours'])*c['carriers'][x['carrier']]['transit_factor']*(.5 if x['expedite'] else 1)))
                x.update(state='transit',depart=s['hour'],ready=s['hour']+transit)
                s['costs']['transport']+=c['carriers'][x['carrier']]['rate']*(c['expedite_multiplier'] if x['expedite'] else 1)+(c['supplemental_load_cost'] if p['supplemental'] else 0)
        inv=inventory(s,site)
        appointments=int(p['appointments']*s['scenario']['appointment_factor'])
        if any(e['kind']=='Appointment congestion' and e['site']==site for e in active):appointments=int(appointments*c['event_magnitude'])
        for x in sorted(s['lots'],key=lambda x:x['born']):
            if x['site']==site and x['state']=='transit' and x['ready']<=s['hour'] and appointments>0 and inv['yard']+x['units']<=cfg['yard_capacity']:
                x.update(state='yard',arrive=s['hour']);inv['yard']+=x['units'];appointments-=1
                s['loads'].append({k:x.get(k) for k in ('id','origin','site','category','units','depart','arrive','carrier')})
        # A lot may only move one department per hour. Processing consumes effort, not just units.
        eligible=sorted(s['lots'],key=lambda x:(0 if p['priority']=='Oldest first' or x['category']==p['priority'] else 1,x['born']))
        throughput=weekly_throughput(s,site,h)['operating']
        units_left=((h%168+1)*throughput//168)-(h%168*throughput//168)
        for source,dest,dept,counter in [('staging',None,'processing','processed'),('receiving','staging','warehouse','staged'),('yard','receiving','receiving','received')]:
            budget=capacity(s,site,dept,r)
            if dept=='processing':s['totals']['processing_capacity']+=budget
            room=cfg['queue_capacity']-sum(y['units'] for y in s['lots'] if y['site']==site and y['state']==dest) if dest else float('inf')
            for x in eligible:
                if x['site']!=site or x['state']!=source or x['units']<=0:continue
                effort=c['effort'][x['category']] if dept=='processing' else 1
                n=min(x['units'],int(budget/effort),room,units_left if dept=='processing' else float('inf'))
                if n<=0:continue
                budget-=n*effort;s['totals'][counter]+=n
                if dest:
                    move(s,x,n,dest);room-=n
                else:
                    units_left-=n
                    s.setdefault('site_processed',{}).setdefault(site,0)
                    s['site_processed'][site]+=n
                    x['units']-=n;s['disposed']+=n;s['totals']['processing_effort']+=n*effort
                    if s['hour']-x['born']<=c['score_targets']['service_hours']:s['totals']['on_time']+=n
                    value=c['recovery'][x['category']]*(c['high_value_share']*c['high_value_multiplier']+(1-c['high_value_share'])*c['low_value_multiplier'])
                    s['revenue']+=n*value
                    remaining=n
                    for i,(disposition,share) in enumerate(c['disposition_mix'].items()):
                        count=remaining if i==len(c['disposition_mix'])-1 else int(n*share)
                        s['dispositions'][disposition]+=count;remaining-=count
        workers=sum(p[k] for k in ('receiving','warehouse','processing'))
        s['costs']['labor']+=(workers*c['labor_rate']+p['temporary']*c['temp_rate'])*c['effective_hours']
        s['costs']['overtime']+=(workers*c['labor_rate']+p['temporary']*c['temp_rate'])*c['effective_hours']*p['overtime']/8*c['overtime_multiplier']
    s['lots']=[x for x in s['lots'] if x['units']>0]
    s['costs']['storage']+=sum(x['units'] for x in s['lots'] if x['state']!='transit')*c['storage_unit_hour']
    s['loads']=s['loads'][-120:];s['rng']=r.getstate()
    invariant(s)
    if s['hour']%8==0:snapshot(s,s['totals']['processed']-s.get('last_processed',0));s['last_processed']=s['totals']['processed']

def invariant(s):
    assert s['initial']+s['generated']==s['disposed']+sum(x['units'] for x in s['lots']), 'Freight conservation violated'
    ids=set()
    for x in s['lots']:
        assert x['id'] not in ids;ids.add(x['id'])
        assert x['units']>0 and x['state'] in STATES
        if x['state'] in ('tender','pickup','transit'):assert x['units']<=s['config']['trailer_units']
        if 'arrive' in x:assert x['arrive']>=x['depart']
    assert all(v>=0 for v in s['costs'].values())
    assert sum(s['dispositions'].values())==s['disposed']
    for site,cfg in s['config']['sites'].items():
        inv=inventory(s,site)
        assert inv['yard']<=cfg['yard_capacity']
        assert inv['receiving']<=cfg['queue_capacity'] and inv['staging']<=cfg['queue_capacity']

def advance(s,hours):
    for _ in range(min(hours,s['config']['horizon_days']*24-s['hour'])):
        hour_step(s)
    return s

def scorecard(s):
    c=s['config'];t=c['score_targets'];n=s['disposed'];inv=inventory(s);daily=max(1,c['weekly_units']/7*seasonal(s))
    clamp=lambda v:round(max(0,min(100,v)),1)
    scores=dict(service=clamp(100*s['totals']['on_time']/max(1,n)) if n else 100,
        finance=clamp(100*(1-(sum(s['costs'].values())/max(1,n)-t['cost_per_unit'])/t['cost_per_unit'])) if n else 50,
        backlog=clamp(100*(1-sum(inv.values())/daily/t['backlog_days'])),
        transport=clamp(100*s['totals']['accepted']/max(1,s['totals']['accepted']+s['totals']['rejected'])/t['transport_acceptance']) if s['totals']['accepted'] else 100,
        labor=clamp(100*s['totals']['processing_effort']/max(1,s['totals']['processing_capacity'])),
        recovery=clamp(100*s['revenue']/max(1,n)/t['recovery_per_unit']) if n else 50,
        stability=clamp(100*(1-inv['yard']/daily/t['stability_days'])))
    scores['overall']=round(sum(scores[k]*w for k,w in c['score_weights'].items()),1)
    return scores

def terminal(s):
    lost=sum(inventory(s).values())/max(1,s['config']['weekly_units']/7*seasonal(s))>s['config']['loss_backlog_days']
    complete=s['hour']>=s['config']['horizon_days']*24
    return dict(done=complete,backlog_warning=lost,outcome=('lost' if lost else 'won' if scorecard(s)['overall']>=s['config']['success_score'] else 'completed below target') if complete else 'continuing')

def snapshot(s,throughput):
    inv=inventory(s)
    s['history'].append(dict(hour=s['hour'],date=date(s).isoformat(),backlog=sum(inv.values()),upstream=inv['upstream']+inv['tender']+inv['pickup'],yard=inv['yard'],throughput=throughput,cost=sum(s['costs'].values()),revenue=s['revenue'],score=scorecard(s)['overall']))

def observe(s):
    c=s['config']; inv=inventory(s);sc=scorecard(s)
    sites={}
    for site,cfg in c['sites'].items():
        q=inventory(s,site);daily=max(1,c['weekly_units']/7*cfg['share']*seasonal(s))
        sites[site]=dict(name=cfg['name'],inventory=q,plan=s['plans'][site],capacity={d:capacity(s,site,d) for d in ('receiving','warehouse','processing')},
            weekly_throughput=weekly_throughput(s,site),processed=s.get('site_processed',{}).get(site,0),
            yard_capacity=cfg['yard_capacity'],max_workers=cfg['max_workers'],upstream_days=round(sum(q[k] for k in ('upstream','tender','pickup'))/daily,1),yard_days=round(q['yard']/daily,1),
            utilization=round(q['yard']/cfg['yard_capacity']*100,1),equipment=cfg['equipment'])
    forecasts=[]
    for day in range(7):
        hour=s['hour']+day*24
        forecasts.append(dict(day=date(s,hour).strftime('%b %d'),demand=round(sum(expected_removals(c,s['scenario']['start_date'],h,s['difficulty']) for h in range(hour,hour+24))*s['demand_override']),capacity=sum(min(capacity(s,site,'processing')*24,weekly_throughput(s,site,hour)['operating']/7) for site in sites)))
    return dict(name=s['name'],seed=s['seed'],scenario=s['scenario'],hour=s['hour'],date=date(s).isoformat(),inventory=inv,sites=sites,
        generated=s['generated'],initial=s['initial'],disposed=s['disposed'],costs=s['costs'],revenue=s['revenue'],dispositions=s['dispositions'],totals=s['totals'],
        score=sc,reward=sc['overall']/100,terminal=terminal(s),history=s['history'],events=s['events'][-100:],decisions=s['decisions'][-100:],loads=s['loads'],
        forecasts=forecasts,annual_forecast=annual_forecast(s),routing=s['routing'],store_count=c['store_count'],dc_count=c['dc_count'],demand_override=s['demand_override'],
        origins={dc:{k:sum(x['units'] for x in s['lots'] if x['origin']==dc and x['state']==k) for k in STATES} for dc in s['routing']},
        available_actions=dict(sites='Staffing, overtime, temporary labor, dispatch, appointments, holds, carrier, expedite, supplemental capacity, priority, equipment investment',routing='DC-to-return-center assignment',demand_override='Planning forecast only'),
        constraints=dict(trailer_units=c['trailer_units'],investment_cost=c['equipment_cost'],horizon_days=c['horizon_days'],success_score=c['success_score']),score_rules=dict(weights=c['score_weights'],targets=c['score_targets']))

def preview(s,action):
    clone=copy.deepcopy(s);apply_action(clone,action);advance(clone,24)
    baseline=copy.deepcopy(s);advance(baseline,24)
    a=observe(clone);b=observe(baseline)
    return dict(hours=24,baseline=dict(backlog=sum(b['inventory'].values()),processed=b['disposed']-s['disposed'],cost=sum(b['costs'].values())-sum(s['costs'].values()),score=b['score']['overall']),
        proposed=dict(backlog=sum(a['inventory'].values()),processed=a['disposed']-s['disposed'],cost=sum(a['costs'].values())-sum(s['costs'].values()),score=a['score']['overall']))
