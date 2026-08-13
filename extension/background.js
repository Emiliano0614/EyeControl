let socket;

function connectWebSocket() {
  socket = new WebSocket("ws://localhost:8765");

  socket.onopen = () => {
    console.log("Connected to EyeControl server");
  };

  socket.onmessage = (event) => {
  const data = JSON.parse(event.data);

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
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