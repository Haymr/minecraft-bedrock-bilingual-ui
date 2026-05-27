# AI CONTEXT PRESERVATION DOCUMENT - BILINGUAL BEDROCK UI PROJECT

## PROJE KİMLİĞİ
Proje: Minecraft Bedrock Çift Dil Arayüz Modifikasyonu (Client-Side Resource Pack).
Platform: iOS 26 ve üzeri cihazlar (Marketplace olmadan .mcpack import yöntemi).
Hedef: Eşya ve arayüz metinlerinde 2 dili aynı anda göstermek. İkinci dil alt satırda, 1 blok girintili (indent), soluk (gri), italik ve daha küçük font boyutunda olmalıdır.

## MİMARİ KARARLAR VE SIKILAR KISITLAMALAR (BUNLARI ASLA İHLAL ETME)
1. **KISITLAMA**: Bedrock .lang dosyalarında \n veya \r\n YASAKTIR. Oyun motoru bu karakterleri işleyemez. 
   **ÇÖZÜM**: Yeni satır, derleyicide metin grubuna özel (menu: 200px, item: 180px vb.) hesaplanan padding ile JSON UI'deki max_size / wrap sınırları aşılarak tetiklenir.
2. **KISITLAMA**: font_size değişkeni Bedrock JSON UI'de metnin sadece bir kısmına uygulanamaz.
   **ÇÖZÜM**: `font/default.json` kullanılarak `\ue100` aralığına yeni bir font dosyası (`bilingual_font.png`) bağlanmıştır. Orijinal `default8.png` silinmez, üzerine yazılmaz.
3. **KISITLAMA**: Dinamik parametreler (`%s`, `{0}`) içeren satırların veya dinamik UI alanlarının (Scoreboard, Komutlar, Erişilebilirlik) statik padding ile kırılmaması gerekir.
   **ÇÖZÜM**: Python derleyicisi bu kelimeleri otomatik olarak atlar (skip) ve çift dil enjeksiyonu yapmaz.
4. **BİÇİMLENDİRME**: İkinci dile geçiş string'i şu formatı taşımaktadır: `[PADDING] + §r + §7 + §o + [İndent] + [Küçültülmüş Unicode Çevirisi]`.

## DOSYA AĞACI VE ÇALIŞMA ORTAMI
- `/compiler/src/parser.py`: Dinamik padding, PUA unicode dönüşümü ve dinamik değişken atlama mantığını içerir.
- `/compiler/src/ui_modifier.py`: Oyundaki tüm (~206 adet) `.json` arayüz dosyasını tarayarak `"wrap": true` parametresini enjekte eder.
- `/compiler/src/font_generator.py`: `default.json` font konfigürasyonunu ve `bilingual_font.png` şablonunu oluşturur.
- `/resource_pack/texts/en_US.lang`: Tüm oyun metinlerini (korunmuş satırlar hariç) barındıran derlenmiş dosya.
- `/resource_pack/ui/`: Kapsamlı şekilde `"wrap": true` enjekte edilmiş tüm oyun UI dosyaları.
- `/resource_pack/font/`: `default.json` ve `bilingual_font.png` (Custom PUA glifleri) burada saklanır.
- `/Bilingual_UI.mcpack`: Oyuna aktarılmaya hazır son sürümdür.
