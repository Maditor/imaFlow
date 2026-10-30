(function () {
    var csInterface = new CSInterface();

    var aiCopyMarkBtn = document.getElementById("aiCopyMarkBtn");
    var aiPasteAlignBtn = document.getElementById("aiPasteAlignBtn");

    var settingsToggleBtn = document.getElementById("settingsToggleBtn");
    var settingsPanel = document.getElementById("settingsPanel");
    var settingsCloseBtn = document.getElementById("settingsCloseBtn");

    var exePathInput = document.getElementById("exePathInput");
    var browseExeBtn = document.getElementById("browseExeBtn");

    var promptText = document.getElementById("promptText");
    var hideStatusCheckbox = document.getElementById("hideStatusCheckbox");

    var aiStatus = document.getElementById("aiStatus");

    var PROMPT_STORAGE_KEY = "imaFlow.savedPrompt";
    var EXE_PATH_STORAGE_KEY = "imaFlow.geminiWidgetExePath";
    var HIDE_STATUS_STORAGE_KEY = "imaFlow.hideStatus";

    function setStatus(text, isError) {
        aiStatus.textContent = text;
        aiStatus.style.color = isError ? "#e08787" : "#7fd77f";
    }

    function openExternal(url) {
        csInterface.openURLInDefaultBrowser(url);
    }

    /* ---------- Copy & Mark / Paste & Align ---------- */
    aiCopyMarkBtn.addEventListener("click", function () {
        setStatus("Đang copy vùng chọn...");
        csInterface.evalScript("aiCopyAndMark()", function (result) {
            result = result || "";
            var parts = result.split("||");
            var message = parts[0];
            var copied = message.indexOf("Đã copy") === 0;
            setStatus(message || "Đã copy + tạo marker.", !copied);
            // Chỉ tự dán khi copy THÀNH CÔNG (ảnh đã nằm trong clipboard)
            if (copied) {
                if (parts[1]) {
                    var ids = parts[1].split("|");
                    autoPlace.addMarker(ids[0], ids[1]);
                }
                sendToGemini(parts[1] || "");
            }
        });
    });

    aiPasteAlignBtn.addEventListener("click", function () {
        setStatus("Đang paste + canh chỉnh...");
        csInterface.evalScript("aiPasteToMarker()", function (result) {
            setStatus(result || "Đã paste + canh chỉnh xong.", result && result.indexOf("Lỗi") === 0);
        });
    });


    /* ---------- Tự dán ảnh Gemini TẢI VỀ vào đúng marker ---------- */
    // Theo dõi thư mục tải về (mặc định Downloads). Có file ảnh mới khớp tên
    // (mặc định "Gemini_Generated_Image") -> đợi tải xong -> đặt vào marker cũ nhất
    // đang chờ (hàng chờ FIFO theo thứ tự Copy & Mark), resize + mask như Paste & Align.
    var AUTO_PLACE_ON_KEY = "imaFlow.autoPlaceOn";            // nguồn chính: ảnh "Sao chép" trong Gemini
    var AUTO_PLACE_DL_KEY = "imaFlow.autoPlaceDownloads";     // nguồn phụ: thư mục tải về
    var AUTO_PLACE_DIR_KEY = "imaFlow.autoPlaceDir";
    var AUTO_PLACE_PREFIX_KEY = "imaFlow.autoPlacePrefix";
    var AUTO_PLACE_DELETE_KEY = "imaFlow.autoPlaceDelete";
    var DEFAULT_PREFIX = "Gemini_Generated_Image";
    var IMAGE_EXT = /\.(png|jpe?g|webp)$/i;

    var autoPlace = (function () {
        var fs, path, os;
        try {
            fs = require("fs");
            path = require("path");
            os = require("os");
        } catch (e) {}

        var markers = [];      // [{docID, layerID}] — cũ nhất ở đầu
        var sources = [];      // [{dir, isResult, watcher, lastListing}]
        var startedAt = 0;
        var seen = {};         // file đã xử lý / đang xử lý
        var queue = Promise.resolve();
        var pollTimer = null;

        // GeminiWidget lưu ảnh vừa "Sao chép" trong Gemini vào đây, tên file mang ID marker
        function resultsDir() {
            try {
                var base = process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
                return path.join(base, "GeminiWidget", "results");
            } catch (e) { return ""; }
        }

        function getBool(key, def) {
            try {
                var v = localStorage.getItem(key);
                return v === null ? def : v === "1";
            } catch (e) { return def; }
        }

        function defaultDir() {
            try { return path.join(os.homedir(), "Downloads"); } catch (e) { return ""; }
        }

        function getDir() {
            var d = "";
            try { d = (localStorage.getItem(AUTO_PLACE_DIR_KEY) || "").trim(); } catch (e) {}
            return d || defaultDir();
        }

        function getPrefix() {
            try {
                var p = localStorage.getItem(AUTO_PLACE_PREFIX_KEY);
                return p === null ? DEFAULT_PREFIX : p.trim();
            } catch (e) { return DEFAULT_PREFIX; }
        }

        function matches(name, src) {
            if (!IMAGE_EXT.test(name)) return false;
            if (src.isResult) return name.indexOf("imaflow_result_") === 0;
            var prefix = getPrefix();
            return !prefix || name.toLowerCase().indexOf(prefix.toLowerCase()) === 0;
        }

        function evalScriptP(script) {
            return new Promise(function (resolve) {
                csInterface.evalScript(script, function (r) { resolve(r || ""); });
            });
        }

        function delay(ms) {
            return new Promise(function (r) { setTimeout(r, ms); });
        }

        // Đợi trình duyệt ghi xong file: kích thước > 0 và không đổi qua 2 lần đo liên tiếp
        function waitStable(file) {
            var last = -1, same = 0, tries = 0;
            return new Promise(function (resolve) {
                (function tick() {
                    tries++;
                    var size = -1;
                    try { size = fs.statSync(file).size; } catch (e) {}
                    if (size > 0 && size === last) same++; else same = 0;
                    last = size;
                    if (same >= 2) return resolve(true);
                    if (tries > 100) return resolve(false); // ~30 giây
                    setTimeout(tick, 300);
                })();
            });
        }

        function placeOne(file, src) {
            var name = path.basename(file);
            return waitStable(file).then(function (ok) {
                if (!ok) {
                    setStatus("Ảnh " + name + " tải chưa xong / không đọc được.", true);
                    return;
                }
                if (src.isResult) {
                    // imaflow_result_<docID>_<layerID>_<time>.png -> dán đúng marker của lần gửi đó
                    var m = /^imaflow_result_(\d+)_(\d+)_/.exec(name);
                    var target = m && m[1] !== "0" ? { docID: m[1], layerID: m[2] } : null;
                    return placeResult(file, name, target, 0);
                }
                return tryMarkers(file, name, 0);
            });
        }

        function removeMarker(docID, layerID) {
            for (var i = 0; i < markers.length; i++) {
                if (String(markers[i].docID) === String(docID) && String(markers[i].layerID) === String(layerID)) {
                    markers.splice(i, 1);
                    return;
                }
            }
        }

        function placeResult(file, name, target, busyRetries) {
            if (!target) return tryMarkers(file, name, busyRetries, true);
            var script = 'aiPlaceFileToMarker("' + encodeURIComponent(file) + '",' +
                (parseInt(target.docID, 10) || 0) + "," + (parseInt(target.layerID, 10) || 0) + ")";
            setStatus("Đang tự dán ảnh vừa sao chép...");
            return evalScriptP(script).then(function (r) {
                if (r.indexOf("OK:") === 0) {
                    removeMarker(target.docID, target.layerID);
                    setStatus("Đã tự dán ảnh Gemini vào marker.");
                    try { fs.unlinkSync(file); } catch (e) {}
                    return;
                }
                if (r.indexOf("NOMARKER:") === 0) {
                    setStatus("Marker của ảnh vừa sao chép không còn — " + r.slice(9), true);
                    try { fs.unlinkSync(file); } catch (e) {}
                    return;
                }
                if (r.indexOf("Lỗi") !== 0 && busyRetries < 20) {
                    return delay(1500).then(function () { return placeResult(file, name, target, busyRetries + 1); });
                }
                setStatus(r || "Không tự dán được ảnh.", true);
            });
        }

        // Thử marker cũ nhất; nếu marker đó không còn (đã dán tay / xoá) thì bỏ, thử cái kế.
        function tryMarkers(file, name, busyRetries, alwaysDelete) {
            var m = markers[0] || { docID: 0, layerID: 0 }; // hết hàng chờ -> dùng layer Pending_AI_ đang chọn
            var script = 'aiPlaceFileToMarker("' + encodeURIComponent(file) + '",' +
                (parseInt(m.docID, 10) || 0) + "," + (parseInt(m.layerID, 10) || 0) + ")";
            setStatus("Đang tự dán " + name + "...");
            return evalScriptP(script).then(function (r) {
                if (r.indexOf("OK:") === 0) {
                    if (markers.length) markers.shift();
                    setStatus(r.slice(3));
                    if (alwaysDelete || getBool(AUTO_PLACE_DELETE_KEY, false)) {
                        try { fs.unlinkSync(file); } catch (e) {}
                    }
                    return;
                }
                if (r.indexOf("NOMARKER:") === 0) {
                    if (markers.length) {
                        markers.shift();
                        return tryMarkers(file, name, busyRetries, alwaysDelete);
                    }
                    setStatus("Có ảnh mới (" + name + ") nhưng không có marker nào đang chờ.", true);
                    return;
                }
                // "EvalScript error." thường do Photoshop đang bận (đang mở hộp thoại, đang vẽ...) -> thử lại
                if (r.indexOf("Lỗi") !== 0 && busyRetries < 20) {
                    return delay(1500).then(function () { return tryMarkers(file, name, busyRetries + 1, alwaysDelete); });
                }
                setStatus(r || "Không tự dán được ảnh.", true);
            });
        }

        function onCandidate(name, src) {
            if (!name || !matches(name, src)) return;
            var file = path.join(src.dir, name);
            if (seen[file]) return;
            var st;
            try { st = fs.statSync(file); } catch (e) { return; } // file tạm đã đổi tên/xoá
            if (!st.isFile() || st.mtime.getTime() < startedAt - 2000) return; // file cũ có sẵn
            seen[file] = true;
            queue = queue.then(function () { return placeOne(file, src); })
                         .catch(function () {});
        }

        // fs.watch trên Windows đôi khi bỏ sót sự kiện -> quét bổ sung mỗi 2 giây
        function pollSource(src) {
            var names;
            try { names = fs.readdirSync(src.dir); } catch (e) { return; }
            var listing = {};
            for (var i = 0; i < names.length; i++) {
                listing[names[i]] = true;
                if (!src.lastListing[names[i]]) onCandidate(names[i], src);
            }
            src.lastListing = listing;
        }

        function poll() {
            for (var i = 0; i < sources.length; i++) pollSource(sources[i]);
        }

        function stop() {
            for (var i = 0; i < sources.length; i++) {
                if (sources[i].watcher) { try { sources[i].watcher.close(); } catch (e) {} }
            }
            sources = [];
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = null;
        }

        function addSource(dir, isResult) {
            var src = { dir: dir, isResult: isResult, watcher: null, lastListing: {} };
            try {
                var names = fs.readdirSync(dir);
                for (var i = 0; i < names.length; i++) src.lastListing[names[i]] = true;
            } catch (e) {}
            try {
                src.watcher = fs.watch(dir, function (evt, name) {
                    if (name) setTimeout(function () { onCandidate(String(name), src); }, 200);
                });
            } catch (e) {}
            sources.push(src);
        }

        function start() {
            stop();
            if (!fs) return;
            startedAt = Date.now();

            if (getBool(AUTO_PLACE_ON_KEY, true)) {
                var rd = resultsDir();
                // Tạo từng cấp (Node đời cũ trong Photoshop 2018 chưa có mkdirSync recursive)
                try { if (!fs.existsSync(path.dirname(rd))) fs.mkdirSync(path.dirname(rd)); } catch (e) {}
                try { if (!fs.existsSync(rd)) fs.mkdirSync(rd); } catch (e) {}
                if (rd && fs.existsSync(rd)) addSource(rd, true);
            }

            if (getBool(AUTO_PLACE_DL_KEY, false)) {
                var dl = getDir();
                if (dl && fs.existsSync(dl)) addSource(dl, false);
                else setStatus("Không thấy thư mục tải về: " + dl, true);
            }

            if (sources.length) pollTimer = setInterval(poll, 2000);
        }

        return {
            start: start,
            stop: stop,
            addMarker: function (docID, layerID) {
                markers.push({ docID: docID, layerID: layerID });
                if (markers.length > 20) markers.shift();
            },
            defaultDir: defaultDir
        };
    })();

    /* ---------- Tự dán ảnh + prompt vào Gemini (nhờ GeminiWidget.exe) ---------- */
    // Ghi prompt ra file tạm rồi gọi GeminiWidget.exe --autopaste <file>.
    // Widget sẽ: đưa Gemini ra trước -> Ctrl+V dán ảnh (đang ở clipboard) -> dán prompt.
    // KHÔNG tự bấm Enter. Ở đây tuyệt đối không ghi đè clipboard để ảnh còn nguyên.
    function sendToGemini(marker) {
        var exePath = localStorage.getItem(EXE_PATH_STORAGE_KEY);
        if (!exePath) {
            setStatus("Tự dán cần GeminiWidget.exe — chọn đường dẫn trong Cài đặt.", true);
            return;
        }
        try {
            var fs = require("fs");
            var os = require("os");
            var path = require("path");
            if (!fs.existsSync(exePath)) {
                setStatus("Không thấy GeminiWidget.exe ở đường dẫn đã lưu — kiểm tra lại trong Cài đặt.", true);
                return;
            }
            var promptFile = path.join(os.tmpdir(), "imaflow_prompt.txt");
            fs.writeFileSync(promptFile, localStorage.getItem(PROMPT_STORAGE_KEY) || "", "utf8");

            var spawn = require("child_process").spawn;
            var args = ["--autopaste", promptFile];
            if (marker) args.push("--marker", marker);
            spawn(exePath, args, { detached: true, stdio: "ignore" }).unref();
            setStatus("Đã copy — đang dán ảnh + prompt vào Gemini...");
        } catch (e) {
            setStatus("Không gọi được GeminiWidget để tự dán.", true);
        }
    }

    /* ---------- Mở Gemini: ưu tiên chạy đúng GeminiWidget.exe đã cài đặt ---------- */
    function openGeminiPinnable() {
        var savedExePath = localStorage.getItem(EXE_PATH_STORAGE_KEY);

        if (savedExePath) {
            try {
                var fs = require("fs");
                if (fs.existsSync(savedExePath)) {
                    var spawn = require("child_process").spawn;
                    spawn(savedExePath, [], { detached: true, stdio: "ignore" }).unref();
                    setStatus("Đã mở GeminiWidget — tự ghim always-on-top.");
                    return;
                } else {
                    setStatus("Đường dẫn GeminiWidget.exe không còn tồn tại — kiểm tra lại trong ⚙️ Cài đặt.", true);
                    // rơi xuống fallback bên dưới
                }
            } catch (e) {
                // Node integration lỗi -> rơi xuống fallback
            }
        }

        openGeminiViaBrowserAppMode();
    }

    // Fallback: chưa cài đặt đường dẫn GeminiWidget.exe -> tự dò trình duyệt
    // và mở app-mode như bản cũ (không tự ghim always-on-top được).
    function openGeminiViaBrowserAppMode() {
        var GEMINI_URL = "https://gemini.google.com/";
        var WINDOW_ARGS = ["--app=" + GEMINI_URL, "--window-size=420,760", "--window-position=1200,80"];

        try {
            var os = require("os");
            if (os.platform() !== "win32") {
                openExternal(GEMINI_URL);
                setStatus("Đã mở Gemini bằng trình duyệt ngoài.");
                return;
            }

            var fs = require("fs");
            var pf = process.env["ProgramFiles"] || "";
            var pf86 = process.env["ProgramFiles(x86)"] || "";
            var local = process.env["LocalAppData"] || "";

            var candidates = [
                local + "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                pf + "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                pf86 + "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                local + "\\CocCoc\\Browser\\Application\\browser.exe",
                pf + "\\CocCoc\\Browser\\Application\\browser.exe",
                pf86 + "\\CocCoc\\Browser\\Application\\browser.exe",
                pf + "\\Google\\Chrome\\Application\\chrome.exe",
                pf86 + "\\Google\\Chrome\\Application\\chrome.exe",
                local + "\\Google\\Chrome\\Application\\chrome.exe",
                pf86 + "\\Microsoft\\Edge\\Application\\msedge.exe",
                pf + "\\Microsoft\\Edge\\Application\\msedge.exe"
            ];

            var browserPath = null;
            for (var i = 0; i < candidates.length; i++) {
                if (candidates[i] && fs.existsSync(candidates[i])) {
                    browserPath = candidates[i];
                    break;
                }
            }

            if (!browserPath) {
                openExternal(GEMINI_URL);
                setStatus("Không tìm thấy trình duyệt nào — đã mở bằng trình duyệt mặc định.");
                return;
            }

            var spawn = require("child_process").spawn;
            spawn(browserPath, WINDOW_ARGS, { detached: true, stdio: "ignore" }).unref();
            setStatus("Đã mở Gemini dạng cửa sổ nhỏ (chưa ghim — cài đặt GeminiWidget.exe trong ⚙️ để tự ghim).");
        } catch (e) {
            openExternal(GEMINI_URL);
            setStatus("Đã mở Gemini bằng trình duyệt ngoài.");
        }
    }

    /* ---------- Prompt: bấm nút ngoài toolbar là copy liền ---------- */
    // Dung ky thuat textarea an + execCommand('copy') — chay dong bo, dang
    // tin cay trong moi truong CEP. KHONG dung navigator.clipboard.writeText()
    // vi no chay bat dong bo va co the bi CEP chan quyen ma khong bao loi gi,
    // khien status hien "da copy" du thuc te chua copy duoc.
    function copyTextToClipboard(text) {
        if (!text) return false;
        try {
            var tmp = document.createElement("textarea");
            tmp.value = text;
            tmp.style.position = "fixed";
            tmp.style.top = "0";
            tmp.style.left = "0";
            tmp.style.opacity = "0";
            document.body.appendChild(tmp);
            tmp.focus();
            tmp.select();
            tmp.setSelectionRange(0, text.length);
            var ok = document.execCommand("copy");
            document.body.removeChild(tmp);
            return ok;
        } catch (e) {
            return false;
        }
    }


    /* ---------- Submenu cài đặt ---------- */
    settingsToggleBtn.addEventListener("click", function () {
        settingsPanel.classList.toggle("hidden");
    });

    settingsCloseBtn.addEventListener("click", function () {
        settingsPanel.classList.add("hidden");
    });

    // Khôi phục dữ liệu đã lưu khi mở panel
    try {
        var savedPromptOnLoad = localStorage.getItem(PROMPT_STORAGE_KEY);
        if (savedPromptOnLoad) promptText.value = savedPromptOnLoad;
    } catch (e) {}

    try {
        var savedExeOnLoad = localStorage.getItem(EXE_PATH_STORAGE_KEY);
        if (savedExeOnLoad) exePathInput.value = savedExeOnLoad;
    } catch (e) {}

    promptText.addEventListener("input", function () {
        try {
            localStorage.setItem(PROMPT_STORAGE_KEY, promptText.value);
        } catch (e) {}
    });

    // Cho phép gõ/dán tay đường dẫn exe, không bắt buộc phải dùng nút Chọn file
    exePathInput.addEventListener("input", function () {
        try {
            localStorage.setItem(EXE_PATH_STORAGE_KEY, exePathInput.value.trim());
        } catch (e) {}
    });

    browseExeBtn.addEventListener("click", function () {
        try {
            var result = window.cep.fs.showOpenDialog(false, false, "Chọn file GeminiWidget.exe", "", ["exe"]);
            if (result && result.err === 0 && result.data && result.data.length > 0) {
                var picked = result.data[0];
                exePathInput.value = picked;
                try {
                    localStorage.setItem(EXE_PATH_STORAGE_KEY, picked);
                } catch (e) {}
                setStatus("Đã lưu đường dẫn GeminiWidget.exe.");
            }
        } catch (e) {
            setStatus("Không mở được hộp thoại chọn file — anh có thể dán tay đường dẫn vào ô bên trên.", true);
        }
    });

    /* ---------- Checkbox ẩn dòng trạng thái ---------- */
    try {
        var savedHideStatus = localStorage.getItem(HIDE_STATUS_STORAGE_KEY) === "1";
        hideStatusCheckbox.checked = savedHideStatus;
        aiStatus.classList.toggle("hidden", savedHideStatus);
    } catch (e) {}

    hideStatusCheckbox.addEventListener("change", function () {
        aiStatus.classList.toggle("hidden", hideStatusCheckbox.checked);
        try {
            localStorage.setItem(HIDE_STATUS_STORAGE_KEY, hideStatusCheckbox.checked ? "1" : "0");
        } catch (e) {}
    });

    /* ---------- Cài đặt tự dán ảnh tải về ---------- */
    var autoPlaceCheckbox = document.getElementById("autoPlaceCheckbox");
    var autoPlaceDlCheckbox = document.getElementById("autoPlaceDlCheckbox");
    var autoPlaceDlOptions = document.getElementById("autoPlaceDlOptions");
    var autoPlaceDirInput = document.getElementById("autoPlaceDirInput");
    var browseDirBtn = document.getElementById("browseDirBtn");
    var autoPlacePrefixInput = document.getElementById("autoPlacePrefixInput");
    var autoPlaceDeleteCheckbox = document.getElementById("autoPlaceDeleteCheckbox");

    function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
    function lsSet(key, v) { try { localStorage.setItem(key, v); } catch (e) {} }

    autoPlaceCheckbox.checked = lsGet(AUTO_PLACE_ON_KEY) !== "0";
    autoPlaceDlCheckbox.checked = lsGet(AUTO_PLACE_DL_KEY) === "1";
    autoPlaceDlOptions.classList.toggle("hidden", !autoPlaceDlCheckbox.checked);
    autoPlaceDirInput.value = lsGet(AUTO_PLACE_DIR_KEY) || "";
    autoPlaceDirInput.placeholder = autoPlace.defaultDir() || "Thư mục Downloads";
    autoPlacePrefixInput.value = lsGet(AUTO_PLACE_PREFIX_KEY) === null ? DEFAULT_PREFIX : lsGet(AUTO_PLACE_PREFIX_KEY);
    autoPlaceDeleteCheckbox.checked = lsGet(AUTO_PLACE_DELETE_KEY) === "1";

    var restartTimer = null;
    function restartWatcherSoon() {
        clearTimeout(restartTimer);
        restartTimer = setTimeout(autoPlace.start, 600);
    }

    autoPlaceCheckbox.addEventListener("change", function () {
        lsSet(AUTO_PLACE_ON_KEY, autoPlaceCheckbox.checked ? "1" : "0");
        autoPlace.start();
        setStatus(autoPlaceCheckbox.checked ? "Đã bật tự dán khi sao chép ảnh trong Gemini." : "Đã tắt tự dán khi sao chép ảnh.");
    });
    autoPlaceDlCheckbox.addEventListener("change", function () {
        lsSet(AUTO_PLACE_DL_KEY, autoPlaceDlCheckbox.checked ? "1" : "0");
        autoPlaceDlOptions.classList.toggle("hidden", !autoPlaceDlCheckbox.checked);
        autoPlace.start();
    });
    autoPlaceDirInput.addEventListener("input", function () {
        lsSet(AUTO_PLACE_DIR_KEY, autoPlaceDirInput.value.trim());
        restartWatcherSoon();
    });
    autoPlacePrefixInput.addEventListener("input", function () {
        lsSet(AUTO_PLACE_PREFIX_KEY, autoPlacePrefixInput.value.trim());
    });
    autoPlaceDeleteCheckbox.addEventListener("change", function () {
        lsSet(AUTO_PLACE_DELETE_KEY, autoPlaceDeleteCheckbox.checked ? "1" : "0");
    });
    browseDirBtn.addEventListener("click", function () {
        try {
            var result = window.cep.fs.showOpenDialog(false, true, "Chọn thư mục tải ảnh về", autoPlaceDirInput.value || "");
            if (result && result.err === 0 && result.data && result.data.length > 0) {
                autoPlaceDirInput.value = result.data[0];
                lsSet(AUTO_PLACE_DIR_KEY, result.data[0]);
                autoPlace.start();
                setStatus("Đang theo dõi: " + result.data[0]);
            }
        } catch (e) {
            setStatus("Không mở được hộp thoại — dán tay đường dẫn thư mục vào ô.", true);
        }
    });

    autoPlace.start();
})();
