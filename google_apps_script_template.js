/**
 * ==============================================================================
 * KURŞUNLU PİKNİK ALANI - GOOGLE E-TABLOLAR CANLI SENKRONİZASYON KODU
 * ==============================================================================
 * 
 * BU KODU NASIL KURACAKSINIZ? (Yalnızca 1 Dakika Sürer):
 * 
 * 1. Google Drive'ınızı açın (drive.google.com) ve yeni bir Google E-Tablo (Google Sheets) oluşturun.
 * 2. Tablonun üst menüsünden "Uzantılar" (Extensions) > "Apps Script" seçeneğine tıklayın.
 * 3. Açılan kod editöründeki her şeyi silin ve AŞAĞIDAKİ TÜM KODU oraya yapıştırın.
 * 4. Sağ üstteki mavi "Dağıt" (Deploy) > "Yeni Dağıtım" (New deployment) butonuna basın.
 * 5. Sol taraftaki çark simgesinden "Web Uygulaması" (Web app) seçin.
 * 6. "Erişimi olanlar" (Who has access) kısmını "Herkes" (Anyone) olarak seçin ve "Dağıt"a tıklayın.
 * 7. Size verilen "Web Uygulaması URL'sini" kopyalayın ve bizim bilgisayar programındaki 
 *    "Google Drive" ayarları kutusuna yapıştırın.
 * 
 * TEBRİKLER! Artık tuvalete her giren kişi ve anlık kasa cirosu cep telefonunuzdaki 
 * Google Drive / Google E-Tablolar uygulamasında anında canlı güncellenecektir!
 * ==============================================================================
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // Eğer ilk satır başlıkları yoksa otomatik ekle
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Tarih", 
        "Son Güncelleme Saati", 
        "Yetişkin Sayısı", 
        "Çocuk Sayısı", 
        "Toplam Kişi", 
        "Kişi Başı Ücret (TL)", 
        "KASADAKİ TOPLAM CİRO (TL)",
        "Durum / Not"
      ]);
      sheet.getRange("A1:H1").setFontWeight("bold").setBackground("#10b981").setFontColor("#ffffff");
    }

    var todayStr = data.tarih;
    var timeStr = data.saat;
    var adults = data.yetiskin_sayisi;
    var children = data.cocuk_sayisi;
    var total = data.toplam_giris;
    var price = data.kisi_basi_ucret;
    var revenue = data.toplam_ciro_tl;

    // Tabloda bugünün satırı var mı kontrol et (Aynı güne ait satırı günceller, her güne 1 özet satırı)
    var dataRange = sheet.getDataRange().getValues();
    var rowIndex = -1;

    for (var i = 1; i < dataRange.length; i++) {
      if (dataRange[i][0] == todayStr) {
        rowIndex = i + 1;
        break;
      }
    }

    if (rowIndex > 0) {
      // Bugünün satırını güncelle
      sheet.getRange(rowIndex, 2).setValue(timeStr);
      sheet.getRange(rowIndex, 3).setValue(adults);
      sheet.getRange(rowIndex, 4).setValue(children);
      sheet.getRange(rowIndex, 5).setValue(total);
      sheet.getRange(rowIndex, 6).setValue(price);
      sheet.getRange(rowIndex, 7).setValue(revenue);
      sheet.getRange(rowIndex, 8).setValue("Canlı Senkronize");
    } else {
      // Yeni gün için satır ekle
      sheet.appendRow([
        todayStr,
        timeStr,
        adults,
        children,
        total,
        price,
        revenue,
        "Vardiya Başladı"
      ]);
    }

    return ContentService.createTextOutput(JSON.stringify({ "status": "success" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ "status": "error", "message": err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
