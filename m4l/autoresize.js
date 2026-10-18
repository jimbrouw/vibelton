/**
 * autoresize.js - Dynamically keeps jweb sized to 100% of the Max subpatcher window.
 */
var p = this.patcher;

function init() {
    if (p && p.wind) {
        p.wind.onresize = onresize;
        updateSize();
    }
}

function onresize(w, h) {
    updateSize();
}

function updateSize() {
    if (!p || !p.wind) return;
    try {
        var s = p.wind.size;
        if (s && s.length >= 2) {
            var w = s[0];
            var h = s[1];
            var jw = p.getnamed("popout_jweb");
            if (jw) {
                // The window opens in presentation mode, so size both rects.
                jw.rect = [0, 0, w, h];
                jw.presentation_rect = [0, 0, w, h];
            }
        }
    } catch (e) {}
}

function bang() {
    init();
}

function loadbang() {
    init();
}

function front() {
    init();
}
