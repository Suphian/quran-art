import os
import requests
from lxml import etree
import matplotlib.pyplot as plt
import cairosvg
import numpy as np
from typing import List, Tuple

# Constants for data sources
DATA_DIR = 'data'
QAC_FILE = os.path.join(DATA_DIR, 'qac.xml')
PRIMARY_URL = 'https://raw.githubusercontent.com/zer0n13/qac-1.0/master/qac.xml'
FALLBACK_URL = 'https://raw.githubusercontent.com/tanzilnet/quran-morphology/master/qac.xml'

# List of proximal demonstrative forms
PROXIMAL_FORMS = [
    'هٰذَا',
    'هَٰذَا',
    'هٰذِهِ',
    'هَٰذِهِ',
    'هٰذَانِ',
    'هٰذَيْنِ',
    'هٰاتَانِ',
    'هٰتَيْنِ',
    'هٰؤُلَاءِ'
]

def download_qac() -> None:
    """Download the QAC XML if not already present."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(QAC_FILE):
        return
    for url in (PRIMARY_URL, FALLBACK_URL):
        try:
            resp = requests.get(url, timeout=30)
            if resp.ok:
                with open(QAC_FILE, 'wb') as f:
                    f.write(resp.content)
                print(f'Downloaded {url}')
                return
        except requests.RequestException:
            continue
    raise RuntimeError('Failed to download qac.xml from both mirrors.')

def parse_qac() -> dict:
    """Parse QAC XML and return mapping of surah -> list of word info."""
    tree = etree.parse(QAC_FILE)
    root = tree.getroot()
    surah_data = {}
    for surah in root.findall('.//chapter'):
        sid = int(surah.get('id'))
        words = []
        for verse in surah.findall('.//verse'):
            vid = int(verse.get('id'))
            for idx, word in enumerate(verse.findall('.//word'), start=1):
                form = word.get('form')
                lemma = word.get('lemma')
                morph = word.get('morph') or ''
                if form in PROXIMAL_FORMS or lemma in PROXIMAL_FORMS:
                    words.append({'verse': vid, 'pos': idx, 'form': form, 'morph': morph})
        surah_data[sid] = words
    return surah_data

def word_to_point(word: dict) -> Tuple[float, float]:
    """Convert word info to 2D point using heuristics."""
    temporal = word['verse']
    spatial = word['pos']
    return (temporal, spatial)

def draw_surah_polyline(sid: int, words: List[dict], out_dir: str) -> None:
    """Draw polyline for a surah and save as SVG/PNG."""
    if not words:
        return
    points = [word_to_point(w) for w in words]
    x, y = zip(*points)
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot(x, y, marker='o', linestyle='-')
    ax.axis('off')
    svg_path = os.path.join(out_dir, f'surah_{sid:03d}.svg')
    png_path = os.path.join(out_dir, f'surah_{sid:03d}.png')
    fig.savefig(svg_path, format='svg', bbox_inches='tight')
    plt.close(fig)
    cairosvg.svg2png(url=svg_path, write_to=png_path)


def build_gallery(out_dir: str, html_path: str) -> None:
    """Generate an HTML gallery referencing SVG images."""
    images = sorted([f for f in os.listdir(out_dir) if f.endswith('.svg')])
    with open(html_path, 'w', encoding='utf-8') as html:
        html.write('<html><head><style>\n.grid{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;}\n.grid img{width:100%;height:auto;}\n</style></head><body>')
        html.write('<div class="grid">')
        for img in images:
            html.write(f'<div><img src="{img}" alt="{img}"></div>')
        html.write('</div></body></html>')


def main():
    download_qac()
    data = parse_qac()
    out_dir = 'output'
    os.makedirs(out_dir, exist_ok=True)
    for sid, words in data.items():
        draw_surah_polyline(sid, words, out_dir)
    build_gallery(out_dir, os.path.join(out_dir, 'gallery.html'))

if __name__ == '__main__':
    main()

