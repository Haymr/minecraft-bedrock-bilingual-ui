# Bilingual Bedrock UI Addon (v5.0 Final)

Bu proje, Minecraft Bedrock Edition (iOS 26 / Bedrock 1.26.0+) için tasarlanmış bağımsız bir arayüz (UI) eklentisidir. Herhangi bir script API veya Marketplace bağımlılığı olmadan, Bedrock'un native JSON UI ve Font render motorunu kullanarak **Aynı anda çift dilli arayüz** sunmayı hedefler.

## Sistem Mimarisi

Bedrock `.lang` dosyaları satır sonu (newline - `\n`) karakterlerini native olarak desteklemez. Bu proje, çift dil desteğini sağlamak için şu akıllı mimariyi kullanır:
1. İkinci dilin tüm karakterleri "Private Use Area" (PUA) Unicode bloklarına (`\uE100` - `\uE1FF`) taşınır.
2. Özel olarak üretilmiş `glyph_E1.png` font dosyası `textures/font/` altına yüklenir. Bedrock bu dosyayı native olarak donanım hızlandırmalı render eder.
3. İngilizce ve Fransızca dilleri arasına UI objesinin ekran genişliğine (`max_size`) tam oturacak şekilde matematiksel olarak boşluk (padding) eklenir. Bedrock'un *word-wrap* mekanizması yazıyı bu padding'in sonundan otomatik olarak kırıp ikinci dili alt satıra atar.

## Compiler Pipeline (Derleme Aşamaları)

Tüm süreç 3 adet Python scripti ile otomatikleştirilmiştir:

1. **`parser.py` (PUA & Padding Engine)**
   * `en_US.lang` ve `fr_FR.lang` dosyalarını alır.
   * `fr_FR`'deki karakterleri analiz edip `charmap.json` tablosu oluşturur (Max 127 glif).
   * İki dizeyi aralarına padding ve format kodları (`§r§7§o`) koyarak birleştirir ve `resource_pack/texts/en_US.lang` dosyasına yazar.

2. **`font_generator.py` (Bedrock Native Atlas Generator)**
   * `charmap.json` dosyasını okur.
   * macOS sistem fontlarını kullanarak her karakteri 16x16 ızgara içerisine (beyaz + alpha opacity ile) render eder.
   * 256x256 boyutunda `resource_pack/textures/font/glyph_E1.png` atlasını oluşturur.

3. **`ui_modifier.py` (JSON Inheritance Injector)**
   * Bedrock JSON UI dosyalarındaki `type: label` veya `@common.label` kalıtımını (inheritance) kullanarak miras alan etiketleri bulur.
   * Sadece hedeflenen bileşenlere `"wrap": true` ve `"max_size": [GENIŞLIK, "default"]` enjekte eder. `start_screen` gibi ana dosyaları es geçmez, ancak arayüzü bozabilecek `credits_text` gibi bileşenleri kara listeye alarak atlar.

## Kurulum ve Kullanım
Oluşturulan `Bilingual_UI.mcpack` dosyasını doğrudan iPad/iPhone veya Windows 10 cihazınızdan açmanız yeterlidir. "Global Kaynaklar" menüsünden etkinleştirdiğinizde oyun otomatik olarak İngilizce ve Alt-Satırda Fransızca (Gri İtalik) şekline bürünecektir.
