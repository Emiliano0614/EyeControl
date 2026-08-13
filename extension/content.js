let previousTypedInput = null;
let previousMode = null;
let linkMap = {};
let links = [];
let badges = [];

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { mode, path, typed_input } = message;

  if (mode === "SELECT" && previousMode !== "SELECT") {
    // clear out old badges before creating new ones
    badges.forEach((badge) => {
      badge.remove();
    });
    badges = [];

    linkMap = {};
    links = document.querySelectorAll("a");

    let visibleCount = 0; // only increments for links that pass the visibility check

    links.forEach((link) => {
      const rect = link.getBoundingClientRect();

      if (rect.top >= 0 && rect.bottom <= window.innerHeight) {
        visibleCount++;
        const number = String(visibleCount);

        linkMap[number] = link;

        const badge = document.createElement("div");
        badge.textContent = number;

        badge.style.position = "fixed";
        badge.style.top = rect.top + "px";
        badge.style.left = rect.left + "px";
        badge.style.backgroundColor = "red";
        badge.style.color = "white";
        badge.style.fontSize = "12px";
        badge.style.padding = "1px 4px";
        badge.style.zIndex = "999999";

        document.body.appendChild(badge);
        badges.push(badge);
      }
    });
  }
  previousMode = mode;

  if (path.length === 0 && typed_input === previousTypedInput && previousTypedInput !== null) {
    console.log("ENTER confirmed! Final value:", typed_input);
    const targetLink = linkMap[typed_input];
    if (targetLink) {
      targetLink.click();
    } else {
      console.log("No link found for:", typed_input);
    }
  }

  previousTypedInput = typed_input;
});