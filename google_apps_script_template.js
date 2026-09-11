/**
 * ==============================================================================
 * AI CAMERA PEOPLE COUNTER - GOOGLE SHEETS LIVE SYNC SCRIPT
 * ==============================================================================
 * 
 * HOW TO SETUP (Takes only 1 minute):
 * 
 * 1. Open Google Drive (drive.google.com) and create a new Google Sheet.
 * 2. In the sheet menu, click "Extensions" > "Apps Script".
 * 3. Delete any existing code and PASTE THIS ENTIRE CODE there.
 * 4. Click the blue "Deploy" button (top right) > "New deployment".
 * 5. Select type: "Web app".
 * 6. Set "Who has access" to "Anyone" and click "Deploy".
 * 7. Copy the provided "Web app URL" and paste it into the Cloud Sync settings 
 *    modal in the People Counter application.
 * 
 * CONGRATULATIONS! Live entrance stats and revenue figures will now sync 
 * automatically to your Google Spreadsheet in real-time.
 * ==============================================================================
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // Auto-create header row if sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Date", 
        "Last Update Time", 
        "Men IN",
        "Men OUT",
        "Men Inside",
        "Women IN",
        "Women OUT",
        "Women Inside",
        "Total IN",
        "Total OUT",
        "Total Inside",
        "Adults", 
        "Children", 
        "Admission Rate", 
        "TOTAL REVENUE",
        "Status / Notes"
      ]);
      sheet.getRange("A1:P1").setFontWeight("bold").setBackground("#10b981").setFontColor("#ffffff");
    }

    var todayStr = data.date || data.tarih;
    var timeStr = data.time || data.saat;
    var menIn = data.men_in !== undefined ? data.men_in : (data.erkek_giris || 0);
    var menOut = data.men_out !== undefined ? data.men_out : (data.erkek_cikis || 0);
    var menInside = data.men_inside !== undefined ? data.men_inside : 0;
    var womenIn = data.women_in !== undefined ? data.women_in : (data.kadin_giris || 0);
    var womenOut = data.women_out !== undefined ? data.women_out : (data.kadin_cikis || 0);
    var womenInside = data.women_inside !== undefined ? data.women_inside : 0;
    var totalIn = data.total_in !== undefined ? data.total_in : (data.total_count || 0);
    var totalOut = data.total_out !== undefined ? data.total_out : 0;
    var totalInside = data.total_inside !== undefined ? data.total_inside : 0;
    var adults = data.adults !== undefined ? data.adults : (data.yetiskin_sayisi || 0);
    var children = data.children !== undefined ? data.children : (data.cocuk_sayisi || 0);
    var price = data.rate !== undefined ? data.rate : (data.kisi_basi_ucret || 0);
    var revenue = data.revenue !== undefined ? data.revenue : (data.toplam_ciro_tl || 0);

    // Check if row for today already exists (updates existing day row)
    var dataRange = sheet.getDataRange().getValues();
    var rowIndex = -1;

    for (var i = 1; i < dataRange.length; i++) {
      if (dataRange[i][0] == todayStr) {
        rowIndex = i + 1;
        break;
      }
    }

    var rowValues = [
      todayStr,
      timeStr,
      menIn,
      menOut,
      menInside,
      womenIn,
      womenOut,
      womenInside,
      totalIn,
      totalOut,
      totalInside,
      adults,
      children,
      price,
      revenue,
      "Live Synced"
    ];

    if (rowIndex > 0) {
      // Update existing row
      sheet.getRange(rowIndex, 1, 1, rowValues.length).setValues([rowValues]);
    } else {
      // Insert new row for today
      sheet.appendRow(rowValues);
    }

    return ContentService.createTextOutput(JSON.stringify({ "status": "success" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ "status": "error", "message": err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
