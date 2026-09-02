(function () {
    var csInterface = new CSInterface();

    var aiCopyMarkBtn = document.getElementById("aiCopyMarkBtn");
    var aiPasteAlignBtn = document.getElementById("aiPasteAlignBtn");
    var openGeminiBtn = document.getElementById("openGeminiBtn");
    var promptToggleBtn = document.getElementById("promptToggleBtn");

    var promptPanel = document.getElementById("promptPanel");
    var promptText = document.getElementById("promptText");
    var promptCopyBtn = document.getElementById("promptCopyBtn");
    var promptClearBtn = document.getElementById("promptClearBtn");

    var aiStatus = document.getElementById("aiStatus");

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

    openGeminiBtn.addEventListener("click", function () {
        openExternal("https://gemini.google.com/");
        setStatus("Đã mở Gemini — dán ảnh (Ctrl+V) rồi nhập prompt.");
    });

    /* ---------- Prompt panel ---------- */
    var PROMPT_STORAGE_KEY = "aiRedrawPanel.savedPrompt";

    // Khôi phục prompt đã lưu lần trước (nếu có)
    try {
        var saved = localStorage.getItem(PROMPT_STORAGE_KEY);
        if (saved) promptText.value = saved;
    } catch (e) {}

    promptToggleBtn.addEventListener("click", function () {
        promptPanel.classList.toggle("hidden");
        if (!promptPanel.classList.contains("hidden")) {
            promptText.focus();
        }
    });

    promptText.addEventListener("input", function () {
        try {
            localStorage.setItem(PROMPT_STORAGE_KEY, promptText.value);
        } catch (e) {}
    });

    promptCopyBtn.addEventListener("click", function () {
        promptText.select();
        try {
            document.execCommand("copy");
            setStatus("Đã copy prompt vào clipboard.");
        } catch (e) {
            setStatus("Không copy được prompt.", true);
        }
    });

    promptClearBtn.addEventListener("click", function () {
        promptText.value = "";
        try {
            localStorage.removeItem(PROMPT_STORAGE_KEY);
        } catch (e) {}
        setStatus("Đã xoá prompt.");
    });
})();
