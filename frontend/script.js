const API_URL = "http://127.0.0.1:8000";

// =====================================
// ELEMENTS
// =====================================

const questionInput = document.getElementById("questionInput");

const sendButton = document.getElementById("sendButton");

const clearButton = document.getElementById("clearButton");

const chatContainer = document.getElementById("chatContainer");

const uploadButton = document.getElementById("uploadButton");

const pdfInput = document.getElementById("pdfInput");

const documentStatus = document.getElementById("documentStatus");

const documentName = document.getElementById("documentName");

const documentMessage = document.getElementById("documentMessage");

// =====================================
// ADD MESSAGE
// =====================================

function addMessage(message, type) {
  const messageDiv = document.createElement("div");

  messageDiv.className = `message ${type}`;

  const bubble = document.createElement("div");

  bubble.className = "bubble";

  if (type === "ai") {
    const markdownHTML = marked.parse(message);

    bubble.innerHTML = DOMPurify.sanitize(markdownHTML);
  } else {
    bubble.textContent = message;
  }

  messageDiv.appendChild(bubble);

  chatContainer.appendChild(messageDiv);

  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// =====================================
// LOADING MESSAGE
// =====================================

function addLoadingMessage() {
  const messageDiv = document.createElement("div");

  messageDiv.className = "message ai";

  messageDiv.id = "loadingMessage";

  messageDiv.innerHTML = `
        <div class="bubble">
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

  chatContainer.appendChild(messageDiv);

  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// =====================================
// REMOVE LOADING
// =====================================

function removeLoadingMessage() {
  const loadingMessage = document.getElementById("loadingMessage");

  if (loadingMessage) {
    loadingMessage.remove();
  }
}

// =====================================
// HIDE WELCOME
// =====================================

function hideWelcome() {
  const welcome = document.querySelector(".welcome");

  if (welcome) {
    welcome.remove();
  }
}

// =====================================
// SHOW DOCUMENT STATUS
// =====================================

function showDocumentStatus(filename, message) {
  documentStatus.classList.remove("hidden");

  documentName.textContent = filename;

  documentMessage.textContent = message;
}

// =====================================
// UPLOAD PDF
// =====================================

async function uploadPDF(file) {
  if (!file) {
    return;
  }

  // Check PDF

  if (
    file.type !== "application/pdf" &&
    !file.name.toLowerCase().endsWith(".pdf")
  ) {
    alert("Please select a PDF file.");

    pdfInput.value = "";

    return;
  }

  // Disable buttons

  uploadButton.disabled = true;

  sendButton.disabled = true;

  // Show processing

  showDocumentStatus(file.name, "Processing PDF...");

  documentStatus.classList.add("uploading");

  // Create form data

  const formData = new FormData();

  formData.append("file", file);

  try {
    const response = await fetch(`${API_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    const data = await response.json();

    console.log("Upload response:", data);

    if (!data.success) {
      throw new Error(data.message || "PDF processing failed.");
    }

    // ==========================
    // SUCCESS
    // ==========================

    documentStatus.classList.remove("uploading");

    showDocumentStatus(
      data.filename,
      `✓ Document ready • ${data.chunks} chunks`,
    );

    // Remove old chat messages

    const messages = chatContainer.querySelectorAll(".message");

    messages.forEach((message) => message.remove());

    // Replace welcome text

    const welcome = document.querySelector(".welcome");

    if (welcome) {
      welcome.innerHTML = `

                <div class="welcome-icon">
                    🤖
                </div>

                <h2>
                    Document Ready! 📄
                </h2>

                <p>
                    I've processed
                    <strong>${data.filename}</strong>.
                    Ask me anything about this document.
                </p>

            `;
    }
  } catch (error) {
    console.error("Upload error:", error);

    documentStatus.classList.remove("uploading");

    showDocumentStatus(file.name, "❌ Upload failed");

    alert(
      "Could not process the PDF. " + "Please make sure FastAPI is running.",
    );
  } finally {
    uploadButton.disabled = false;

    sendButton.disabled = false;

    pdfInput.value = "";
  }
}

// =====================================
// ASK QUESTION
// =====================================

async function askQuestion() {
  const question = questionInput.value.trim();

  if (!question) {
    return;
  }

  hideWelcome();

  addMessage(question, "user");

  questionInput.value = "";

  sendButton.disabled = true;

  addLoadingMessage();

  try {
    const response = await fetch(`${API_URL}/ask`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        question: question,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    removeLoadingMessage();

    addMessage(data.answer, "ai");
  } catch (error) {
    console.error(error);

    removeLoadingMessage();

    addMessage(
      "Sorry, I couldn't connect to the AI server. Please make sure FastAPI is running.",
      "ai",
    );
  } finally {
    sendButton.disabled = false;

    questionInput.focus();
  }
}

// =====================================
// CLEAR CHAT
// =====================================

function clearChat() {
  const documentWasUploaded = !documentStatus.classList.contains("hidden");

  chatContainer.innerHTML = "";

  // Put document status back

  if (documentWasUploaded) {
    chatContainer.appendChild(documentStatus);
  }

  // Create welcome

  const welcome = document.createElement("div");

  welcome.className = "welcome";

  if (documentWasUploaded) {
    welcome.innerHTML = `

            <div class="welcome-icon">
                🤖
            </div>

            <h2>
                Ready! 👋
            </h2>

            <p>
                Ask me anything about
                your uploaded document.
            </p>

        `;
  } else {
    welcome.innerHTML = `

            <div class="welcome-icon">
                🤖
            </div>

            <h2>
                Welcome! 👋
            </h2>

            <p>
                Upload a PDF and ask me
                anything about your document.
            </p>

        `;
  }

  chatContainer.appendChild(welcome);

  questionInput.focus();
}

// =====================================
// EVENT LISTENERS
// =====================================

// Upload button

uploadButton.addEventListener("click", () => {
  pdfInput.click();
});

// PDF selected

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files[0];

  uploadPDF(file);
});

// Send question

sendButton.addEventListener("click", askQuestion);

// Clear

clearButton.addEventListener("click", clearChat);

// Enter

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();

    askQuestion();
  }
});
