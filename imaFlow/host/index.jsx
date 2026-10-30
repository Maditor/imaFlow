// Host script (ExtendScript) chạy trong Photoshop.

function helloFromHost() {
    return "Host script đã sẵn sàng.";
}

/* ==========================================================
   AI Copy & Mark  (tương đương phím F3 trong workflow gốc)
   - Copy vùng chọn hiện tại (merged) vào clipboard
   - Tạo layer "marker" màu neon để đánh dấu tọa độ,
     dùng để canh chỉnh lại khi paste ảnh AI về sau
   ========================================================== */
function aiCopyAndMark() {
    if (app.documents.length === 0) return "Không có document nào đang mở.";
    var doc = app.activeDocument;

    try {
        _aiLastMarker = "";
        doc.suspendHistory("Copy AI & Mark Target", "aiCopyAndMark_main()");
        // Kèm "||docID|layerID" để panel nhớ đúng marker này (tự dán ảnh tải về sau đó)
        return "Đã copy vùng chọn + tạo marker." + (_aiLastMarker ? "||" + _aiLastMarker : "");
    } catch (e) {
        return "Lỗi: " + e.message;
    }
}

var _aiLastMarker = "";

function aiCopyAndMark_main() {
    var doc = app.activeDocument;

    var bounds;
    try {
        bounds = doc.selection.bounds;
    } catch (e) {
        throw new Error("Chưa có vùng chọn (selection) nào.");
    }

    // Copy merged (toàn bộ pixel hiển thị trong vùng chọn) qua ActionManager
    // Cách 1: ActionManager (nhanh). Cách 2 (dự phòng cho Photoshop đời cũ như 2018):
    // DOM selection.copy(true) = Copy Merged. Báo kèm lý do thật nếu cả hai đều lỗi.
    var copyErr1 = "", copyErr2 = "";
    var copied = false;
    try {
        var desc = new ActionDescriptor();
        executeAction(charIDToTypeID("CpyM"), desc, DialogModes.NO);
        copied = true;
    } catch (e1) {
        copyErr1 = e1.message;
    }
    if (!copied) {
        try {
            doc.selection.copy(true);
            copied = true;
        } catch (e2) {
            copyErr2 = e2.message;
        }
    }
    if (!copied) {
        throw new Error("Không copy được (" + copyErr1 + " | " + copyErr2 + ")");
    }

    // Tạo layer marker
    var markerLayer = doc.artLayers.add();
    var timeID = new Date().getTime().toString().slice(-4);
    markerLayer.name = "Pending_AI_" + timeID;
    markerLayer.opacity = 25;
    markerLayer.blendMode = BlendMode.NORMAL;

    var colorIndex = parseInt(timeID, 10) % 4;
    var neonColor = new SolidColor();

    if (doc.mode === DocumentMode.GRAYSCALE) {
        neonColor.gray.gray = (colorIndex + 1) * 20;
    } else {
        if (colorIndex === 0) { neonColor.rgb.red = 0; neonColor.rgb.green = 255; neonColor.rgb.blue = 255; }
        else if (colorIndex === 1) { neonColor.rgb.red = 255; neonColor.rgb.green = 0; neonColor.rgb.blue = 255; }
        else if (colorIndex === 2) { neonColor.rgb.red = 50; neonColor.rgb.green = 255; neonColor.rgb.blue = 50; }
        else { neonColor.rgb.red = 255; neonColor.rgb.green = 255; neonColor.rgb.blue = 0; }
    }

    try {
        doc.selection.fill(neonColor);
        doc.selection.deselect();
    } catch (e) {}

    try {
        _aiLastMarker = _aiActiveDocID() + "|" + _aiActiveLayerID();
    } catch (e) {
        _aiLastMarker = "";
    }
}

/* ==========================================================
   AI Paste & Auto-Align  (tương đương phím F4 trong workflow gốc)
   - Yêu cầu: đang chọn layer marker, và clipboard đã có ảnh AI
   - Paste ảnh, convert Smart Object, resize + canh đúng vị trí
     marker, xoá marker, tạo mask
   ========================================================== */
var AI_PASTE_ENABLE_MASK = true;
var AI_PASTE_START_HIDDEN = false;

function aiPasteToMarker() {
    if (app.documents.length === 0) return "Không có document nào đang mở.";
    var doc = app.activeDocument;

    try {
        doc.suspendHistory("Paste AI Safe", "aiPasteToMarker_main()");
        return "Đã paste và canh chỉnh ảnh AI vào marker.";
    } catch (e) {
        return "Lỗi: " + e.message;
    }
}

function aiPasteToMarker_main() {
    _aiInsertAndAlign(function (doc) {
        try {
            doc.paste();
        } catch (e) {
            throw new Error("Clipboard đang trống — hãy copy ảnh AI trước.");
        }
        try {
            executeAction(stringIDToTypeID("newPlacedLayer"), undefined, DialogModes.NO);
        } catch (e) {
            // Không fatal — một số phiên bản Photoshop vẫn paste đúng dù bước
            // convert Smart Object báo lỗi. Bỏ qua và tiếp tục.
        }
    });
}

// Chèn ảnh (insertFn) rồi resize + canh vào layer marker đang active, rasterize,
// xoá marker, tạo mask. Dùng chung cho Paste & Align và tự dán file tải về.
function _aiInsertAndAlign(insertFn) {
    var doc = app.activeDocument;
    var markerLayer = doc.activeLayer;

    if (markerLayer.isBackgroundLayer) {
        throw new Error("Hãy chọn layer marker trước (layer neon do Copy & Mark tạo ra).");
    }

    var markerBounds = markerLayer.bounds;
    var targetLeft = markerBounds[0].as("px");
    var targetTop = markerBounds[1].as("px");
    var targetRight = markerBounds[2].as("px");
    var targetBottom = markerBounds[3].as("px");

    var targetWidth = targetRight - targetLeft;
    var targetHeight = targetBottom - targetTop;

    var markerID = -1;
    try { markerID = _aiActiveLayerID(); } catch (eId) {}

    insertFn(doc);

    var aiLayer = doc.activeLayer;
    try {
        if (markerID !== -1 && _aiActiveLayerID() === markerID) {
            throw new Error("Không chèn được ảnh vào document.");
        }
    } catch (eChk) {
        if (eChk.message === "Không chèn được ảnh vào document.") throw eChk;
    }

    var aiBounds = aiLayer.bounds;
    var aiWidth = aiBounds[2].as("px") - aiBounds[0].as("px");
    var aiHeight = aiBounds[3].as("px") - aiBounds[1].as("px");

    if (aiWidth > 0 && aiHeight > 0) {
        var scaleX = (targetWidth / aiWidth) * 100;
        var scaleY = (targetHeight / aiHeight) * 100;

        if (isFinite(scaleX) && isFinite(scaleY) && scaleX > 0 && scaleY > 0) {
            try {
                aiLayer.resize(scaleX, scaleY, AnchorPosition.MIDDLECENTER);
            } catch (e) {
                // Bỏ qua lỗi resize — ảnh vẫn đã được paste vào document,
                // chỉ là chưa tự resize khớp marker, anh chỉnh tay Ctrl+T.
            }
        }

        var newBounds = aiLayer.bounds;
        var currentLeft = newBounds[0].as("px");
        var currentTop = newBounds[1].as("px");

        var deltaX = targetLeft - currentLeft;
        var deltaY = targetTop - currentTop;

        if (isFinite(deltaX) && isFinite(deltaY)) {
            try {
                aiLayer.translate(UnitValue(deltaX, "px"), UnitValue(deltaY, "px"));
            } catch (e) {
                // Bỏ qua lỗi canh vị trí — anh có thể tự kéo layer bằng tay.
            }
        }
    }

    // Rasterize layer ảnh AI (Smart Object -> layer pixel thường) để làm việc ngay,
    // khỏi bị hộp thoại hỏi "rasterize?" khi vẽ/xoá/tô lên layer này.
    // Làm sau khi resize/canh vị trí để giữ chất lượng tối đa, và trước khi xoá marker
    // (lúc này layer ảnh AI vẫn đang là layer active).
    try {
        doc.activeLayer = aiLayer;
        executeAction(stringIDToTypeID("rasterizeLayer"), (function () {
            var d = new ActionDescriptor();
            var r = new ActionReference();
            r.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
            d.putReference(charIDToTypeID("null"), r);
            return d;
        })(), DialogModes.NO);
    } catch (e) {
        // Bỏ qua nếu rasterize lỗi — layer vẫn dán được, chỉ là còn ở dạng Smart Object.
    }

    try {
        markerLayer.remove();
    } catch (e) {}

    if (AI_PASTE_ENABLE_MASK) {
        try {
            doc.selection.deselect();

            var desc = new ActionDescriptor();
            var ref = new ActionReference();
            desc.putClass(charIDToTypeID("Nw "), charIDToTypeID("Chnl"));
            ref.putEnumerated(charIDToTypeID("Chnl"), charIDToTypeID("Chnl"), charIDToTypeID("Msk "));
            desc.putReference(charIDToTypeID("At "), ref);
            var maskType = AI_PASTE_START_HIDDEN ? charIDToTypeID("HdAl") : charIDToTypeID("RvlA");
            desc.putEnumerated(charIDToTypeID("Usng"), charIDToTypeID("UsrM"), maskType);
            executeAction(charIDToTypeID("Mk "), desc, DialogModes.NO);
        } catch (e) {
            // Bỏ qua lỗi tạo mask — anh có thể tự thêm mask bằng tay nếu cần.
        }
    }
}


/* ==========================================================
   Tự dán ảnh Gemini vừa TẢI VỀ (file) vào đúng marker
   - panel theo dõi thư mục Downloads, thấy file mới thì gọi hàm này
   - docID/layerID là của marker do Copy & Mark tạo (0 = dùng layer đang chọn)
   Trả về: "OK:..." | "NOMARKER:..." (marker không còn) | "Lỗi: ..."
   ========================================================== */
var _aiPlacePath = "";

function aiPlaceFileToMarker(encodedPath, docID, layerID) {
    if (app.documents.length === 0) return "NOMARKER:Không có document nào đang mở.";
    var filePath = decodeURIComponent(encodedPath);
    var f = new File(filePath);
    if (!f.exists) return "Lỗi: Không thấy file " + filePath;

    docID = parseInt(docID, 10) || 0;
    layerID = parseInt(layerID, 10) || 0;

    try {
        if (docID && !_aiActivateDocByID(docID)) {
            return "NOMARKER:Document chứa marker đã bị đóng.";
        }
        if (layerID && !_aiSelectLayerByID(layerID)) {
            return "NOMARKER:Layer marker không còn (có thể đã dán tay rồi).";
        }
        var active = app.activeDocument.activeLayer;
        if (!layerID && (!active || active.name.indexOf("Pending_AI_") !== 0)) {
            return "NOMARKER:Không có marker đang chờ.";
        }
    } catch (e) {
        return "NOMARKER:" + e.message;
    }

    try {
        _aiPlacePath = filePath;
        app.activeDocument.suspendHistory("Auto Place AI", "aiPlaceFileToMarker_main()");
        return "OK:Đã tự dán ảnh " + f.displayName + " vào marker.";
    } catch (e2) {
        return "Lỗi: " + e2.message;
    }
}

function aiPlaceFileToMarker_main() {
    _aiInsertAndAlign(function (doc) {
        var desc = new ActionDescriptor();
        desc.putPath(charIDToTypeID("null"), new File(_aiPlacePath));
        desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
        executeAction(charIDToTypeID("Plc "), desc, DialogModes.NO); // Place Embedded -> Smart Object
    });
}

/* ---------- Helper ActionManager (chạy được cả Photoshop đời cũ) ---------- */
function _aiActiveDocID() {
    var r = new ActionReference();
    r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("documentID"));
    r.putEnumerated(charIDToTypeID("Dcmn"), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    return executeActionGet(r).getInteger(stringIDToTypeID("documentID"));
}

function _aiActiveLayerID() {
    var r = new ActionReference();
    r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("layerID"));
    r.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    return executeActionGet(r).getInteger(stringIDToTypeID("layerID"));
}

function _aiActivateDocByID(docID) {
    try {
        if (_aiActiveDocID() === docID) return true;
    } catch (e) {}
    for (var i = 1; i <= app.documents.length; i++) {
        try {
            var r = new ActionReference();
            r.putProperty(charIDToTypeID("Prpr"), stringIDToTypeID("documentID"));
            r.putIndex(charIDToTypeID("Dcmn"), i);
            if (executeActionGet(r).getInteger(stringIDToTypeID("documentID")) === docID) {
                var d = new ActionDescriptor();
                var ref = new ActionReference();
                ref.putIdentifier(charIDToTypeID("Dcmn"), docID);
                d.putReference(charIDToTypeID("null"), ref);
                try {
                    executeAction(charIDToTypeID("slct"), d, DialogModes.NO);
                } catch (eSel) {}
                // Dự phòng cho Photoshop đời cũ: chuyển document bằng DOM
                if (_aiActiveDocID() !== docID) app.activeDocument = app.documents[i - 1];
                return _aiActiveDocID() === docID;
            }
        } catch (e2) {}
    }
    return false;
}

function _aiSelectLayerByID(layerID) {
    try {
        var d = new ActionDescriptor();
        var ref = new ActionReference();
        ref.putIdentifier(charIDToTypeID("Lyr "), layerID);
        d.putReference(charIDToTypeID("null"), ref);
        d.putBoolean(charIDToTypeID("MkVs"), false);
        executeAction(charIDToTypeID("slct"), d, DialogModes.NO);
        return _aiActiveLayerID() === layerID;
    } catch (e) {
        return false;
    }
}
