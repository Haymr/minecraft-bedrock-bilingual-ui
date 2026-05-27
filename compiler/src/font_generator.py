"""
font_generator.py — Bilingual Bedrock UI Font Generator (v3.0)

Bedrock-native glyph_E1.png üretir (256×256, 16×16 ızgara, her hücre 16×16 px).
- charmap.json'u okur (parser.py tarafından üretilir)
- Her haritalı karakteri piksel fontu ile hücresine çizer
- Vanilla Minecraft glyph stili: beyaz piksel + alpha (~200), şeffaf arkaplan
- Kaynak: resource_pack/font/glyph_E1.png (Bedrock bu dosyayı 0xE1xx bloğu için okur)

Önemli Bedrock Font Notları:
- Dosya adı glyph_E1.png → 0xE100-0xE1FF bloğunu kapsar
- Hücre konumu: code_point & 0xFF = hücre index'i; row = idx // 16, col = idx % 16
- Glyphlar beyaz (#FFFFFF) olmalı; Bedrock §7 (gray) + §o (italic) ile render eder
- Arkaplan tamamen şeffaf (alpha=0) olmalı
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

GRID_SIZE   = 16         # 16×16 hücre ızgarası
CELL_SIZE   = 16         # Her hücre 16×16 piksel
IMG_SIZE    = GRID_SIZE * CELL_SIZE   # 256×256

GLYPH_ALPHA = 210        # Vanilla benzeri alpha değeri (~217)
FONT_SIZE   = 9          # Hücreye sığan render boyutu

# Tercih sırası ile sistem font adayları (Minecraft'a en yakın monospace)
FONT_CANDIDATES = [
    '/System/Library/Fonts/SFNSMono.ttf',
    '/System/Library/Fonts/Supplemental/PTMono.ttc',
    '/Library/Fonts/Courier New.ttf',
    '/System/Library/Fonts/Monaco.dfont',
]


def load_best_font(size: int) -> ImageFont.FreeTypeFont:
    """Sistemde mevcut en iyi monospace fontu yükler."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback: PIL built-in (pixelated, Minecraft estetiğine yakın)
    return ImageFont.load_default(size=size)


def char_to_cell(pua_codepoint: int) -> tuple[int, int]:
    """
    PUA code point → (row, col) ızgara konumu.
    Bedrock, hücre konumunu code_point'in alt baytından (& 0xFF) hesaplar.
    E1xx bloğu için: index = cp & 0xFF, row = index // 16, col = index % 16
    """
    idx = pua_codepoint & 0xFF
    return (idx // GRID_SIZE, idx % GRID_SIZE)


def render_glyph(draw: ImageDraw.ImageDraw,
                 char: str,
                 row: int,
                 col: int,
                 font: ImageFont.FreeTypeFont) -> None:
    """Verilen karakteri ızgaradaki hücreye çizer."""
    x_origin = col * CELL_SIZE
    y_origin = row * CELL_SIZE

    # Karakterin bounding box'ını hesapla (ortalamak için)
    try:
        bbox = font.getbbox(char)
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]
        # Hücre içinde yatay/dikey ortala (sol/üst ağırlıklı)
        x_offset = max(1, (CELL_SIZE - char_w) // 2 - bbox[0])
        y_offset = max(1, (CELL_SIZE - char_h) // 2 - bbox[1])
    except Exception:
        x_offset, y_offset = 2, 3

    # Piksel koordinatı
    x = x_origin + x_offset
    y = y_origin + y_offset

    # Beyaz + vanilla alpha — Bedrock rendering kendi renk/opacity'yi uygular
    draw.text((x, y), char, fill=(255, 255, 255, GLYPH_ALPHA), font=font)


def generate_glyph_png(charmap_path: str, output_path: str) -> None:
    """
    charmap.json'u okur ve glyph_E1.png üretir.

    charmap.json format: {"original_char": pua_codepoint_int, ...}
    """
    # charmap.json yükle
    with open(charmap_path, 'r', encoding='utf-8') as f:
        charmap: dict[str, int] = json.load(f)

    print(f'  charmap: {len(charmap)} karakter yüklenecek')

    # 256×256 şeffaf RGBA kanvas
    img = Image.new('RGBA', (IMG_SIZE, IMG_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Font yükle
    font = load_best_font(FONT_SIZE)
    print(f'  Font: {font}')

    # Her karakteri doğru hücreye render et
    rendered = 0
    for original_char, pua_cp in charmap.items():
        # Validate: PUA aralığında mı?
        if not (0xE101 <= pua_cp <= 0xE1FF):
            print(f'  UYARI: {repr(original_char)} → U+{pua_cp:04X} PUA dışında, atlanıyor')
            continue

        row, col = char_to_cell(pua_cp)
        render_glyph(draw, original_char, row, col, font)
        rendered += 1

    print(f'  {rendered} glyph render edildi')

    # Çıktı dizini oluştur ve kaydet
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, 'PNG')
    print(f'  → {output_path}')
    
    # Bedrock için textures/font/ klasörüne de kaydet
    textures_font_dir = output_path.replace('/font/glyph_', '/textures/font/glyph_')
    if textures_font_dir != output_path:
        os.makedirs(os.path.dirname(textures_font_dir), exist_ok=True)
        img.save(textures_font_dir, 'PNG')
        print(f'  → {textures_font_dir} (Bedrock native path)')

    # Boyut doğrulama
    saved = Image.open(output_path)
    assert saved.size == (IMG_SIZE, IMG_SIZE), \
        f"Beklenen {IMG_SIZE}x{IMG_SIZE}, üretilen {saved.size}"
    print(f'  Doğrulama OK: {saved.size[0]}×{saved.size[1]} RGBA PNG')


def cleanup_old_assets(font_dir: str) -> None:
    """Artık kullanılmayan / hatalı eski dosyaları temizler."""
    to_remove = [
        os.path.join(font_dir, 'default.json'),       # Java Edition formatı
        os.path.join(font_dir, 'bilingual_font.png'),  # 1x1 geçersiz PNG
        os.path.join(font_dir, 'default8.png'),        # Eski yanlış placeholder
    ]
    for path in to_remove:
        if os.path.exists(path):
            os.remove(path)
            print(f'  Kaldırıldı: {path}')


# ---------------------------------------------------------------------------
# Ana Akış
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    BASE = os.path.dirname(__file__)  # compiler/src/

    charmap_path = os.path.join(BASE, '..', 'charmap.json')
    font_dir     = os.path.join(BASE, '..', '..', 'resource_pack', 'font')
    output_path  = os.path.join(font_dir, 'glyph_E1.png')

    print('[1/3] Eski font dosyaları temizleniyor...')
    cleanup_old_assets(font_dir)

    print('[2/3] glyph_E1.png üretiliyor...')
    generate_glyph_png(charmap_path, output_path)

    print('[3/3] Tamamlandı.')
