const chatToggleBtn     = document.getElementById("chatToggleBtn");
const chatbotContainer  = document.getElementById("chatbotContainer");
const closeChatbot      = document.getElementById("closeChatbot");
const chatBody          = document.getElementById("chatBody");
const userInput         = document.getElementById("userInput");
const sendBtn           = document.getElementById("sendBtn");
const suggestionsToggle = document.getElementById("suggestionsToggle");
const suggestionsPanel  = document.getElementById("suggestionsPanel");
const closeSuggestions  = document.getElementById("closeSuggestions");

chatToggleBtn.addEventListener("click", () => {
    chatbotContainer.classList.add("open");
    scrollToBottom();
    userInput.focus();
});

closeChatbot.addEventListener("click", () => {
    chatbotContainer.classList.remove("open");
    closeSuggestionsPanel();
});

suggestionsToggle.addEventListener("click", () => {
    if (suggestionsPanel.classList.contains("open")) {
        closeSuggestionsPanel();
    } else {
        openSuggestionsPanel();
    }
});

closeSuggestions.addEventListener("click", closeSuggestionsPanel);

function openSuggestionsPanel() {
    suggestionsPanel.classList.add("open");
    suggestionsToggle.classList.add("active");
}

function closeSuggestionsPanel() {
    suggestionsPanel.classList.remove("open");
    suggestionsToggle.classList.remove("active");
}

userInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) sendMessage();
});

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatBody.scrollTop = chatBody.scrollHeight;
    });
}

function appendMessage(role, content, html = false) {
    const div = document.createElement("div");
    div.classList.add(role === "user" ? "user-message" : "bot-message");
    const p = document.createElement("p");
    if (html) {
        p.innerHTML = content;
    } else {
        p.textContent = content;
    }
    div.appendChild(p);
    chatBody.appendChild(div);
    scrollToBottom();
    return div;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    closeSuggestionsPanel();
    appendMessage("user", message);
    userInput.value = "";

    userInput.disabled = true;
    sendBtn.disabled = true;

    const botDiv = appendMessage(
        "bot",
        '<span class="typing-dots"><span></span><span></span><span></span></span>',
        true
    );

    try {
        const res = await fetch("/chatbot/query/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({ message }),
        });
        const data = await res.json();
        botDiv.querySelector("p").innerHTML = data.reply;
    } catch {
        botDiv.querySelector("p").innerHTML =
            '<span style="color:#ef4444"><i class="ri-error-warning-line"></i> Could not connect. Please try again.</span>';
    }

    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
    scrollToBottom();
}

function sendSuggestion(text) {
    closeSuggestionsPanel();
    userInput.value = text;
    sendMessage();
}
