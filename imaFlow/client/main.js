(function () {
    var csInterface = new CSInterface();

    var aiCopyMarkBtn = document.getElementById("aiCopyMarkBtn");
    var aiPasteAlignBtn = document.getElementById("aiPasteAlignBtn");
    var openGeminiBtn = document.getElementById("openGeminiBtn");
    var promptCopyMainBtn = document.getElementById("promptCopyMainBtn");

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
            setStatus(result || "Đã copy + tạo marker.", result && result.indexOf("Lỗi") === 0);
        });
    });

    aiPasteAlignBtn.addEventListener("click", function () {
        setStatus("Đang paste + canh chỉnh...");
        csInterface.evalScript("aiPasteToMarker()", function (result) {
            setStatus(result || "Đã paste + canh chỉnh xong.", result && result.indexOf("Lỗi") === 0);
        });
    });

    /* ---------- Mở Gemini: ưu tiên chạy đúng GeminiWidget.exe đã cài đặt ---------- */
    openGeminiBtn.addEventListener("click", function () {
        openGeminiPinnable();
    });

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

    promptCopyMainBtn.addEventListener("click", function () {
        var saved = localStorage.getItem(PROMPT_STORAGE_KEY) || "";
        if (!saved.trim()) {
            setStatus("Chưa có prompt nào được lưu — mở ⚙️ Cài đặt để soạn prompt trước.", true);
            return;
        }
        if (copyTextToClipboard(saved)) {
            setStatus("Đã copy prompt vào clipboard.");
        } else {
            setStatus("Không copy được prompt.", true);
        }
    });

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
})();
