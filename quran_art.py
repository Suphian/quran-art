import importlib,sys, pkg_resources, subprocess
import os
from pathlib import Path
missing = [p for p in ['pandas','numpy','matplotlib','tqdm'] if importlib.util.find_spec(p) is None]
if missing:
    print('Missing packages detected. Please run: pip install -r requirements.txt')
    sys.exit(1)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from tqdm import tqdm

reqs = ['pandas','numpy','matplotlib','tqdm']
with open('requirements.txt','w') as f:
    for p in reqs:
        f.write(f"{p}=={pkg_resources.get_distribution(p).version}\n")

def detect_columns(df, options):
    for opt in options:
        if opt in df.columns:
            return opt
    raise KeyError(f"None of {options} found in columns")

def extract_number(feat):
    s = str(feat).lower()
    if 'dual' in s or 'du' in s:
        return 'dual'
    if 'plur' in s or 'pl' in s:
        return 'plural'
    return 'singular'

TURN_MAP = {
    (-1,-1):-60, (-1,0):-30, (-1,1):0,
    (0,-1):-15, (0,0):0, (0,1):15,
    (1,-1):30, (1,0):60, (1,1):90
}

STROKE_WIDTH = {'singular':0.6,'dual':1.0,'plural':1.4}

SURAH_NAMES = [
    'Al-Fatiha','Al-Baqara','Al Imran','An-Nisa','Al-Ma\'idah','Al-An\'am','Al-A\'raf','Al-Anfal','At-Tawbah','Yunus','Hud','Yusuf','Ar-Ra\'d','Ibrahim','Al-Hijr','An-Nahl','Al-Isra','Al-Kahf','Maryam','Ta-Ha','Al-Anbiya','Al-Hajj','Al-Mu\'minun','An-Nur','Al-Furqan','Ash-Shu\'ara','An-Naml','Al-Qasas','Al-\'Ankabut','Ar-Rum','Luqman','As-Sajdah','Al-Ahzab','Saba','Fatir','Ya-Sin','As-Saffat','Sad','Az-Zumar','Ghafir','Fussilat','Ash-Shura','Az-Zukhruf','Ad-Dukhan','Al-Jathiyah','Al-Ahqaf','Muhammad','Al-Fath','Al-Hujurat','Qaf','Adh-Dhariyat','At-Tur','An-Najm','Al-Qamar','Ar-Rahman','Al-Waqi\'ah','Al-Hadid','Al-Mujadila','Al-Hashr','Al-Mumtahanah','As-Saff','Al-Jumu\'ah','Al-Munafiqun','At-Taghabun','At-Talaq','At-Tahrim','Al-Mulk','Al-Qalam','Al-Haqqah','Al-Ma\'arij','Nuh','Al-Jinn','Al-Muzzammil','Al-Muddaththir','Al-Qiyamah','Al-Insan','Al-Mursalat','An-Naba','An-Nazi\'at','Abasa','At-Takwir','Al-Infitar','Al-Mutaffifin','Al-Inshiqaq','Al-Buruj','At-Tariq','Al-A\'la','Al-Ghashiyah','Al-Fajr','Al-Balad','Ash-Shams','Al-Layl','Ad-Duhaa','Ash-Sharh','At-Tin','Al-\'Alaq','Al-Qadr','Al-Bayyinah','Az-Zalzalah','Al-\'Adiyat','Al-Qari\'ah','At-Takathur','Al-Asr','Al-Humazah','Al-Fil','Quraysh','Al-Ma\'un','Al-Kawthar','Al-Kafirun','An-Nasr','Al-Masad','Al-Ikhlas','Al-Falaq','An-Nas'
]

def main(dataset='qac-with-id.tsv', outdir='output'):
    df = pd.read_csv(dataset, sep='\t', dtype=str)
    df.reset_index(drop=True, inplace=True)
    pos_col = detect_columns(df, ['pos','tag','morph','pos_tag'])
    head_col = detect_columns(df, ['head','parent','dep_parent','link'])
    surah_col = detect_columns(df, ['sura','surah','chapter'])
    ayah_col = detect_columns(df, ['ayah','verse'])
    token_col = detect_columns(df, ['token','word','position','index'])
    feature_col = detect_columns(df, ['feat','features','morph','tag'])

    df_dm = df[df[pos_col].str.contains('DM', na=False)].copy()
    index_map = {k:i for i,k in enumerate(df[token_col])}

    spatial = []
    temporal = []
    number = []
    for idx,row in df_dm.iterrows():
        head_id = row.get(head_col)
        head_pos = index_map.get(head_id, None)
        if head_pos is None:
            spatial.append(0)
        else:
            if head_pos < idx:
                spatial.append(-1)
            elif head_pos > idx:
                spatial.append(1)
            else:
                spatial.append(0)
        win = df.iloc[max(idx-3,0):min(idx+4,len(df))]
        verb_rows = win[win[feature_col].str.contains('PERF|IMPF|JUS|IMPV', na=False)]
        if verb_rows.empty:
            temporal.append(0)
        else:
            nearest_index = (verb_rows.index-idx).abs().idxmin()
            tag = verb_rows.loc[nearest_index, feature_col]
            if 'PERF' in str(tag):
                temporal.append(-1)
            elif any(k in str(tag) for k in ['IMPF','JUS','IMPV']):
                temporal.append(1)
            else:
                temporal.append(0)
        number.append(extract_number(row.get(feature_col,'')))
    df_dm['spatial'] = spatial
    df_dm['temporal'] = temporal
    df_dm['number'] = number
    df_dm['turn_deg'] = [TURN_MAP.get((s,t),0) for s,t in zip(spatial,temporal)]

    Path(outdir,'svg').mkdir(parents=True, exist_ok=True)
    Path(outdir,'png').mkdir(parents=True, exist_ok=True)
    df_dm.to_csv(Path(outdir,'hada_tokens.csv'), index=False)

    for surah in tqdm(range(1,115), desc='Drawing'):
        data = df_dm[df_dm[surah_col]==str(surah)]
        if data.empty:
            continue
        data = data.sort_values([ayah_col, token_col])
        x=y=0.0
        heading=90.0
        segments=[]
        widths=[]
        for _,r in data.iterrows():
            heading += r['turn_deg']
            new_x = x + np.cos(np.deg2rad(heading))
            new_y = y + np.sin(np.deg2rad(heading))
            segments.append([[x,y],[new_x,new_y]])
            widths.append(STROKE_WIDTH[r['number']])
            x,y = new_x,new_y
        fig,ax = plt.subplots(figsize=(3,3))
        lc = LineCollection(segments, linewidths=widths, color='black', capstyle='round')
        ax.add_collection(lc)
        ax.autoscale()
        ax.axis('off')
        fig.savefig(Path(outdir,'svg',f'surah_{surah:03d}.svg'), bbox_inches='tight', pad_inches=0)
        fig.savefig(Path(outdir,'png',f'surah_{surah:03d}.png'), dpi=300, bbox_inches='tight', pad_inches=0)
        plt.close(fig)

    html_lines = ['<!DOCTYPE html>','<html><head><meta charset="utf-8"><style>',
                  '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));grid-gap:10px;}',
                  '.grid img{width:100%;height:auto;}',
                  'body{font-family:sans-serif;padding:20px;}',
                  '</style></head><body><div class="grid">']
    for i in range(1,115):
        name = SURAH_NAMES[i-1]
        html_lines.append(f'<div><img src="svg/surah_{i:03d}.svg" alt="Surah {i}: {name}"></div>')
    html_lines.append('</div></body></html>')
    with open(Path(outdir,'gallery.html'),'w',encoding='utf-8') as f:
        f.write('\n'.join(html_lines))

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Generate Quran art poly-lines from QAC dataset')
    p.add_argument('--dataset', default='qac-with-id.tsv', help='TSV dataset path')
    p.add_argument('--outdir', default='output', help='Output directory')
    args = p.parse_args()
    main(args.dataset, args.outdir)
