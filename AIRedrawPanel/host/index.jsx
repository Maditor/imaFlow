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
        doc.suspendHistory("Copy AI & Mark Target", "aiCopyAndMark_main()");
        return "Đã copy vùng chọn + tạo marker.";
    } catch (e) {
        return "Lỗi: " + e.message;
    }
}

function aiCopyAndMark_main() {
    var doc = app.activeDocument;

    var bounds;
    try {
        bounds = doc.selection.bounds;
    } catch (e) {
        throw new Error("Chưa có vùng chọn (selection) nào.");
    }

    // Copy merged (toàn bộ pixel hiển thị trong vùng chọn) qua ActionManager
    try {
        var desc = new ActionDescriptor();
        executeAction(charIDToTypeID("CpyM"), desc, DialogModes.NO);
    } catch (e) {
        throw new Error("Không copy được. Kiểm tra lại visibility của layer.");
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

    try {
        doc.paste();
    } catch (e) {
        throw new Error("Clipboard đang trống — hãy copy ảnh AI trước.");
    }

    var idnewPlacedLayer = stringIDToTypeID("newPlacedLayer");
    try {
        executeAction(idnewPlacedLayer, undefined, DialogModes.NO);
    } catch (e) {
        // Không fatal — một số phiên bản Photoshop vẫn paste đúng dù bước
        // convert Smart Object báo lỗi. Bỏ qua và tiếp tục.
    }

    var aiLayer = doc.activeLayer;

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
