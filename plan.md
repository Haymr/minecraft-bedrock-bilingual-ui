# Phase 1 & 2 plan.md Kontrol Yapısı

| Durum | Kontrol Maddesi | Beklenen Çıktı / Doğrulama Kriteri |
| --- | --- | --- |
| [x] | Dizin Ağacı Oluşturuldu mu? | `compiler/src` ve `resource_pack/texts` dizinleri kök dizinde mevcut. |
| [x] | Vanilla Dosyaları Çıkarıldı mı? | Güncel Bedrock .lang dosyaları parser'a girdi olarak sağlandı. |
| [ ] | Parser Modülü Testi | Regex, `##` yorumlarını hatasız temizleyebiliyor. |
| [ ] | Padding Mantığı | Çıktı dizesi anahtar kelimeleri `§r§7` kodlarını başarıyla içeriyor. |

# Faz 3 & 4 plan.md Kontrol Yapısı

| Durum | Kontrol Maddesi | Beklenen Çıktı / Doğrulama Kriteri |
| --- | --- | --- |
| [ ] | default8.png Düzenlemesi | Minyatür harfler belirtilen özel unicode slotlarına yerleştirildi. |
| [ ] | JSON UI Genişlik Sabitleme | `inventory_screen.json` içinde tooltip `max_size` değerleri ayarlandı. |
| [ ] | .mcpack Oluşturma | `manifest.json` formatı geçerli, UUID çakışması yok. |
| [ ] | iOS Kurulum Doğrulaması | Oyun kapalıyken içe aktarıldığında "İçe aktarma başarılı" uyarısı alındı. |
| [ ] | Eşya Lore Testi | Büyülü "Netherite Sword" gibi uzun metinler ekrandan taşmıyor. |
