/*
 * ASDPolicy: keep Zulip's real composer open by clicking its own Reply control.
 * Load this after Zulip has initialized, not as an inline script.
 * Uses Zulip's actual click handler, rather than faking an editable text field.
 * Intended only for the customized production web client.
 */
(() => {
    "use strict";
    let scheduled = false;
    let lastAttempt = 0;

    function reopen() {
        scheduled = false;
        const composer = document.getElementById("compose");
        if (!composer || composer.classList.contains("compose-box-open")) {
            return;
        }
        // Only attempt to reply when Zulip has an actual message selection.
        // The built-in button determines the correct channel/topic/recipient.
        const reply = document.getElementById("left_bar_compose_reply_button_big");
        if (!reply || reply.disabled || reply.getClientRects().length === 0) {
            return;
        }
        if (Date.now() - lastAttempt < 1200) {
            return;
        }
        lastAttempt = Date.now();
        reply.click();
        // Don't steal keyboard focus from navigation after auto-opening.
        if (document.activeElement && document.activeElement.matches(".new_message_textarea")) {
            document.activeElement.blur();
        }
    }

    function schedule() {
        if (scheduled) {
            return;
        }
        scheduled = true;
        window.setTimeout(reopen, 180);
    }

    // Zulip constructs the composer asynchronously and replaces portions of
    // the message view during navigation.
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
