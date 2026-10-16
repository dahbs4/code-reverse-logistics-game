import copy
import json
import pytest
from simulation.engine import (new_game,advance,inventory,invariant,apply_action,preview,seasonal,capacity,observe,CONFIG,terminal)
from simulation.models import Action

def quiet(scenario='stable',seed=42):
    c=copy.deepcopy(CONFIG);c['event_probability']=0
    return new_game(scenario,seed,config=c)

def plan(s,site='IND',**changes):
    return {'sites':{site:{**s['plans'][site],**changes}}}

@pytest.mark.parametrize('scenario',['stable','crisis','peak','breakdown'])
def test_freight_conservation_and_hourly_invariants(scenario):
    s=quiet(scenario);advance(s,72);invariant(s)
    assert s['initial']+s['generated']==s['disposed']+sum(inventory(s).values())
    assert s['disposed']>0 and s['hour']==72
    assert all(n>=0 for n in inventory(s).values())
    assert all(n>=0 for n in s['costs'].values())
    assert len({x['id'] for x in s['lots']})==len(s['lots'])


def test_reproducibility_and_save_load_rng():
    a=quiet();b=quiet();advance(a,24);advance(b,24)
    assert a==b
    restored=json.loads(json.dumps(a));advance(a,24);advance(restored,24)
    assert json.dumps(a,sort_keys=True)==json.dumps(restored,sort_keys=True)


def test_step_partition_consistency():
    a=quiet();b=quiet();advance(a,48)
    for _ in range(6):advance(b,8)
    assert a==b


def test_hold_increases_upstream_and_releases_no_tenders():
    a=quiet();b=quiet()
    for site in b['plans']:apply_action(b,plan(b,site,hold=True))
    advance(a,48);advance(b,48)
    assert b['totals']['tendered']==0
    assert inventory(b)['upstream']>inventory(a)['upstream']


def test_rejection_and_retender():
    s=quiet();s['scenario']['acceptance_factor']=0
    advance(s,24)
    assert s['totals']['rejected']>0 and s['totals']['accepted']==0
    assert inventory(s)['transit']==0
    s['scenario']['acceptance_factor']=1
    advance(s,48)
    assert s['totals']['accepted']>0 and s['loads']
    assert all(x['units']<=s['config']['trailer_units'] and x['arrive']>x['depart'] for x in s['loads'])


def test_appointments_block_arrivals():
    s=quiet()
    for site in s['plans']:apply_action(s,plan(s,site,appointments=0))
    advance(s,72)
    assert not s['loads'] and inventory(s)['transit']>0


def test_receiving_bottleneck_cannot_be_fixed_by_processing():
    s=quiet()
    for site in s['plans']:apply_action(s,plan(s,site,receiving=0,warehouse=0,processing=130 if site=='IND' else 100))
    start={k:inventory(s,k)['yard'] for k in s['plans']}
    advance(s,48)
    assert s['totals']['received']==0 and s['totals']['staged']==0
    assert inventory(s)['yard']>=sum(start.values())
    assert s['disposed']<=round(s['config']['weekly_units']/7/2)+5


def test_processing_capacity_and_backlog_carryover():
    s=quiet()
    for site in s['plans']:apply_action(s,plan(s,site,processing=0))
    advance(s,48)
    assert s['disposed']==0 and inventory(s)['staging']>0
    assert s['totals']['received']>0


def test_financial_accounting_and_investment():
    s=quiet();p=plan(s,invest=True,overtime=2,temporary=10,expedite=True,supplemental=3)
    apply_action(s,p);assert s['costs']['investment']==CONFIG['equipment_cost']
    assert s['config']['sites']['IND']['equipment']==1.15
    advance(s,48)
    assert all(s['costs'][k]>0 for k in ['labor','overtime','transport','storage'])
    assert sum(s['dispositions'].values())==s['disposed']
    assert s['revenue']>0
    assert s['plans']['IND']['invest'] is False


def test_seasonality():
    s=quiet('peak');assert seasonal(s)==2
    assert seasonal(s,12*24)==4.05
    assert CONFIG['weekly_units']*seasonal(s,12*24)==4455000
    s['scenario']['start_date']='2026-11-01';assert seasonal(s)==2
    s['scenario']['start_date']='2026-09-01';assert seasonal(s)==1


def test_preview_is_nonmutating_and_commit_only():
    s=quiet();before=copy.deepcopy(s)
    p=preview(s,plan(s,dispatch=0))
    assert s==before and p['hours']==24
    apply_action(s,plan(s,dispatch=0));assert s['hour']==0 and s['plans']['IND']['dispatch']==0


def test_all_action_fields_and_routing():
    s=quiet();a=plan(s,receiving=30,warehouse=50,processing=90,overtime=2,temporary=5,dispatch=80,appointments=8,
                         hold=True,expedite=True,supplemental=4,carrier='National Express',priority='Mail-In Returns',invest=True)
    a.update(routing={'DC-01':'EAST'},demand_override=1.4)
    apply_action(s,a)
    assert s['routing']['DC-01']=='EAST'
    assert all(x['site']=='EAST' for x in s['lots'] if x['origin']=='DC-01')
    assert observe(s)['forecasts'][0]['demand']>CONFIG['weekly_units']/7
    advance(s,8);invariant(s)


def test_invalid_actions_do_not_mutate():
    s=quiet();before=copy.deepcopy(s)
    with pytest.raises(ValueError):apply_action(s,plan(s,receiving=250,warehouse=200,processing=300))
    assert s==before
    with pytest.raises(ValueError):apply_action(s,{'routing':{'DC-99':'IND'}})
    with pytest.raises(ValueError):Action.model_validate(plan(s,dispatch=-1))


def test_forecast_override_does_not_change_actual_demand():
    a=quiet();b=quiet();apply_action(b,{'demand_override':2});advance(a,24);advance(b,24)
    assert a['generated']==b['generated']


def test_event_impact_and_recovery():
    s=quiet();base=capacity(s,'IND','processing')
    s['events']=[dict(kind='Equipment failure',site='IND',start=0,end=8,magnitude=.5)]
    assert capacity(s,'IND','processing')==int(base*.5) or abs(capacity(s,'IND','processing')-base*.5)<1
    advance(s,8);assert capacity(s,'IND','processing')==base


def test_yard_capacity_and_queues():
    s=quiet()
    for site in s['plans']:apply_action(s,plan(s,site,receiving=0,dispatch=200,appointments=20))
    advance(s,96);invariant(s)
    for site,cfg in s['config']['sites'].items():assert inventory(s,site)['yard']<=cfg['yard_capacity']


def test_processing_never_exceeds_available_work():
    s=quiet();s['config']['weekly_units']=0
    for x in s['lots']:x['units']=0
    s['lots']=[];s['initial']=0
    advance(s,8)
    assert s['disposed']==0


def test_trailer_pool_limits_outstanding_loads():
    s=quiet()
    for site in s['plans']:
        s['config']['sites'][site]['trailers']=5
        apply_action(s,plan(s,site,receiving=0,appointments=0,dispatch=200))
    advance(s,48)
    for site in s['plans']:
        occupied=[x for x in s['lots'] if x['site']==site and x['state'] in ('tender','pickup','transit','yard')]
        assert len(occupied)<=5
    assert inventory(s)['upstream']>0


def test_exact_one_hour_labor_cost_and_recovery():
    s=quiet();c=s['config'];advance(s,1)
    expected=sum(sum(p[k] for k in ('receiving','warehouse','processing'))*c['labor_rate']*c['effective_hours'] for p in s['plans'].values())
    assert s['costs']['labor']==pytest.approx(expected)
    assert s['costs']['overtime']==0 and s['costs']['transport']==0
    assert s['disposed']==s['totals']['processed']


def test_monthly_dc_removal_pulse():
    a=quiet();b=quiet();a['scenario']['start_date']='2026-09-14';b['scenario']['start_date']='2026-09-15'
    advance(a,8);advance(b,8)
    assert b['generated']>a['generated']*1.4


def test_demand_disruption_changes_actual_generation():
    a=quiet();b=quiet()
    b['events']=[dict(kind='Demand spike',site='IND',start=0,end=24,magnitude=.5)]
    advance(a,8);advance(b,8)
    assert b['generated']>a['generated']


def test_more_processing_cannot_consume_missing_inventory():
    s=quiet();initial=sum(x['units'] for x in s['lots'] if x['state']=='staging')
    for site in s['plans']:apply_action(s,plan(s,site,receiving=0,warehouse=0,processing=150,overtime=4))
    advance(s,48)
    assert s['disposed']==initial
    assert inventory(s)['staging']==0


def test_terminal_horizon_and_scoring_bounds():
    s=quiet();s['config']['horizon_days']=1
    advance(s,168)
    assert s['hour']==24 and terminal(s)['done']
    before=copy.deepcopy(s);advance(s,24);assert s==before
    assert all(0<=v<=100 for v in observe(s)['score'].values())


def test_different_seed_changes_actual_demand():
    a=quiet(seed=42);b=quiet(seed=137);advance(a,8);advance(b,8)
    assert a['generated']!=b['generated']
