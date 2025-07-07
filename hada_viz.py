#!/usr/bin/env python3
"""Generate Qur'an proximal demonstrative visualisations."""
import os
import sys
import math
import pkg_resources

# -- Dependency check ---------------------------------------------------------
required = [
    'requests',
    'pandas',
    'numpy',
    'lxml',
    'matplotlib',
    'Pillow',
    'cairosvg',
]
missing = []
for pkg in required:
    try:
        if pkg == 'Pillow':
            __import__('PIL')
        else:
            __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print('Missing packages:', ', '.join(missing))
    print('Run: pip install -r requirements.txt')
    sys.exit(1)

# Auto-generate requirements.txt with versions used
req_lines = []
for pkg in required:
    if pkg == 'Pillow':
        dist = pkg_resources.get_distribution('Pillow')
    else:
        dist = pkg_resources.get_distribution(pkg)
    req_lines.append(f"{dist.project_name}=={dist.version}")
with open('requirements.txt', 'w') as fh:
    fh.write('\n'.join(req_lines) + '\n')

# -- Imports (after verification) -------------------------------------------
import requests
import pandas as pd
import numpy as np
from lxml import etree
import matplotlib.pyplot as plt
from PIL import Image
import cairosvg

# -- Constants ---------------------------------------------------------------
DATA_DIR = 'data'
OUTPUT_DIR = 'output'
SVG_DIR = os.path.join(OUTPUT_DIR, 'svg')
PNG_DIR = os.path.join(OUTPUT_DIR, 'png')
QAC_URLS = [
    'https://raw.githubusercontent.com/zer0n13/qac-1.0/master/qac.xml',
    'https://raw.githubusercontent.com/tanzilnet/quran-morphology/master/qac.xml',
]
DEMONSTRATIVES = {
    'هٰذَا': ('sg',),
    'هٰذِهِ': ('sg',),
    'هَذَا': ('sg',),
    'هَذِهِ': ('sg',),
    'هٰذَانِ': ('dual',),
    'هَذَانِ': ('dual',),
    'هٰذَيْنِ': ('dual',),
    'هَذَيْنِ': ('dual',),
    'هٰتَانِ': ('dual',),
    'هَاتَانِ': ('dual',),
    'هٰتَيْنِ': ('dual',),
    'هَاتَيْنِ': ('dual',),
    'هٰؤُلَاءِ': ('pl',),
    'هَؤُلَاءِ': ('pl',),
}
THICKNESS = {'sg': 0.6, 'dual': 1.0, 'pl': 1.4}
TURN = {
    (-1, -1): -60,
    (-1, 0): -30,
    (-1, 1): 0,
    (0, -1): -15,
    (0, 0): 0,
    (0, 1): 15,
    (1, -1): 30,
    (1, 0): 60,
    (1, 1): 90,
}
SURAH_NAMES = [
    'Al-Fatihah','Al-Baqara','Al-i-Imran','An-Nisa','Al-Ma\'idah','Al-An\'am',
    'Al-A\'raf','Al-Anfal','At-Tawbah','Yunus','Hud','Yusuf','Ar-Ra\'d',
    'Ibrahim','Al-Hijr','An-Nahl','Al-Isra','Al-Kahf','Maryam','Ta-Ha',
    'Al-Anbiya','Al-Hajj','Al-Mu\'minoon','An-Nur','Al-Furqan','Ash-Shu\'ara',
    'An-Naml','Al-Qasas','Al-Ankabut','Ar-Rum','Luqman','As-Sajda','Al-Ahzab',
    'Saba','Fatir','Ya-Sin','As-Saffat','Sad','Az-Zumar','Ghafir','Fussilat',
    'Ash-Shuraa','Az-Zukhruf','Ad-Dukhan','Al-Jathiya','Al-Ahqaf','Muhammad',
    'Al-Fath','Al-Hujurat','Qaf','Adh-Dhariyat','At-Tur','An-Najm','Al-Qamar',
    'Ar-Rahman','Al-Waqia','Al-Hadid','Al-Mujadila','Al-Hashr','Al-Mumtahanah',
    'As-Saff','Al-Jumuah','Al-Munafiqun','At-Taghabun','At-Talaq','At-Tahrim',
    'Al-Mulk','Al-Qalam','Al-Haqqa','Al-Ma\'arij','Nuh','Al-Jinn','Al-Muzzammil',
    'Al-Muddaththir','Al-Qiyamah','Al-Insan','Al-Mursalat','An-Naba','An-Naziat',
    'Abasa','At-Takwir','Al-Infitar','Al-Mutaffifin','Al-Inshiqaq','Al-Buruj',
    'At-Tariq','Al-Ala','Al-Ghashiya','Al-Fajr','Al-Balad','Ash-Shams','Al-Layl',
    'Ad-Duhaa','Ash-Sharh','At-Tin','Al-Alaq','Al-Qadr','Al-Bayyinah','Az-Zalzalah',
    'Al-Adiyat','Al-Qari\'ah','At-Takathur','Al-Asr','Al-Humazah','Al-Fil','Quraysh',
    'Al-Ma\'un','Al-Kawthar','Al-Kafirun','An-Nasr','Al-Masad','Al-Ikhlas','Al-Falaq','An-Nas'
]

# -- Helper functions -------------------------------------------------------
def download_qac(path: str):
    """Download qac.xml to the given path if not already present."""
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for url in QAC_URLS:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(path, 'wb') as fh:
                    fh.write(r.content)
                return
        except requests.RequestException:
            continue
    raise RuntimeError('Unable to download qac.xml from the provided URLs.')

def parse_qac(path: str) -> pd.DataFrame:
    """Parse qac.xml and return DataFrame of proximal demonstratives."""
    tree = etree.parse(path)
    root = tree.getroot()
    tokens = []
    # Retrieve all token elements
    for tok in root.xpath('.//token'):
        form = tok.get('form') or tok.text or ''
        if form not in DEMONSTRATIVES:
            continue
        # Ascend to surah and ayah via ancestors
        aya_elem = tok.getparent()
        while aya_elem is not None and aya_elem.tag != 'aya':
            aya_elem = aya_elem.getparent()
        sura_elem = aya_elem.getparent() if aya_elem is not None else None
        surah = int(sura_elem.get('id')) if sura_elem is not None else 0
        aya = int(aya_elem.get('id')) if aya_elem is not None else 0
        word_elem = tok.getparent()
        while word_elem is not None and word_elem.tag != 'word':
            word_elem = word_elem.getparent()
        word_id = word_elem.get('id') if word_elem is not None else tok.get('id')
        pos_str = tok.get('pos') or tok.get('type') or ''
        head = tok.get('head')
        index_attr = tok.get('index') or tok.get('id')
        tokens.append({
            'surah': surah,
            'ayah': aya,
            'word_id': word_id,
            'token_id': index_attr,
            'form': form,
            'lemma': tok.get('lemma'),
            'pos': pos_str,
            'head': head,
        })
    df = pd.DataFrame(tokens)
    return df


def compute_axes(df: pd.DataFrame, all_tokens: pd.DataFrame):
    """Compute spatial and temporal axes and turning angles."""
    # Map token id -> position index within surah for head comparison
    all_tokens['global_index'] = np.arange(len(all_tokens))
    id_to_idx = dict(zip(all_tokens['token_id'], all_tokens['global_index']))

    spatial_vals = []
    temporal_vals = []
    for i, row in df.iterrows():
        head = row['head']
        spatial = 0
        if head and head in id_to_idx:
            if id_to_idx[head] < id_to_idx[row['token_id']]:
                spatial = -1
            elif id_to_idx[head] > id_to_idx[row['token_id']]:
                spatial = 1
        spatial_vals.append(spatial)

        # search for nearest finite verb within +-3 tokens
        idx = id_to_idx.get(row['token_id'], -1)
        window = all_tokens.iloc[max(0, idx-3):idx+4]
        temporal = 0
        for _, wrow in window.iterrows():
            tag = wrow.get('pos','')
            if tag in ('PERF', 'IMPF', 'JUS', 'IMPV'):
                if tag == 'PERF':
                    temporal = -1
                else:
                    temporal = 1
                break
        temporal_vals.append(temporal)
    df['spatial'] = spatial_vals
    df['temporal'] = temporal_vals
    df['turn_deg'] = [TURN[(s,t)] for s,t in zip(df['spatial'], df['temporal'])]
    df['number'] = [DEMONSTRATIVES.get(f,('sg',))[0] for f in df['form']]


def draw_surahs(df: pd.DataFrame):
    """Generate poly-line visualisations for each surah."""
    os.makedirs(SVG_DIR, exist_ok=True)
    os.makedirs(PNG_DIR, exist_ok=True)
    for surah in range(1,115):
        s_df = df[df['surah']==surah]
        if s_df.empty:
            # generate blank figure
            fig, ax = plt.subplots(figsize=(3,3))
            ax.axis('off')
            fig.savefig(os.path.join(SVG_DIR, f'surah_{surah:03d}.svg'), bbox_inches='tight', pad_inches=0)
            fig.savefig(os.path.join(PNG_DIR, f'surah_{surah:03d}.png'), bbox_inches='tight', pad_inches=0, dpi=96)
            plt.close(fig)
            continue
        heading = 90
        x, y = 0.0, 0.0
        pts_x = [x]
        pts_y = [y]
        for _, row in s_df.sort_values(['ayah','word_id']).iterrows():
            heading += row['turn_deg']
            rad = math.radians(heading)
            x += math.cos(rad)
            y += math.sin(rad)
            pts_x.append(x)
            pts_y.append(y)
        thickness = THICKNESS[s_df.iloc[0]['number']]
        fig, ax = plt.subplots(figsize=(3,3))
        ax.plot(pts_x, pts_y, lw=thickness, color='black')
        ax.axis('off')
        fig.savefig(os.path.join(SVG_DIR, f'surah_{surah:03d}.svg'), bbox_inches='tight', pad_inches=0)
        fig.savefig(os.path.join(PNG_DIR, f'surah_{surah:03d}.png'), bbox_inches='tight', pad_inches=0, dpi=96)
        plt.close(fig)


def generate_gallery():
    """Create HTML gallery referencing all SVGs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    html = ['<!DOCTYPE html>', '<html>', '<head>', '<meta charset="utf-8">',
            '<style>',
            'body{font-family:sans-serif;}','.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;}',
            'img{width:100%;height:auto;}',
            '</style></head><body>',
            '<div class="grid">']
    for i in range(1,115):
        name = SURAH_NAMES[i-1] if i-1 < len(SURAH_NAMES) else ''
        html.append(f'<div><img src="svg/surah_{i:03d}.svg" alt="Surah {i}: {name}"></div>')
    html += ['</div></body></html>']
    with open(os.path.join(OUTPUT_DIR, 'gallery.html'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(html))


if __name__ == '__main__':
    qac_path = os.path.join(DATA_DIR, 'qac.xml')
    download_qac(qac_path)

    # Parse all tokens to compute positional info
    all_df = parse_qac(qac_path)
    df = all_df.copy()
    compute_axes(df, all_df)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUTPUT_DIR, 'hada_tokens.csv'), index=False)
    draw_surahs(df)
    generate_gallery()
