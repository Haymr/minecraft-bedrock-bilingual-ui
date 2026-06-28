"""
ui_fixups.py — Bilingual Bedrock UI ek düzeltmeleri (post-pass)

ui_modifier.py'dan SONRA çalıştırılır. İdempotenttir (tekrar çalıştırmak güvenli).
İki sistemik hatayı düzeltir:

DÜZELTME #1 — Tek-satır yükseklik kırpması:
  Metin düğmelerinin label'ı, enjekte edilen "max_size":[200,"default"]'a rağmen
  şablonun kendi tek-satırlık yüksekliğiyle (height=10) 2. (FR) satırı kırpıyordu.
  Özellikle ui_template_buttons.json > new_ui_binding_button_label içinde max_size
  İKİ KEZ tanımlı; ikinci (yükseklik 10) kazanıyor. Bu yükseklikleri 20'ye (≈2 satır)
  çıkararak FR satırının düğme içinde görünmesini sağlıyoruz.

DÜZELTME #4 — Ayarlar fontu (tofu + literal §):
  Özel glyph_E1.png atlası YALNIZCA "default" fontu besler. font_type "smooth" /
  "MinecraftTen" kullanan Ayarlar etiketleri PUA Fransızcasını tofu (□) gösterir ve
  o render yolu § kodlarını düz metin basar. settings_sections içindeki çevrilen
  etiketleri "default" fonta zorlayarak Fransızcanın görünmesini deniyoruz.
  NOT: Bu, smooth/MinecraftTen tipografisini default piksel fontuna çevirir
  (kasıtlı ödünleşim). Dropdown DEĞER metinleri motor tarafından çizildiği için
  bu yöntemle düzelmeyebilir → oyun-içi test gerekir.
"""

import os
import re

BASE = os.path.dirname(__file__)
UI_DIR = os.path.join(BASE, '..', '..', 'resource_pack', 'ui')

# --- DÜZELTME #1: tek-satır buton yüksekliklerini 10 → 20 -------------------
# (dosya_göreli_yol, eski_alt_dize, yeni_alt_dize)
HEIGHT_FIXES = [
    # Merkez şablon: TÜM new_ui_binding_button_label tabanlı düğmeleri etkiler.
    ('ui_template_buttons.json',
     '"$button_text_max_size|default": [ "100%", 10 ]',
     '"$button_text_max_size|default": [ "100%", 20 ]'),
    # Açık piksel-genişlikli geçersiz kılmalar:
    ('in_bed_screen.json',
     '"$button_text_max_size": [ 120, 10 ]',
     '"$button_text_max_size": [ 120, 20 ]'),
    ('skin_picker_screen.json',
     '"$button_text_max_size": [ 120, 10 ]',
     '"$button_text_max_size": [ 120, 20 ]'),
]

# --- DÜZELTME #5: Crafting başlığı "Crafting / ..." ellipsis -----------------
# "Crafting / Fabrication" inline metni, crafting_label kutusuna (84px) sığmayıp
# "..." ile kırpılıyordu. Kutuyu genişletiyoruz. Pocket'ta, dosyadaki 2x2'nin
# kanıtlı yöntemini birebir uyguluyoruz: size "200%" + offset "-50%" (etiketi
# dar panelin üzerinde 2 katı genişlikte ortalar, çevredeki boş alana taşar).
CRAFTING_FIXES = [
    # Desktop (inventory_screen.json): sabit genişliği büyüt.
    ('inventory_screen.json', '"size": [ 84, 10 ],', '"size": [ 140, 10 ],'),
    ('inventory_screen.json', '"size": [ 66, 10 ],', '"size": [ 140, 10 ],'),
    # Pocket (inventory_screen_pocket.json): 3x3 etiketini 200%/-50% ile genişlet.
    ('inventory_screen_pocket.json',
     '          "max_size": [ 200, "default" ],\n'
     '          "size": [ "100%", 10 ],\n'
     '          "text_alignment": "$grid_label_alignment"\n'
     '        }\n'
     '      },\n'
     '      {\n'
     '        "crafting_grid_3x3@crafting_pocket.crafting_grid_3x3": {',
     '          "max_size": [ 200, "default" ],\n'
     '          "size": [ "200%", 10 ],\n'
     '          "offset": [ "-50%", 0 ],\n'
     '          "text_alignment": "$grid_label_alignment"\n'
     '        }\n'
     '      },\n'
     '      {\n'
     '        "crafting_grid_3x3@crafting_pocket.crafting_grid_3x3": {'),
]

# --- DÜZELTME #4: settings_sections içinde non-default fontları default'a çek -
# Yalnızca *font_type* aileli anahtarlardaki "smooth"/"MinecraftTen"/"rune"/
# "unicode" değerleri hedeflenir (texture vb. değerlere dokunulmaz).
FONT_TYPE_RE = re.compile(
    r'("\$?[a-z_]*font_type[a-z_|]*"\s*:\s*)"(?:smooth|MinecraftTen|rune|unicode)"'
)
SETTINGS_DIR = os.path.join(UI_DIR, 'settings_sections')


def apply_replacements(fixes, tag: str) -> int:
    changed = 0
    for fname, old, new in fixes:
        path = os.path.join(UI_DIR, fname)
        if not os.path.exists(path):
            print(f'  UYARI: {fname} bulunamadı, atlanıyor')
            continue
        text = open(path, encoding='utf-8').read()
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            open(path, 'w', encoding='utf-8').write(text)
            changed += n
            print(f'  {tag} {fname}: {n} değişiklik')
        elif text.count(new) == 0:
            # Ne eski ne yeni varsa: hedef metin değişmiş olabilir — uyar.
            print(f'  UYARI: {tag} {fname}: hedef alt-dize bulunamadı')
    return changed


def apply_font_fixes() -> int:
    changed = 0
    if not os.path.isdir(SETTINGS_DIR):
        print('  UYARI: settings_sections/ bulunamadı')
        return 0
    for fname in sorted(os.listdir(SETTINGS_DIR)):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(SETTINGS_DIR, fname)
        text = open(path, encoding='utf-8').read()
        new_text, n = FONT_TYPE_RE.subn(r'\1"default"', text)
        if n:
            open(path, 'w', encoding='utf-8').write(new_text)
            changed += n
            print(f'  #4 settings_sections/{fname}: {n} font_type → default')
    return changed


if __name__ == '__main__':
    print('[ui_fixups] DÜZELTME #1 — buton/label yükseklik kırpması...')
    h = apply_replacements(HEIGHT_FIXES, '#1')
    print('[ui_fixups] DÜZELTME #5 — Crafting başlığı genişletme...')
    c = apply_replacements(CRAFTING_FIXES, '#5')
    # DÜZELTME #4 (font_type → default) GERİ ALINDI: Ayarlar/dünya-oluşturma
    # ekranları metni motor tarafından § işlenmeden + PUA fontu olmadan ham
    # render ediyor; font_type değiştirmek tofu'yu çözmedi. Artık bu key'ler
    # parser.py'de skip ediliyor (temiz İngilizce). apply_font_fixes ÇAĞRILMIYOR.
    print(f'ui_fixups tamamlandı: #1 {h}, #5 {c} düzeltme. (#4 geri alındı — bkz. parser skip)')
