let previousTypedInput = null;
let linkMap = {};
let links = [];
let badges = [];
let scanTimeout = null;

function scanAndNumberLinks() {
  badges.forEach((badge) => {
    badge.remove();
  });
  badges = [];

  linkMap = {};
  links = document.querySelectorAll("a");

  let visibleCount = 0;

  links.forEach((link) => {
    const rect = link.getBoundingClientRect();

    // Must be positioned within the viewport on BOTH axes, have real
    // size (filters out 0x0 hidden anchor tags), and not be hidden via
    // CSS (offsetParent is null for display:none / detached elements).
    const inViewport =
      rect.top >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.left >= 0 &&
      rect.right <= window.innerWidth;

    const hasSize = rect.width > 0 && rect.height > 0;
    const isVisible = link.offsetParent !== null;

    if (inViewport && hasSize && isVisible) {
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

function clearBadges() {
  badges.forEach((badge) => {
    badge.remove();
  });
  badges = [];
}

// Run once, immediately, when content.js is injected into the page.
scanAndNumberLinks();

// Re-scan on scroll, debounced.
window.addEventListener("scroll", () => {
  clearTimeout(scanTimeout);
  scanTimeout = setTimeout(scanAndNumberLinks, 150);
});

// Hide badges while in real fullscreen (video playback etc.), and
// rescan once fullscreen is exited.
document.addEventListener("fullscreenchange", () => {
  if (document.fullscreenElement) {
    clearBadges();
  } else {
    scanAndNumberLinks();
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { path, typed_input } = message;

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