"""
ui_modifier.py — Bilingual Bedrock UI Modifier (v3.0)

Değişiklikler (v3.0):
- Hem "wrap": true HEM DE "max_size": [W, "default"] birlikte enjekte edilir.
- max_size genişliği dosya adına göre belirlenir (parser.py padding değerleriyle senkron).
- Idempotent: zaten "wrap": true içeren bloğa tekrar ekleme yapmaz.
- Bedrock JSON C-style comment (// ...) uyumu: regex ile value string'lerini değil,
  yalnızca "type": "label" pattern'ini hedef alır — comment'lere dokunmaz.
- Yapısal yaklaşım: JSON obje bloğunu satır bazlı işler (ast parse gerektirmez).
"""

import os
import re

import os
import re

# ---------------------------------------------------------------------------
# Bileşen Bazlı Kara Liste (Blacklist)
# ---------------------------------------------------------------------------
# Dosyaları tamamen atlamak yerine, sadece bu kelimeleri içeren nesne
# isimlerine (örn: "credits_text@...") max_size basmayacağız.
COMPONENT_BLACKLIST = [
    'credits',
    'how_to_play',
    'start',
    'eula',
    'death',
    'world_templates',
    'toast',
    'title',
    'header'
]

def should_skip_component(comp_name: str) -> bool:
    name = comp_name.lower()
    for b in COMPONENT_BLACKLIST:
        if b in name:
            return True
    return False

# ---------------------------------------------------------------------------
# Dosya adı → max_size genişlik eşlemesi
# parser.py'daki get_target_width() ile senkron olmalı
# ---------------------------------------------------------------------------

FILE_WIDTH_MAP: dict[str, int] = {
    'achievement': 250,
    'options':     220,
    'settings':    220,
    'menu':        200,
    'hud':         200,
    'inventory':   200,
    'chest':       200,
    'anvil':       200,
    'book':        200,
    'beacon':      200,
    'brewing':     200,
    'cartography': 200,
    'furnace':     200,
    'stonecutter': 200,
    'crafting':    200,
}

DEFAULT_WIDTH = 200

def get_width_for_file(filename: str) -> int:
    name = filename.replace('.json', '').lower()
    for key, width in FILE_WIDTH_MAP.items():
        if name.startswith(key) or key in name:
            return width
    return DEFAULT_WIDTH

# ---------------------------------------------------------------------------
# Enjeksiyon Mantığı
# ---------------------------------------------------------------------------

TYPE_LABEL_RE = re.compile(r'^(\s*)"type"\s*:\s*"label"(\s*,?)(\s*)$')
INHERIT_LABEL_RE = re.compile(r'^(\s*)"([^"]*@[^"]*(?:label|text|button))"\s*:\s*\{\s*$')

def process_file(filepath: str, target_width: int) -> bool:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines: list[str] = []
    changed = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            new_lines.append(line)
            i += 1
            continue

        # Durum 1: "type": "label"
        m_type = TYPE_LABEL_RE.match(line.rstrip('\n'))
        if m_type:
            indent = m_type.group(1)
            trailing_comma = m_type.group(2)
            
            lookahead = ''.join(lines[i:min(i+15, len(lines))])
            has_wrap = '"wrap"' in lookahead[:lookahead.find('}', 1)] if '}' in lookahead[1:] else '"wrap"' in lookahead
            has_max = '"max_size"' in lookahead[:lookahead.find('}', 1)] if '}' in lookahead[1:] else '"max_size"' in lookahead

            if not trailing_comma.strip():
                line = line.rstrip('\n').rstrip() + ',\n'
            new_lines.append(line)

            if not has_wrap:
                new_lines.append(f'{indent}"wrap": true,\n')
                changed = True
            if not has_max:
                new_lines.append(f'{indent}"max_size": [ {target_width}, "default" ],\n')
                changed = True

            i += 1
            continue

        # Durum 2: Kalıtım ("name@common.label": {)
        m_inherit = INHERIT_LABEL_RE.match(line.rstrip('\n'))
        if m_inherit:
            indent = m_inherit.group(1)
            comp_name = m_inherit.group(2)
            
            new_lines.append(line)
            i += 1
            
            if should_skip_component(comp_name):
                continue
                
            lookahead = ''.join(lines[i:min(i+15, len(lines))])
            has_wrap = '"wrap"' in lookahead[:lookahead.find('}', 1)] if '}' in lookahead[1:] else '"wrap"' in lookahead
            has_max = '"max_size"' in lookahead[:lookahead.find('}', 1)] if '}' in lookahead[1:] else '"max_size"' in lookahead

            inject_indent = indent + "  "
            if not has_wrap:
                new_lines.append(f'{inject_indent}"wrap": true,\n')
                changed = True
            if not has_max:
                new_lines.append(f'{inject_indent}"max_size": [ {target_width}, "default" ],\n')
                changed = True
                
            continue

        new_lines.append(line)
        i += 1

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return changed

def inject_wrap_and_maxsize(ui_dir: str) -> None:
    modified = 0
    skipped  = 0
    total    = 0

    for root, _, files in os.walk(ui_dir):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            total += 1
            filepath = os.path.join(root, filename)
            target_width = get_width_for_file(filename)
            try:
                if process_file(filepath, target_width):
                    modified += 1
            except Exception as e:
                print(f'  UYARI: {filename} işlenemedi — {e}')
                skipped += 1

    print(f'ui_modifier.py (v4.0): {total} dosya tarandı → {modified} güncellendi, {skipped} hatalı')

if __name__ == '__main__':
    BASE   = os.path.dirname(__file__)
    ui_dir = os.path.join(BASE, '..', '..', 'resource_pack', 'ui')
    inject_wrap_and_maxsize(ui_dir)
