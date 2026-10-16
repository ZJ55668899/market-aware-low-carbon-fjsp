"""Recreate the seven manuscript figures from revision 3 archived results."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/figures/rev3';OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data/results'
main=json.loads((DATA/'rev3/main_stats_rev3.json').read_text())
pool=json.loads((DATA/'rev3/pricepool_gear_rev3.json').read_text())
old=json.loads((DATA/'c1_rev2_gear.json').read_text())
plt.rcParams.update({'font.family':'Arial','font.size':11,'axes.labelsize':11,
 'xtick.labelsize':10,'ytick.labelsize':10,'legend.fontsize':10,'axes.linewidth':1.0,
 'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False,
 'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
BLUE='#0F4D92';GREEN='#2E7751';ORANGE='#BC6C25';GRAY='#767676'
def save(fig,n):
    for fmt in ['png','svg','pdf']:fig.savefig(OUT/f'figure{n}.{fmt}',dpi=400,bbox_inches='tight',pad_inches=.07)
    plt.close(fig)
def box(ax,x,y,w,h,label,fc='#EEF3F8',ec=BLUE,fs=11):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.02',
        lw=1.2,facecolor=fc,edgecolor=ec))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=fs)
def arrow(ax,a,b,color=BLUE):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,lw=1.2,color=color))

# Figure 1 is regenerated as a model schematic, with machine-specific ON gaps.
fig,ax=plt.subplots(figsize=(7.6,3.15));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
box(ax,.01,.45,.17,.33,'Decisions\nOrder / machine\nSpeed',fs=10.5)
box(ax,.23,.45,.26,.33,'Queue-append decode\nOperation times\nON gaps / busy blocks',fs=10.5)
box(ax,.54,.45,.19,.33,'Unified ledger\n'+r'$E_{proc}+E_{idle}+E_{ss}$',fs=10)
box(ax,.79,.59,.20,.30,'Total cost\nMaterial + labour\n+ bill + settlement',fc='#FFF3E8',ec=ORANGE,fs=10)
box(ax,.79,.15,.20,.24,'Carbon\n'+r'$F_o=\delta F_e$',fc='#EEF7EF',ec=GREEN,fs=10.5)
box(ax,.23,.02,.37,.20,'Scenario parameters\nTOU tariff '+r'$\pi(t)$'+' / carbon price '+r'$p_c$',fc='#FFF3E8',ec=ORANGE,fs=10)
arrow(ax,(.18,.62),(.23,.62));arrow(ax,(.49,.62),(.54,.62))
arrow(ax,(.73,.70),(.79,.74),ORANGE);arrow(ax,(.73,.49),(.79,.28),GREEN)
arrow(ax,(.60,.13),(.79,.59),ORANGE)
ax.text(.62,.95,'Every kWh is billed and carbon-counted',ha='center',fontsize=10)
save(fig,1)

fig,ax=plt.subplots(figsize=(7.8,5.0));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
box(ax,.03,.80,.94,.17,'Instance and scenario parameters\nProcessing alternatives / power / speed levels / tariff / carbon price',fs=12)
box(ax,.03,.52,.27,.19,'BASE\nFlat / fixed speed')
box(ax,.365,.52,.27,.19,'CTRL\nFlat / variable speed',fc='#EEF7EF',ec=GREEN)
box(ax,.70,.52,.27,.19,'C1\nTOU + carbon\nVariable speed',fc='#FFF3E8',ec=ORANGE,fs=11)
for x in [.165,.5,.835]:arrow(ax,(x,.8),(x,.71))
box(ax,.03,.24,.94,.19,'Queue-append earliest-start decoding\nNSGA-II with the same budget within each experiment family',fs=12)
for x in [.165,.5,.835]:arrow(ax,(x,.52),(x,.43))
box(ax,.03,.015,.94,.13,'Same-reality revaluation and non-dominated filtering\nMinimum-cost selection / paired run statistics / bidirectional C-metric',fs=11.5)
arrow(ax,(.50,.24),(.50,.145))
save(fig,2)

# Compact numeric figures use short group names, all defined in captions.
fig,axes=plt.subplots(1,3,figsize=(8.0,3.0))
colors={'BASE':GRAY,'CTRL':GREEN,'C1':ORANGE}
for ax,(i,j,xl,yl) in zip(axes,[(0,1,'Makespan (min)','Cost (CNY)'),(0,2,'Makespan (min)',r'Carbon (kgCO$_2$)'),(1,2,'Cost (CNY)',r'Carbon (kgCO$_2$)')]):
    for label,pts in main['gear']['front_objectives'].items():
        ax.scatter([p[i] for p in pts],[p[j] for p in pts],s=10,alpha=.58,color=colors[label],label=label,rasterized=False)
    ax.set(xlabel=xl,ylabel=yl);ax.grid(alpha=.14);ax.tick_params(axis='x',labelrotation=25)
handles,labels_legend=axes[0].get_legend_handles_labels()
fig.legend(handles,labels_legend,loc='upper center',bbox_to_anchor=(.52,1.0),ncol=3)
fig.subplots_adjust(left=.095,right=.985,bottom=.26,top=.82,wspace=.66);save(fig,3)

fig,axes=plt.subplots(1,3,figsize=(8.0,3.1))
names=list(old['E2']);labels=['Full','No TOU','No speed','No carbon']
for ax,key,yl in zip(axes,['makespan','cost','carbon'],['Makespan (min)','Cost (CNY)',r'Carbon (kgCO$_2$)']):
    values=[old['E2'][x][key] for x in names]
    ax.scatter(range(4),values,s=40,color=[ORANGE,BLUE,GRAY,GREEN],zorder=3)
    ax.set_xticks(range(4));ax.set_xticklabels(labels,rotation=35,ha='right');ax.set_ylabel(yl)
    ax.grid(alpha=.15,axis='y');ax.set_xlim(-.5,3.5);span=max(values)-min(values);ax.set_ylim(min(values)-span*.20,max(values)+span*.28)
    for x,y in enumerate(values):ax.annotate(f'{y:.1f}',(x,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
fig.tight_layout(w_pad=.8);save(fig,4)

# Four sampled prices are categorical points; no interpolation of a threshold.
fig,axes=plt.subplots(1,2,figsize=(7.6,3.3));prices=pool['prices'];xs=list(range(4))
for ax,key,yl,color in zip(axes,['carbon','cost_excl'],[r'Carbon (kgCO$_2$)','Cost excluding settlement (CNY)'],[GREEN,ORANGE]):
    mu=[pool['per_price'][str(p)][key]['mean'] for p in prices]
    sd=[pool['per_price'][str(p)][key]['sd_n'] for p in prices]
    ax.errorbar(xs,mu,yerr=sd,fmt='o',capsize=4,color=color,ms=6,lw=1.4)
    ax.set_xticks(xs);ax.set_xticklabels(['0','0.08','0.8','2.0'])
    ax.set(xlabel=r'Carbon price (CNY/kgCO$_2$)',ylabel=yl);ax.grid(alpha=.15,axis='y');ax.set_xlim(-.45,3.45)
fig.tight_layout(w_pad=1.4);save(fig,5)

fig,axes=plt.subplots(1,2,figsize=(8.0,3.4));records=old['E4_origins']
keys=[f'origin{o}/{m}' for o in [0,360,480] for m in ['BASE','C1']];xx=list(range(6));bottom=[0.0]*6
for tier,color in [('valley','#AADCA9'),('flat','#CFCECE'),('peak','#E9A6A1')]:
    yy=[records[k]['tier_kwh'].get(tier,0) for k in keys]
    axes[0].bar(xx,yy,bottom=bottom,color=color,edgecolor='white',linewidth=.6,label=tier)
    bottom=[a+b for a,b in zip(bottom,yy)]
axes[0].set_ylabel('Processing + idle energy (kWh)');axes[0].set_xticks(xx);axes[0].set_xticklabels(['B\n00:00','C1\n00:00','B\n06:00','C1\n06:00','B\n08:00','C1\n08:00'])
axes[0].legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.19),columnspacing=.8)
for m,c,marker in [('BASE',GRAY,'s'),('C1',ORANGE,'o')]:
    yy=[records[f'origin{o}/{m}']['carbon'] for o in [0,360,480]]
    axes[1].plot(range(3),yy,marker=marker,color=c,label=m,lw=1.4)
axes[1].set_xticks(range(3));axes[1].set_xticklabels(['00:00','06:00','08:00']);axes[1].set(xlabel='Shift origin',ylabel=r'Carbon (kgCO$_2$)');axes[1].legend();axes[1].grid(alpha=.15)
fig.tight_layout(w_pad=1.3);save(fig,6)

fig,axes=plt.subplots(1,2,figsize=(7.6,3.2))
for ax,key,yl in zip(axes,['cost','carbon'],['Cost (CNY)',r'Carbon (kgCO$_2$)']):
    for ratio,c,marker in [(0.0,BLUE,'o'),(0.1,ORANGE,'s'),(0.2,GREEN,'^')]:
        ys=[old['E5_idle_boundary'][f'idle{ratio}/{spread}'][key] for spread in ['flat','wide']]
        ax.plot([0,1],ys,marker=marker,label=f'Joint ratio {ratio:g}',color=c,lw=1.5)
    ax.set_xticks([0,1]);ax.set_xticklabels(['Flat','Wide']);ax.set(xlabel='Tariff scenario',ylabel=yl);ax.grid(alpha=.15)
axes[0].legend(fontsize=9);fig.tight_layout(w_pad=1.3);save(fig,7)
print('Seven figures regenerated in PNG SVG PDF')
