import { menuItems } from './menuData.js';
// ✅ 選取按鈕區域與互動區塊
const buttonContainer = document.querySelector(".button-container");
const interactionSection = document.querySelector(".chat-options");

let sendButton;

document.addEventListener("DOMContentLoaded", () => {
    sendButton = document.getElementById("send"); // ✅ `DOMContentLoaded` 內部才初始化，確保 HTML 已載入

    // ✅ 確保 `sendButton` 存在後才綁定事件，避免重複綁定
    if (sendButton && !sendButton.hasAttribute("data-listener")) {
        sendButton.addEventListener("click", () => {
            if (!sendButton.disabled) {  // ✅ 確保按鈕沒有被禁用時才允許送出
                const userInput = document.getElementById("user-input").value;
                if (userInput.trim() !== "") {
                    sendToGPT(userInput);
                }
            }
        });
        sendButton.setAttribute("data-listener", "true"); // 標記按鈕已經被綁定
    }

    // ✅ 啟動歡迎訊息
    showWelcomeMessage();
});



// ✅ 生成或讀取 `user_id`（每次開啟瀏覽器時都會產生新的 ID）
function getUserId() {
    let userId = sessionStorage.getItem("user_id");
    if (!userId) {
        userId = "user_" + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem("user_id", userId);
    }
    console.log("✅ 目前的 user_id:", userId);
    return userId;
}
// ✅ AI 歡迎語
function showWelcomeMessage() {
    const chatBox = document.getElementById("gpt-response");
    chatBox.textContent = "🌿 歡迎來到老濟安 Healing Herbar！我是安爺爺，你的 AI 草本茶顧問。為了讓我們一起喝茶的時候，是最適合於你的茶飲，待會請盡量回答我的問題囉！我會推薦適合的茶飲 🍵 給你！🌿 Welcome to Healing Herbar! I’m Grandpa An, your AI herbal tea advisor. To find the perfect tea for you, please answer my questions carefully! 🍵 I’ll recommend the best tea for you!";

    // **✅ 10 秒後自動啟動問卷**
    setTimeout(() => {
        console.log("✅ 嘗試啟動問卷...");
        if (typeof startQuestionnaire === "function") {
            startQuestionnaire();
        } else {
            console.error("❌ `startQuestionnaire` 未定義，請確認 `voiceAssistant.js` 是否正確載入");
        }
    }, 10000);
}

// ✅ 問卷開始
function startQuestionnaire() {
    console.log("✅ 問卷開始");
    buttonContainer.style.display = "flex"; // 顯示問卷按鈕
    askNextQuestion();
}

// ✅ 問卷問題
const questions = [
    { text: "🌿 最近是不是睡不好呢？", key: "睡不好", type: "single", options: ["憂鬱最嚴重", "焦慮", "容易緊張", "無"] },
    { text: "🌿 半夜是不是難以入眠，或是到半夜還在嗨？", key: "半暝還在嗨", type: "single", options: ["22點以前", "22-24點", "24-3點", "3點以後"] },
    { text: "🌿 早上會不會打噴嚏？", key: "早上哈啾", type: "single", options: ["長期有呼吸胸悶", "偶發有呼吸胸悶", "無"] },
    { text: "🌿 皮膚是否容易過敏？", key: "癢癢", type: "single", options: ["長期過敏", "短期過敏", "無"] },
    { text: "🌿 最近胃部是否有不適？（可複選）", key: "胃生氣", type: "multiple", options: ["胃脹氣", "反胃", "胃食道逆流", "無"] },
    { text: "🌿 來大姨媽會不會痛？", key: "厭世生理期", type: "single", options: ["重度疼痛", "輕度疼痛", "不會痛", "無生理期"] },
    { text: "🌿 你能接受有苦味的飲品嗎？", key: "接受苦的程度", type: "single", options: ["可以", "不行"] }
];

// ✅ 問題進度
let userResponses = {};
let currentQuestionIndex = 0;

// ✅ 顯示問題
function askNextQuestion() {
    if (currentQuestionIndex < questions.length) {
        let question = questions[currentQuestionIndex];
        document.getElementById("gpt-response").textContent = question.text;
        buttonContainer.innerHTML = "";

        // 單選題
        if (question.type === "single") {
            question.options.forEach(option => {
                let btn = document.createElement("button");
                btn.textContent = option;
                btn.onclick = function () {
                    userResponses[question.key] = option;
                    currentQuestionIndex++;
                    askNextQuestion();
                };
                buttonContainer.appendChild(btn);
            });

        // 多選題
        } else if (question.type === "multiple") {
            if (!userResponses[question.key]) {
                userResponses[question.key] = [];
            }

            question.options.forEach(option => {
                let btn = document.createElement("button");
                btn.textContent = option;

                btn.onclick = function () {
                    let selectedOptions = userResponses[question.key];
                
                    if (option === "無") {
                        selectedOptions = ["無"];
                    } else {
                        if (selectedOptions.includes("無")) {
                            selectedOptions = [];
                        }
                        if (selectedOptions.includes(option)) {
                            selectedOptions = selectedOptions.filter(item => item !== option);
                        } else {
                            if (selectedOptions.includes("無")) {
                                selectedOptions = [];
                            }
                            selectedOptions.push(option);
                        }
                    }
                
                    userResponses[question.key] = selectedOptions;
                    updateButtonColors();
                };

                buttonContainer.appendChild(btn);
            });

            function updateButtonColors() {
                buttonContainer.querySelectorAll("button").forEach(b => {
                    b.style.backgroundColor = userResponses[question.key].includes(b.textContent) ? "#90ee90" : "";
                });
            }
        }

        // 「下一題」按鈕
        let nextBtn = document.createElement("button");
        nextBtn.textContent = "下一題";
        nextBtn.onclick = function () {
            if (!(question.key in userResponses)) {
                userResponses[question.key] = question.type === "multiple" ? ["無"] : "無";
            }
            currentQuestionIndex++;
            askNextQuestion();
        };
        buttonContainer.appendChild(nextBtn);

        buttonContainer.style.display = "flex";

    } else {
        buttonContainer.style.display = "none";
        sendToAI(userResponses);
    }
}

// ✅ 送問卷資料到 AI
async function sendToAI(userResponses) {
    const userId = getUserId();
    try {
        const response = await fetch("https://healingherbar-site.onrender.com/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, responses: userResponses })
        });

        const data = await response.json();
        if (data.response) {
            document.getElementById("gpt-response").textContent = `${data.response}`;
        } else {
            document.getElementById("gpt-response").textContent = "❌ 無法獲取 AI 回應，請稍後再試。";
        }
        unlockChatInteraction();
    } catch (error) {
        console.error("❌ 問卷送出失敗:", error);
    }
}

// ✅ 啟動下半部 AI 互動區
function unlockChatInteraction() {
    interactionSection.style.display = "block"; // 讓下半部互動區顯示
}

// ✅ 使用者輸入 GPT
async function sendToGPT(userInput) {
    const userId = getUserId();
    if (!sendButton) sendButton = document.getElementById("send");
    // ✅ 禁用送出按鈕，防止連點
    sendButton.disabled = true;
    sendButton.textContent = "請稍候..."; // 改變按鈕文字，提示使用者

    try {
        const response = await fetch("https://healingherbar-site.onrender.com/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, message: userInput })
        });

        const data = await response.json();
        console.log("✅ 送出的 Prompt：", data.prompt);

        if (data.response) {
            document.getElementById("gpt-response").textContent = `${data.response}`;
        } else {
            document.getElementById("gpt-response").textContent = "❌ 無法獲取 AI 回應，請稍後再試。";
        }
    } catch (error) {
        console.error("❌ 伺服器請求失敗", error);
        document.getElementById("gpt-response").textContent = "❌ 伺服器異常，請稍後再試。";
    }

    // ✅ 當 AI 回應後，重新啟用送出按鈕
    sendButton.disabled = false;
    sendButton.textContent = "送出"; // 恢復原本的按鈕文字
}


// ✅ 啟動問卷與歡迎語
document.addEventListener("DOMContentLoaded", showWelcomeMessage);

function handleUserInput(userMessage) {
    sendToGPT(userMessage);
}