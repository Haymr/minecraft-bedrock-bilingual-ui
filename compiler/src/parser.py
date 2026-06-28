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
    # Komut/debug çıktıları — oyuncuya gösterilmiyor
    'commands.',
    'scoreboard.',
    'sidebar.',
    # Erişilebilirlik / TTS — ekran okuyucuya gönderiliyor, bilingual gerekmez
    'accessibility.',
    # Yükleme ekranı ipuçları — yeterince alan var ama aşırı metin
    'progressScreen.',
    'tips.',
    # ── Layout-problematik olanlar ──────────────────────────────────────────
    # Kontroller ekranı: "Jump", "Attack" vb. kısa etiket, keybind paneli ≤60px
    'controls.',
    # İstatistik etiketleri: çok kısa tek-satır sayaç label'ları
    'stat.',
    # Ses altyazıları: 0.5s görünüp yok oluyor, çok küçük
    'subtitles.',
    # ── MOTOR TARAFINDAN RAW ÇİZİLEN AYAR EKRANLARI ─────────────────────────
    # Bu ekranlar metni § format kodlarını İŞLEMEDEN ve PUA fontu OLMADAN ham
    # render eder → "§r§7§o" düz metin + boş kutu (tofu) çıkar. Pakette
    # düzeltilemez (mimari sınır). Bu yüzden tek-dilli (temiz İngilizce) bırakılır.
    'createWorldScreen.',   # Dünya oluşturma ayarları (Default/Hardcore/Starting map…)
    'options.',             # Ayarlar menüsü etiket+açıklamaları (Video/Audio/…)
    'menu.game.tab.',       # Oyun ayarları sekmeleri (World Setup, açıklamalar…)
    'generator.',           # Dünya tipi seçenekleri (Default/Flat/…)
    'soundCategory.',        # Ses ayarları kategorileri (Hostile mobs…)
    'storageManager.',       # Depolama yönetimi ekranı (üst üste biniyor)
)
# NOT: container.* (Chest/Coffre), tile.* (Blast Furnace/Haut fourneau),
#       item.* (Iron Ingot/Lingot de fer), action.interact.* (Stand/Se lever)
#       ve entity.* key'leri BİLİNGUAL KALIR — kullanıcıya görünen asıl içerik.

# Tam-eşleşme skip: tek tek key'ler (motor-render ayar nav/başlıkları veya dar
# butonlar). furnaceScreen.header BİLEREK listede DEĞİL → inline çevrilir.
SKIP_EXACT_KEYS = {
    # Fırın slot placeholder'ları: "Input/Fuel/Result" ~32px slotta — sığmaz.
    'furnaceScreen.fuel', 'furnaceScreen.input', 'furnaceScreen.result',
    # Ayarlar sol nav kategorileri (motor-render → tofu): temiz İngilizce kalsın.
    'menu.globalpacks', 'menu.resourcepacks', 'menu.behaviors',
    'menu.skinpacks', 'menu.storage', 'menu.storageManagement',
    'menu.worldtemplates', 'menu.skins', 'menu.options', 'menu.moreOptions',
    # Ana menüdeki Marketplace/Profile GÖRSEL butonları: 2 satır metin
    # arka plan görselinin üzerine taşıyor → tek dilli bırak.
    'menu.store', 'menu.profile',
    # "Dressing Room" butonu dar; "Dressing Room / Vestiaire" taşıyor → İngilizce.
    'profileScreen.header',
}

# Suffix bazlı skip (key sonuna göre) - Settings nav tab label'ları
SKIP_KEY_SUFFIXES = (
    '.tab.title',        # Settings sol nav tab label'ları (30px sabit toggle)
    '.tab.name',         # Benzer nav tab label'ları
)

# options.* prefix'li key'ler için özel kural:
# Kısa değerler (<= 30 karakter) settings nav toggle'larında kullanılıyor (30px fixed height)
# Uzun değerler (> 30 karakter) açıklama/tooltip metinleri - bilingual yapılabilir
OPTIONS_BILINGUAL_MIN_LEN = 30  # Bu uzunluktan kısa options.* key'leri skip edilir

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
            # Kontrol karakterleri, § format kodları, \n VE boşluklar hariç tümünü map'e al.
            # DÜZELTME (#2 — boş space-glyph): U+0020 ve U+00A0 (NBSP) ASLA PUA'ya
            # map EDİLMEZ. Aksi halde font_generator bu hücrelere boş glyph çizer,
            # ikinci dilin kelime araları sıfır-genişlikli olur → kelimeler birbirine
            # girer / "fer" gibi sözcükler "f er" diye yanlış noktadan bölünür.
            # Boşluklar olduğu gibi (ASCII) bırakılınca default fontun 4px kırılabilir
            # boşluğu kullanılır ve word-wrap doğru çalışır.
            if cp >= 32 and ch not in ('§', ' ', ' '):
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
    """Verilen metindeki her karakteri charmap'e göre PUA'ya çevirir.
    §X format kodları (§r, §7, §o, §e, §f vb.) korunur — hem § hem de
    sonraki karakter PUA'ya çevrilmez."""
    result = []
    skip_next = False
    for ch in text:
        if skip_next:
            # § sonrası format kodu karakteri — olduğu gibi geç
            result.append(ch)
            skip_next = False
        elif ch == '§':
            result.append(ch)
            skip_next = True  # sonraki karakteri de koru
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
    # Tam-eşleşme skip (motor-render ayar nav/başlık veya dar buton key'leri)
    if key in SKIP_EXACT_KEYS:
        return True

    # Dinamik runtime parametresi içeriyor mu?
    if DYNAMIC_PARAM_RE.search(primary_value):
        return True

    # Devre dışı bırakılan prefix'ler
    if key.startswith(SKIP_KEY_PREFIXES):
        return True

    # menu.* iki veya daha çok segmentliyse (menu.X.tab.Y, menu.X.access…)
    # bu motor-render ayar başlık/açıklamalarıdır → tofu. Skip.
    # Tek-segmentli menu.X (menu.play/settings/quit…) pack-buton → bilingual kalır.
    if key.startswith('menu.') and key.count('.') >= 2:
        return True

    # Suffix bazlı skip (settings nav tab label'ları vs.)
    if key.endswith(SKIP_KEY_SUFFIXES):
        return True

    # options.* prefix'li kısa key'ler: settings nav toggle label'larıdır
    # 30px fixed-height toggle button'larda ikinci satır görüntülenemez
    clean_primary = re.sub(r'§.', '', primary_value).strip()
    if key.startswith('options.') and len(clean_primary) <= OPTIONS_BILINGUAL_MIN_LEN:
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
# Inline (yan yana) başlık key'leri  —  DÜZELTME #3
# ---------------------------------------------------------------------------
# Sandık / fırın / crafting GUI başlık çubukları çok dardır (yükseklik ~10px) ve
# hemen altında OPAK eşya ızgarası başlar. EN/FR'yi alt alta zorladığımızda 2.
# satır (FR) ızgaranın arkasında kalıp görünmez olur (overdraw). Bu yüzden bu
# key'lerde dolgu-ile-sarma YERİNE tek satırda "EN / FR" yan yana gösteriyoruz.
# '/' başlık renginde (default font), FR ise §r§7§o ile gri-italik (PUA).
INLINE_TITLE_EXTRA_KEYS = {
    # Bu bloklar container.* key'i kullanmaz; başlık tile.*.name'den gelir.
    'tile.furnace.name',
    'tile.blast_furnace.name',
    'tile.smoker.name',
    # Normal fırın başlığı motorda $container_title = furnaceScreen.header'dan
    # gelir (container.furnace değil). Dar başlık çubuğu → inline.
    'furnaceScreen.header',
}
# Tek-segmentli container.* başlığı olsa da inline YAPILMAYACAK key'ler:
INLINE_TITLE_EXCLUDE_KEYS = {
    # Envanter başlığı dikey alana sahip ve alt alta DÜZGÜN çalışıyor (kanıtlı
    # ekran görüntüsü) — bozmuyoruz, alt alta bırakıyoruz.
    'container.inventory',
}
# Güvenlik üst sınırı: bu uzunluğu aşan başlıklar tek satıra sığmaz.
INLINE_TITLE_MAX_LEN = 24


def is_inline_title_key(key: str, clean_primary: str) -> bool:
    """Dar tek-satır başlık çubuğunda render edilen, inline gösterilmesi gereken key mi?

    Yalnızca GERÇEK başlıkları hedefler: 'container.X' / 'container.X_block' gibi
    tek-segmentli key'ler. 'container.smithing_table.template_slot_tooltip' gibi
    çok-segmentli tooltip/label key'leri alt alta (stacked) kalır."""
    if key in INLINE_TITLE_EXCLUDE_KEYS:
        return False
    if key in INLINE_TITLE_EXTRA_KEYS:
        return True
    # HUD etkileşim ipuçları (Trade/Stand/Board...): motorun tek-satır, SARMAYAN
    # prompt çubuğunda render edilir. Alt alta zorlamak için eklenen dolgu, EN ve
    # FR'yi çubuğun iki ucuna itip kocaman boşluk bırakıyordu. Inline ("/" ile)
    # boşluksuz, kompakt "Trade / Commercer" verir.
    if key.startswith('action.interact.'):
        return True
    if (key.startswith('container.')
            and key.count('.') == 1
            and len(clean_primary) <= INLINE_TITLE_MAX_LEN):
        return True
    return False


def use_newline_stack(key: str) -> bool:
    """item.* / tile.* adlari: dolgu yerine GERCEK satir sonu ile FR'yi
    dogrudan alta, hizali koy. Bu adlar merkez-hizali HUD/tooltip etiketlerinde
    gosterilir; dolgu bosluklari EN'i kaydirip hizasiz birakir + arka plani tasirir."""
    # GERI ALINDI: \n yaklasimi riskliydi (Bedrock .lang literal '\n' gosterebilir)
    # ve kullanici istemedi. Esya/blok adlari tekrar dolgu (padding) ile alt satira iner.
    return False


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

        # İkinci dili PUA'ya çevir
        pua_text = translate_to_pua(secondary_val, charmap)
        clean_primary = re.sub(r'§.', '', primary_val).strip()

        # DÜZELTME #3: Dar başlık çubukları (container.* başlıkları + blast
        # furnace/smoker) için EN/FR'yi alt alta zorlamak yerine TEK satırda
        # yan yana göster; böylece 2. satır opak eşya ızgarasının arkasında
        # kaybolmaz. '/' başlık renginde, FR ise §r§7§o ile gri-italik.
        if is_inline_title_key(key, clean_primary):
            merged[key] = f'{primary_val} / §r§7§o{pua_text}'
            continue

        # DÜZELTME: item/tile adları merkez-hizalı HUD/tooltip etiketlerinde
        # gösterilir. Dolgu boşlukları EN'i sola kaydırıp FR ile hizasız bırakıyor
        # + arka planı taşırıyor. Gerçek satır sonu ile FR'yi DOĞRUDAN alta koy.
        # (\\n = ters-bölü+n; .lang'da gerçek newline byte YOK — Bedrock kırar.)
        if use_newline_stack(key):
            merged[key] = f'{primary_val}\\n§r§7§o{pua_text}'
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
