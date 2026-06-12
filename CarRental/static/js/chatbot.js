const chatToggleBtn    = document.getElementById("chatToggleBtn");
const chatbotContainer = document.getElementById("chatbotContainer");
const closeChatbot     = document.getElementById("closeChatbot");
const chatBody         = document.getElementById("chatBody");
const userInput        = document.getElementById("userInput");

chatToggleBtn.onclick = () => { chatbotContainer.style.display = "flex"; scrollToBottom(); };
closeChatbot.onclick  = () => { chatbotContainer.style.display = "none"; };

userInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}

function scrollToBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
}

// role: "user" | "bot"  |  html: true renders innerHTML (bot only)
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

    appendMessage("user", message);
    userInput.value = "";

    // Animated typing indicator
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
        botDiv.querySelector("p").textContent = "⚠️ Could not connect. Please try again.";
    }

    scrollToBottom();
}

function sendSuggestion(text) {
    userInput.value = text;
    sendMessage();
}
