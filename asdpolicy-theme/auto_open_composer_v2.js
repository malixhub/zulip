/*
 * ASDPolicy composer v2: only auto-open inside a specific channel topic
 * or a dedicated direct-message conversation. Do not open a channel picker
 * when browsing Inbox, Combined feed, search, or the channel list.
 */
(() => {
    "use strict";
    let scheduled = false;
    let lastAttempt = 0;

    function eligible() {
        const hash = decodeURIComponent(window.location.hash || "");
        return /\/topic\//.test(hash) || /#narrow\/(?:dm|pm-with|pm)\//.test(hash);
    }

    function reopen() {
        scheduled = false;
        if (!eligible()) {
            return;
        }
        const composer = document.getElementById("compose");
        if (!composer || composer.classList.contains("compose-box-open")) {
            return;
        }
        const reply = document.getElementById("left_bar_compose_reply_button_big");
        if (!reply || reply.disabled || reply.getClientRects().length === 0) {
            return;
        }
        if (Date.now() - lastAttempt < 1500) {
            return;
        }
        lastAttempt = Date.now();
        reply.click();
        if (document.activeElement?.matches(".new_message_textarea")) {
            document.activeElement.blur();
        }
    }

    function schedule() {
        if (scheduled) return;
        scheduled = true;
        window.setTimeout(reopen, 250);
    }

    const observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class"],
    });
    window.addEventListener("hashchange", schedule);
    window.addEventListener("load", schedule);
    schedule();
})();
