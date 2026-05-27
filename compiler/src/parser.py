"""
parser.py — Bilingual Bedrock UI Compiler (v3.0)

Değişiklikler (v3.0):
- Charmap tabanlı PUA mapping: fr_FR'deki her benzersiz karakter 0xE101-0xE1FF
  aralığına sıralı haritalanır. Doğrudan offset yaklaşımı kaldırıldı (overflow fix).
- Spesifik format string tespiti: geniş '{' yerine regex ile %s/%d/%1$s/{0} gibi
  Minecraft-spesifik dinamik parametreler tespit edilir.
- charmap.json export: font_generator.py bu dosyayı okuyarak glyph_E1.png üretir.
"""

import os
import re
import json

# ---------------------------------------------------------------------------
# Sabit Değerler
# ---------------------------------------------------------------------------

MOJANGLES_WIDTHS = {
    'A': 6, 'B': 6, 'C': 6, 'D': 6, 'E': 6, 'F': 6, 'G': 6, 'H': 6, 'I': 4, 'J': 6,
    'K': 6, 'L': 6, 'M': 6, 'N': 6, 'O': 6, 'P': 6, 'Q': 6, 'R': 6, 'S': 6, 'T': 6,
    'U': 6, 'V': 6, 'W': 6, 'X': 6, 'Y': 6, 'Z': 6,
    'a': 6, 'b': 6, 'c': 6, 'd': 6, 'e': 6, 'f': 5, 'g': 6, 'h': 6, 'i': 2, 'j': 6,
    'k': 5, 'l': 3, 'm': 6, 'n': 6, 'o': 6, 'p': 6, 'q': 6, 'r': 6, 's': 6, 't': 4,
    'u': 6, 'v': 6, 'w': 6, 'x': 6, 'y': 6, 'z': 6,
    '0': 6, '1': 6, '2': 6, '3': 6, '4': 6, '5': 6, '6': 6, '7': 6, '8': 6, '9': 6,
    ' ': 4, '.': 2, ',': 2, ':': 2, ';': 2, '!': 2, '?': 6, "'": 2, '"': 4,
    '(': 4, ')': 4, '[': 4, ']': 4, '{': 4, '}': 4, '<': 5, '>': 5,
    '-': 6, '_': 6, '+': 6, '=': 6, '*': 4, '/': 6, '\\': 6, '|': 2,
    '@': 7, '#': 6, '$': 6, '%': 6, '^': 6, '&': 6, '~': 6, '`': 3,
}

PUA_BASE = 0xE101   # 0xE100 boş bırakılır (null glyph)
PUA_MAX  = 0xE1FF   # 255 slot (yeterli: fr_FR maks 128 benzersiz char)

# Minecraft dinamik format parametreleri (bunları içeren satırlar skip edilir)
DYNAMIC_PARAM_RE = re.compile(
    r'%[0-9]*\$?[sdf]'      # %s %d %f %1$s %2$d ...
    r'|\{[0-9]+\}'           # {0} {1} {2} ...
)

SKIP_KEY_PREFIXES = (
    'commands.',
    'accessibility.',
    'scoreboard.',
    'sidebar.',
    'progressScreen.',
    'tips.',
    'loading.',
)

# ---------------------------------------------------------------------------
# Charmap Oluşturma
# ---------------------------------------------------------------------------

def build_charmap(secondary_lang_dict: dict) -> dict:
    """
    secondary_lang_dict içindeki tüm benzersiz karakterleri toplar ve
    PUA_BASE'den başlayarak haritalandırır.

    Döndürür: {original_char: pua_char} (string → string)
    """
    # Tüm value stringlerinden benzersiz karakterleri topla
    all_chars: set[str] = set()
    for value in secondary_lang_dict.values():
        for ch in value:
            cp = ord(ch)
            # Kontrol karakterleri, § format kodları ve \n hariç tümünü map'e al
            if cp >= 32 and ch != '§':
                all_chars.add(ch)

    # Sıralı listele (deterministik çıktı için)
    sorted_chars = sorted(all_chars, key=ord)

    # Slot kontrolü
    available_slots = PUA_MAX - PUA_BASE + 1
    if len(sorted_chars) > available_slots:
        raise ValueError(
            f"Secondary language has {len(sorted_chars)} unique chars "
            f"but PUA block only has {available_slots} slots."
        )

    charmap: dict[str, str] = {}
    for i, ch in enumerate(sorted_chars):
        pua_cp = PUA_BASE + i
        charmap[ch] = chr(pua_cp)

    return charmap


def translate_to_pua(text: str, charmap: dict[str, str]) -> str:
    """Verilen metindeki her karakteri charmap'e göre PUA'ya çevirir."""
    result = []
    for ch in text:
        if ch == '§':
            # §X format kodları aynen geçsin (bunlar PUA'ya çevrilmemeli)
            result.append(ch)
        else:
            result.append(charmap.get(ch, ch))
    return ''.join(result)


# ---------------------------------------------------------------------------
# Lang Dosyası Parse
# ---------------------------------------------------------------------------

def parse_lang_file(filepath: str) -> dict[str, str]:
    """
    Bedrock .lang dosyasını parse eder.
    - ## ile başlayan satırlar: yorum → atla
    - Tek # ile başlayan satırlar: Bedrock'ta YORUM DEĞİL, geçerli satır!
      Ancak genellikle ## kullanılır; # başlangıcını da güvenlik için atlıyoruz
      çünkü Mojang'ın vanilla dosyaları ## kullanıyor ve # içeren satırlar
      nadiren key=value formatında olur. BUG NOTU: bu satırları değerlendirip
      key-value içerip içermediğine bakıyoruz.
    - Boş satırlar: atla
    """
    lang_dict: dict[str, str] = {}
    with open(filepath, 'r', encoding='utf-8-sig') as f:  # utf-8-sig: BOM temizler
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            stripped = line.strip()

            # Boş satır
            if not stripped:
                continue

            # Yorum satırı (## veya tek # — her ikisi de atlanır)
            if stripped.startswith('#'):
                continue

            # key=value ayrıştır
            if '=' in stripped:
                key, value = stripped.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key:
                    lang_dict[key] = value

    return lang_dict


# ---------------------------------------------------------------------------
# Skip Mantığı
# ---------------------------------------------------------------------------

def should_skip(key: str, primary_value: str) -> bool:
    """True dönerse bu satır tek dilli bırakılır."""
    # Dinamik runtime parametresi içeriyor mu?
    if DYNAMIC_PARAM_RE.search(primary_value):
        return True

    # Devre dışı bırakılan prefix'ler
    if key.startswith(SKIP_KEY_PREFIXES):
        return True

    return False


# ---------------------------------------------------------------------------
# Genişlik Hesabı
# ---------------------------------------------------------------------------

def get_string_width(text: str) -> int:
    """§X format kodlarını temizleyerek Mojangles piksel genişliği hesaplar."""
    clean = re.sub(r'§.', '', text)
    return sum(MOJANGLES_WIDTHS.get(ch, 6) for ch in clean)


def get_target_width(key: str) -> int:
    """Anahtar prefix'ine göre hedef satır genişliği (piksel).
    DİKKAT: ui_modifier.py ile BİREBİR senkronize çalışmalıdır."""
    if key.startswith('achievement.'):
        return 250
    if key.startswith(('options.', 'settings.')):
        return 220
    # Artık 'item.' ve 'potion.' da 200px (ui_modifier'daki inventory vs 200px ile aynı)
    return 200


# ---------------------------------------------------------------------------
# Dil Birleştirme
# ---------------------------------------------------------------------------

def merge_languages(
    primary_dict: dict[str, str],
    secondary_dict: dict[str, str],
    charmap: dict[str, str],
) -> dict[str, str]:
    merged: dict[str, str] = {}

    for key, primary_val in primary_dict.items():
        # Skip kontrolü
        if key not in secondary_dict or should_skip(key, primary_val):
            merged[key] = primary_val
            continue

        secondary_val = secondary_dict[key]

        # İkinci dil değeri boş veya birincisiyle aynıysa tek dilli bırak
        if not secondary_val.strip() or primary_val == secondary_val:
            merged[key] = primary_val
            continue

        # Padding hesabı (tam senkronize max_size için)
        target_width = get_target_width(key)
        primary_width = get_string_width(primary_val)
        remainder = primary_width % target_width
        padding_px = (target_width - remainder) if remainder else 0

        # Minimum padding: Güvenlik payı (eğer kalan boşluk 12px'ten azsa
        # kelime yanlışlıkla üst satıra sıkışabilir, bu yüzden ekstra bir tur atıyoruz)
        if padding_px < 12:
            padding_px += target_width

        # Bedrock'ta space = 4px genişliğinde
        padding_spaces = ' ' * max(1, padding_px // 4)

        # İkinci dili PUA'ya çevir ve formatla
        pua_text = translate_to_pua(secondary_val, charmap)
        # V3.1 DÜZELTME: 4 boşlukluk (indent) kaldırıldı!
        # Wrap noktasının tam padding bitiminde olması için format kodları doğrudan bitişiktir.
        secondary_formatted = f'\u00a7r\u00a77\u00a7o{pua_text}'

        combined = f'{primary_val}{padding_spaces}{secondary_formatted}'

        # Güvenlik: satır içinde \n olmamalı
        assert '\n' not in combined, f"Newline found in merged string for key: {key}"
        assert '\r' not in combined, f"CR found in merged string for key: {key}"

        merged[key] = combined

    return merged


# ---------------------------------------------------------------------------
# Çıktı Yazımı
# ---------------------------------------------------------------------------

def write_lang_file(filepath: str, lang_dict: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        f.write('## Auto-generated Bilingual Resource Pack — DO NOT EDIT MANUALLY\n')
        for key, val in lang_dict.items():
            f.write(f'{key}={val}\n')


def export_charmap(charmap: dict[str, str], output_path: str) -> None:
    """charmap'i font_generator.py için JSON olarak dışa aktarır."""
    # JSON için: {original_char_as_unicode_escape: pua_codepoint_int}
    exportable = {
        ch: ord(pua_ch)
        for ch, pua_ch in charmap.items()
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(exportable, f, ensure_ascii=False, indent=2)
    print(f'  charmap.json: {len(exportable)} entries → {output_path}')


# ---------------------------------------------------------------------------
# Ana Akış
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    BASE = os.path.dirname(__file__)  # compiler/src/

    primary_path   = os.path.join(BASE, '..', 'input_langs', 'en_US.lang')
    secondary_path = os.path.join(BASE, '..', 'input_langs', 'fr_FR.lang')
    output_path    = os.path.join(BASE, '..', '..', 'resource_pack', 'texts', 'en_US.lang')
    charmap_path   = os.path.join(BASE, '..', 'charmap.json')

    print('[1/4] Lang dosyaları parse ediliyor...')
    primary_lang   = parse_lang_file(primary_path)
    secondary_lang = parse_lang_file(secondary_path)
    print(f'  EN: {len(primary_lang)} satır, FR: {len(secondary_lang)} satır')

    print('[2/4] Charmap oluşturuluyor...')
    charmap = build_charmap(secondary_lang)
    print(f'  {len(charmap)} benzersiz karakter → PUA U+{PUA_BASE:04X}–U+{PUA_BASE+len(charmap)-1:04X}')
    export_charmap(charmap, charmap_path)

    print('[3/4] Diller birleştiriliyor...')
    merged = merge_languages(primary_lang, secondary_lang, charmap)
    bilingual_count = sum(
        1 for v in merged.values() if '\u00a7r\u00a77\u00a7o' in v
    )
    print(f'  Toplam: {len(merged)} satır, çift dilli: {bilingual_count}')

    print('[4/4] en_US.lang yazılıyor...')
    write_lang_file(output_path, merged)
    print(f'  → {output_path}')
    print('Derleme tamamlandı.')
