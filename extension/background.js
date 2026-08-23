let socket;

function connectWebSocket() {
  socket = new WebSocket("ws://localhost:8765");

  socket.onopen = () => {
    console.log("Connected to EyeControl server");
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // CHANGED: was { active: true, currentWindow: true }, which only
    // matches a Chrome window that currently has OS-level focus. Since
    // the normal EyeControl workflow means the tkinter drill tree/
    // cursor window has focus while tilting (not Chrome), this query
    // was returning an empty tabs[] array most of the time, causing
    // tabs[0].id below to throw and silently killing message delivery.
    // lastFocusedWindow finds the last Chrome window that WAS focused,
    // even if OS focus is currently elsewhere.
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      // ADDED: guard so a genuine no-tab-found case fails quietly
      // instead of crashing the service worker with a TypeError.
      if (!tabs[0]) {
        console.log("No active Chrome tab found");
        return;
      }
      const tabId = tabs[0].id;
      chrome.tabs.sendMessage(tabId, data);
    });
  };

  socket.onclose = () => {
    console.log("Disconnected — retrying in 3s...");
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

connectWebSocket(); // kick off the first connection