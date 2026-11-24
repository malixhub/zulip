/*
 * ASDPolicy navigation experiment.
 * Move Recent conversations to first position and Inbox to last.
 * Keep Inbox working, but display its label struck through.
 * Designed for Zulip 13.x's #left-sidebar-navigation-list.
 */
(() => {
    "use strict";
    let pending = false;

    function reorder() {
        pending = false;
        const list = document.getElementById("left-sidebar-navigation-list");
        if (!list) return;
        const items = Array.from(list.children).filter((node) => node.matches("li.top_left_row"));
        const find = (name, className) => items.find((item) => {
            const href = item.querySelector("a[href]")?.getAttribute("href") || "";
            const label = item.querySelector(".left-sidebar-navigation-label")?.textContent?.trim().toLowerCase() || "";
            return item.classList.contains(className) || label === name || href === "#" + name.replaceAll(" ", "_");
        });
        const recent = find("recent conversations", "top_left_recent");
        const inbox = find("inbox", "top_left_inbox");
        if (recent && list.firstElementChild !== recent) list.insertBefore(recent, list.firstElementChild);
        if (inbox) {
            inbox.classList.add("asdpolicy-retired-inbox");
            if (list.lastElementChild !== inbox) list.append(inbox);
        }
    }

    function schedule() {
        if (pending) return;
        pending = true;
        window.requestAnimationFrame(reorder);
    }

    const observer = new MutationObserver(schedule);
    observer.observe(document.documentElement, {childList: true, subtree: true});
    window.addEventListener("load", schedule);
    schedule();
})();
