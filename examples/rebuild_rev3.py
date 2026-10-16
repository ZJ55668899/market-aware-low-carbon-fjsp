"""Rebuild revision 3 without rerunning optimization. Python standard library only.

Source archives are unchanged snapshots from public commit 81cdfd8. Experiment
configurations below are reconstructed from that commit's run_c1_rev2.py order
and checked against EVERY archived planning objective before results are used.
The rev3 price pool uses existing E3 four-price fronts and the first four E1
BASE fronts within each run. It replaces the separate, summary-only old pool.
"""
from pathlib import Path
import sys, json, hashlib, statistics, math, copy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from fjsp import instance as instmod
from fjsp.instance import gear_shaft_instance, load_brandimarte
from fjsp.schedule import decode
from fjsp.c1_model import TOUSpeedCarbonModel, FlatUnifiedModel, TOU_MULTIPLIER
from fjsp.metrics import pareto_set, c_metric

OUT = ROOT/'data/results/rev3'
OUT.mkdir(parents=True, exist_ok=True)
PRICES = [0.0, 0.08, 0.8, 2.0]
SOURCE_COMMIT = '81cdfd8751e27f31d2a619e24d493f61b09f917a'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, obj):
    # Stable bytes on Windows and Unix, including for manifest verification.
    (OUT/name).write_bytes(json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8'))

def configurations(entries, cap):
    configs = []
    def add(start, end, experiment, variant, tou=False, trade=False, price=0.08,
            origin=0.0, idle=0.2, multipliers=None, cap_value=None):
        for i in range(start,end):
            configs.append(dict(entry_index=i, experiment=experiment, variant=variant,
                tou=tou, cap_trade=trade, carbon_price=price, origin_min=origin,
                idle_ratio=idle, carbon_cap_kg=cap if cap_value is None else cap_value,
                tou_multipliers=multipliers or dict(peak=1.6,flat=1.0,valley=0.4)))
    add(0,6,'anchor','BASE')
    add(6,12,'E1','C1',True,True)
    add(12,18,'E1','BASE')
    add(18,24,'E1','CTRL')
    add(24,30,'E2','full',True,True)
    add(30,36,'E2','no-TOU',False,True)
    add(36,42,'E2','no-speed',True,True)
    add(42,48,'E2','no-trade',True,False)
    for j,pc in enumerate(PRICES):
        add(48+4*j,52+4*j,'E3',str(pc),True,True,price=pc)
    for j,origin in enumerate([0,360,480]):
        add(64+8*j,68+8*j,'E4','BASE',origin=origin)
        add(68+8*j,72+8*j,'E4','C1',True,True,origin=origin)
    for j,idle in enumerate([0.0,0.1,0.2]):
        for k,spread in enumerate(['flat','wide']):
            start=88+12*j+6*k
            cap2=statistics.median(o[2] for e in entries[start:start+3] for o in e['objectives'])
            mult=dict(peak=1.0,flat=1.0,valley=1.0) if spread=='flat' else dict(peak=1.6,flat=1.0,valley=0.4)
            add(start,start+3,'E5-anchor',spread,idle=idle,multipliers=mult,cap_value=cap2)
            add(start+3,start+6,'E5',spread,True,True,idle=idle,multipliers=mult,cap_value=cap2)
    assert [x['entry_index'] for x in configs]==list(range(124))
    return configs

def make_inst(name, ratio=0.2):
    old=instmod.IDLE_RATIO
    instmod.IDLE_RATIO=ratio
    try:
        return gear_shaft_instance() if name=='gear' else load_brandimarte(str(ROOT/'instances'/f'{name}.fjs'))
    finally:
        instmod.IDLE_RATIO=old

def evaluate(inst, chrom, speeds, cap, pc=0.08, tou=True, trade=True, origin=0.0, mult=None):
    old=dict(TOU_MULTIPLIER)
    if mult is not None:
        TOU_MULTIPLIER.clear();TOU_MULTIPLIER.update(mult)
    try:
        model=TOUSpeedCarbonModel(tou=tou,cap_trade=trade,carbon_cap_kg=cap,carbon_price=pc,origin=origin)
        sch=decode(inst,chrom[0],chrom[1],chrom[2] if speeds else None)
        model.evaluate(inst,sch)
        return sch
    finally:
        TOU_MULTIPLIER.clear();TOU_MULTIPLIER.update(old)

def vals(sch):
    return [sch.makespan,sch.cost,sch.carbon]

main={};aux={}
for name in ['gear','Mk04']:
    ap=ROOT/'data/results'/f'archive_{name}.json'
    sp=ROOT/'data/results'/f'c1_rev2_{name.lower()}.json'
    source=json.loads(sp.read_text())
    assert sha(ap)==source['archive_sha256']
    entries=json.loads(ap.read_text())['entries']
    configs=configurations(entries,source['cap'])
    insts={r:make_inst(name,r) for r in [0.0,0.1,0.2]}
    max_error=0.0
    for c,e in zip(configs,entries):
        for chrom,expected in zip(e['chromosomes'],e['objectives']):
            sch=evaluate(insts[c['idle_ratio']],chrom,e['speeds'],c['carbon_cap_kg'],
                pc=c['carbon_price'],tou=c['tou'],trade=c['cap_trade'],origin=c['origin_min'],mult=c['tou_multipliers'])
            max_error=max(max_error,max(abs(x-y) for x,y in zip(vals(sch),expected)))
    assert max_error<1e-6, (name,max_error)
    write(f'archive_mapping_{name}.json',dict(source_archive=ap.name,source_sha256=sha(ap),
        source_commit=SOURCE_COMMIT,max_planning_objective_error=max_error,entries=configs))
    inst=insts[0.2];cap=source['cap']
    groups={'BASE':list(range(12,18)),'CTRL':list(range(18,24)),'C1':list(range(6,12))}
    fronts={}; run_points={}; selected={}
    for label,indices in groups.items():
        all_points=[];best_run=[]
        for ei in indices:
            e=entries[ei];points=[]
            for j,ch in enumerate(e['chromosomes']):
                sch=evaluate(inst,ch,e['speeds'],cap)
                p=dict(id=f'{ei:03d}:{j:03d}',entry=ei,index=j,seed=e['seed'],objectives=vals(sch),breakdown=sch.breakdown)
                points.append(p)
            best_run.append(min(points,key=lambda p:p['objectives'][1]))
            all_points.extend(points)
        indices_nd=pareto_set([p['objectives'] for p in all_points])
        fronts[label]=[all_points[i] for i in indices_nd]
        selected[label]=min(fronts[label],key=lambda p:p['objectives'][1])
        run_points[label]=best_run
    stats={}
    for a,b in [('CTRL','BASE'),('C1','CTRL'),('C1','BASE')]:
        stats[f'{a}-{b}']={}
        for dim,key in enumerate(['makespan','cost','carbon']):
            ds=[x['objectives'][dim]-y['objectives'][dim] for x,y in zip(run_points[a],run_points[b])]
            mu=statistics.mean(ds);sd=statistics.pstdev(ds)
            half=2.5705818356*statistics.stdev(ds)/math.sqrt(6)
            stats[f'{a}-{b}'][key]=dict(differences=ds,mean=mu,sd_n=sd,sd_sample=statistics.stdev(ds),t95=[mu-half,mu+half])
    metrics={}
    for a,b in [('C1','BASE'),('BASE','C1'),('CTRL','BASE'),('BASE','CTRL'),('C1','CTRL'),('CTRL','C1')]:
        aa=[p['objectives'] for p in fronts[a]];bb=[p['objectives'] for p in fronts[b]]
        metrics[a+'>'+b]=dict(multiset=c_metric(aa,bb),unique=c_metric(list(dict.fromkeys(map(tuple,aa))),list(dict.fromkeys(map(tuple,bb)))))
    # E6 signed values are recomputed, original legacy records are left unchanged.
    shifts=[]
    for ratio_a,ratio_b in [(0.9,1.0),(1.0,1.1)]:
        sch_a=evaluate(inst,entries[selected['C1']['entry']]['chromosomes'][selected['C1']['index']],True,cap*ratio_a)
        sch_b=evaluate(inst,entries[selected['C1']['entry']]['chromosomes'][selected['C1']['index']],True,cap*ratio_b)
        shifts.append(sch_b.cost-sch_a.cost)
    main[name]=dict(selected=selected,per_run=run_points,paired=stats,cmetric=metrics,
        front_objectives={label:[p['objectives'] for p in points] for label,points in fronts.items()},
        e6=dict(cap=cap,signed_shifts=shifts,expected_signed_shift=-0.08*0.1*cap),
        selection_tie_rule='minimum unrounded cost, then first source-order candidate')
    aux[name]={}
    for experiment in ['E2','E3','E4','E5']:
        grouped={}
        for config,e in zip(configs,entries):
            if config['experiment']!=experiment:continue
            key=config['variant']
            if experiment=='E4':key=f"origin{int(config['origin_min'])}/"+key
            if experiment=='E5':key=f"idle{config['idle_ratio']}/"+key
            for j,ch in enumerate(e['chromosomes']):
                sch=evaluate(insts[config['idle_ratio']],ch,e['speeds'],config['carbon_cap_kg'],
                    pc=config['carbon_price'],origin=config['origin_min'],mult=config['tou_multipliers'])
                grouped.setdefault(key,[]).append(dict(entry=config['entry_index'],index=j,
                    objectives=vals(sch),breakdown=sch.breakdown))
        for key,points in grouped.items():
            nd=pareto_set([p['objectives'] for p in points])
            aux[name].setdefault(experiment,{})[key]=min((points[i] for i in nd),key=lambda p:p['objectives'][1])
    print(name,'all archive objectives verified',max_error,flush=True)
    if name=='gear':
        pool_runs=[];per_price={str(pc):[] for pc in PRICES}
        for r in range(4):
            candidates=[]
            for ei in [12+r]+[48+4*k+r for k in range(4)]:
                e=entries[ei]
                for j,ch in enumerate(e['chromosomes']):
                    sch=evaluate(inst,ch,e['speeds'],cap,pc=0.0)
                    candidates.append(dict(id=f'{ei:03d}:{j:03d}',source_entry=ei,source_index=j,
                        source_seed=e['seed'],source_price=None if ei<18 else PRICES[(ei-48)//4],
                        cost_excl=sch.cost,carbon=sch.carbon,makespan=sch.makespan))
            chosen={}
            for pc in PRICES:
                best=min(candidates,key=lambda x:x['cost_excl']+pc*(x['carbon']-cap))
                selected_record=dict(id=best['id'],cost=best['cost_excl']+pc*(best['carbon']-cap),
                    cost_excl=best['cost_excl'],carbon=best['carbon'],makespan=best['makespan'])
                per_price[str(pc)].append(selected_record)
                chosen[str(pc)]=selected_record
            cs=[chosen[str(pc)]['carbon'] for pc in PRICES]
            assert all(b<=a+1e-8 for a,b in zip(cs,cs[1:]))
            pool_runs.append(dict(run=r,candidates=candidates,selected=chosen,
                same_id_zero_and_008=chosen['0.0']['id']==chosen['0.08']['id']))
        summary={}
        for pc,points in per_price.items():
            summary[pc]={key:dict(mean=statistics.mean(p[key] for p in points),sd_n=statistics.pstdev(p[key] for p in points))
                for key in ['cost','cost_excl','carbon','makespan']}
        pool=dict(protocol='rev3 archived-candidate within-run pool',source_commit=SOURCE_COMMIT,
            source_archive=ap.name,source_sha256=sha(ap),cap=cap,runs=4,prices=PRICES,
            pool_rule='E1 BASE runs 0-3 and E3 four-price runs 0-3; pool separately by run; no new search',
            gens=80,pop=150,selection_tie_rule='minimum unrounded net cost then first source-order candidate',
            per_price=summary,per_run=pool_runs)
        write('pricepool_gear_rev3.json',pool)
        print('rev3 pool means',json.dumps(summary),flush=True)
write('main_stats_rev3.json',main)
write('experiments_rev3.json',aux)
print('All revision 3 numerical files rebuilt from source archives',flush=True)
