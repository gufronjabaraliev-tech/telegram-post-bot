// State
let tg = window.Telegram?.WebApp;
let currentUser = {
  id: 1001,
  first_name: "Foydalanuvchi"
};

let uploadedImages = []; // Array of { filename, original_name, url }
let selectedEmojis = ["👍", "❤️", "🔥"];
let customButtons = [];
let savedChannels = [];
let userTemplates = [];

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe?.user) {
      currentUser = tg.initDataUnsafe.user;
    }
  }

  // Set user badge
  const userBadge = document.getElementById("user-badge");
  if (userBadge) {
    userBadge.innerText = currentUser.first_name || `ID: ${currentUser.id}`;
  }

  // Set minimum schedule time to now + 5 mins
  const scheduleInput = document.getElementById("schedule-datetime");
  if (scheduleInput) {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5);
    const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    scheduleInput.min = localIso;
    scheduleInput.value = localIso;
  }

  // Load saved channels, scheduled posts & templates
  loadSavedChannels();
  loadScheduledPosts();
  loadTemplates();

  // Initial preview
  updatePreview();
});

// Authentication Headers for Telegram Mini App API Security
function getAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (window.Telegram?.WebApp?.initData) {
    headers["X-Telegram-Init-Data"] = window.Telegram.WebApp.initData;
  }
  return headers;
}

// Toast notifier
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.style.background = isError ? "rgba(239, 68, 68, 0.95)" : "rgba(16, 185, 129, 0.95)";
  toast.style.display = "block";
  if (tg?.HapticFeedback) {
    tg.HapticFeedback.notificationOccurred(isError ? "error" : "success");
  }
  setTimeout(() => {
    toast.style.display = "none";
  }, 3500);
}

// Native Telegram Channel / Group Picker
function openTelegramChannelPicker(type) {
  const url = (type === 'channel')
    ? "https://t.me/Almuraadmin_bot?startchannel=admin&admin=post_messages+edit_messages+delete_messages"
    : "https://t.me/Almuraadmin_bot?startgroup=admin&admin=post_messages+delete_messages";
  
  if (tg?.openTelegramLink) {
    tg.openTelegramLink(url);
  } else {
    window.open(url, "_blank");
  }

  showToast("Kanalni tanlab admin qilganingizdan so'ng, ro'yxat avtomatik yangilanadi!");
  // Poll saved channels after returning
  setTimeout(loadSavedChannels, 3000);
  setTimeout(loadSavedChannels, 7000);
}

// Tab Switching
function switchTab(tab) {
  const editorView = document.getElementById("view-editor");
  const templatesView = document.getElementById("view-templates");
  const scheduledView = document.getElementById("view-scheduled");

  const editorBtn = document.getElementById("tab-editor-btn");
  const templatesBtn = document.getElementById("tab-templates-btn");
  const scheduledBtn = document.getElementById("tab-scheduled-btn");

  editorView.style.display = (tab === "editor") ? "block" : "none";
  templatesView.style.display = (tab === "templates") ? "block" : "none";
  scheduledView.style.display = (tab === "scheduled") ? "block" : "none";

  editorBtn.classList.toggle("active", tab === "editor");
  templatesBtn.classList.toggle("active", tab === "templates");
  scheduledBtn.classList.toggle("active", tab === "scheduled");

  if (tab === "scheduled") {
    loadScheduledPosts();
  } else if (tab === "templates") {
    loadTemplates();
  }
}

// Saved Channels
async function loadSavedChannels() {
  try {
    const res = await fetch(`/api/channels?user_id=${currentUser.id}`);
    const data = await res.json();
    if (data.ok && data.channels?.length > 0) {
      savedChannels = data.channels;
      const group = document.getElementById("saved-channels-group");
      const select = document.getElementById("saved-channels-select");
      select.innerHTML = '<option value="">-- Saqlangan kanallardan tanlash --</option>';
      savedChannels.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.channel_id;
        opt.innerText = c.title ? `${c.title} (${c.channel_id})` : c.channel_id;
        select.appendChild(opt);
      });
      group.style.display = "flex";

      // If input is empty, prefill first
      const input = document.getElementById("channel-input");
      if (!input.value && savedChannels.length > 0) {
        input.value = savedChannels[0].channel_id;
        updatePreview();
      }
    }
  } catch (e) {
    console.error("Channels load error:", e);
  }
}

function onSelectSavedChannel() {
  const select = document.getElementById("saved-channels-select");
  const input = document.getElementById("channel-input");
  if (select.value) {
    input.value = select.value;
    updatePreview();
  }
}

// Verify Channel Admin status
async function verifyChannel() {
  const channel = document.getElementById("channel-input").value.trim();
  const statusBadge = document.getElementById("channel-status");
  if (!channel) {
    showToast("Iltimos, kanal username'ini kiriting!", true);
    return;
  }

  statusBadge.style.display = "inline-block";
  statusBadge.innerText = "Tekshirilmoqda...";
  statusBadge.style.background = "rgba(245, 158, 11, 0.2)";
  statusBadge.style.color = "var(--warning-color)";

  try {
    const res = await fetch("/api/verify-channel", {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ user_id: currentUser.id, channel_id: channel })
    });
    const data = await res.json();
    if (data.ok) {
      statusBadge.innerText = "✅ Bot Admin!";
      statusBadge.style.background = "rgba(16, 185, 129, 0.2)";
      statusBadge.style.color = "var(--success-color)";
      showToast("Kanal tekshirildi va saqlandi!");
      loadSavedChannels();
    } else {
      statusBadge.innerText = "❌ Xatolik";
      statusBadge.style.background = "rgba(239, 68, 68, 0.2)";
      statusBadge.style.color = "var(--danger-color)";
      showToast(data.description || "Bot bu kanalda admin emas!", true);
    }
  } catch (e) {
    statusBadge.innerText = "❌ Aloqa xatosi";
    showToast("Server bilan aloqa uzildi", true);
  }
  updatePreview();
}

// 1-10 File Upload Handling
async function handleFileSelect(event) {
  const files = Array.from(event.target.files);
  if (!files.length) return;

  if (uploadedImages.length + files.length > 10) {
    showToast(`Maksimal 10 ta rasm yuklash mumkin! Hozir: ${uploadedImages.length}`, true);
    return;
  }

  const formData = new FormData();
  files.forEach(f => formData.append("files", f));

  showToast("Rasmlar yuklanmoqda...");
  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.ok) {
      uploadedImages.push(...data.files);
      renderImages();
      updatePreview();
      showToast(`${data.files.length} ta rasm yuklandi!`);
    } else {
      showToast(data.detail || "Yuklashda xatolik", true);
    }
  } catch (e) {
    showToast("Rasmlarni yuklab bo'lmadi", true);
  }

  event.target.value = "";
}

function removeImage(index) {
  uploadedImages.splice(index, 1);
  renderImages();
  updatePreview();
}

function renderImages() {
  const grid = document.getElementById("image-grid");
  const badge = document.getElementById("image-count-badge");
  const limitSpan = document.getElementById("char-limit");
  const typeBadge = document.getElementById("caption-type-badge");

  badge.innerText = `${uploadedImages.length} / 10 ta rasm`;
  grid.innerHTML = "";

  if (uploadedImages.length > 0) {
    limitSpan.innerText = "1024";
    typeBadge.innerText = uploadedImages.length > 1 ? "Albom post" : "Rasmli post";
  } else {
    limitSpan.innerText = "4096";
    typeBadge.innerText = "Faqat matn";
  }

  uploadedImages.forEach((img, idx) => {
    const thumb = document.createElement("div");
    thumb.className = "img-thumb";
    thumb.innerHTML = `
      <img src="${img.url}" alt="Rasm ${idx + 1}">
      <span class="index-badge">#${idx + 1}</span>
      <button type="button" class="del-btn" onclick="removeImage(${idx})">×</button>
    `;
    grid.appendChild(thumb);
  });
}

// Text Formatting
function applyFormat(tag) {
  const textarea = document.getElementById("post-text");
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;

  const selected = text.substring(start, end);
  const openTag = `<${tag}>`;
  const closeTag = `</${tag}>`;

  if (selected) {
    textarea.value = text.substring(0, start) + openTag + selected + closeTag + text.substring(end);
    textarea.selectionStart = start + openTag.length;
    textarea.selectionEnd = end + openTag.length;
  } else {
    textarea.value = text.substring(0, start) + openTag + closeTag + text.substring(end);
    textarea.selectionStart = textarea.selectionEnd = start + openTag.length;
  }
  textarea.focus();
  updatePreview();
}

function addLinkPrompt() {
  const url = prompt("Havola (URL) manzilini kiriting:", "https://");
  if (!url) return;
  const textarea = document.getElementById("post-text");
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;
  const selected = text.substring(start, end) || "Havola matni";

  const formatted = `<a href="${url}">${selected}</a>`;
  textarea.value = text.substring(0, start) + formatted + text.substring(end);
  textarea.focus();
  updatePreview();
}

// Komplektatsiyalar toggles
function toggleReactionsBox() {
  const checked = document.getElementById("toggle-reactions").checked;
  const box = document.getElementById("reactions-box");
  box.className = checked ? "sub-config-box open" : "sub-config-box";
  updatePreview();
}

function toggleSubBox(id, checked) {
  const box = document.getElementById(id);
  box.className = checked ? "sub-config-box open" : "sub-config-box";
  updatePreview();
}

function toggleEmojiChip(element, emoji) {
  const index = selectedEmojis.indexOf(emoji);
  if (index > -1) {
    if (selectedEmojis.length === 1) {
      showToast("Kamida bitta emoji qolishi kerak!", true);
      return;
    }
    selectedEmojis.splice(index, 1);
    element.classList.remove("selected");
  } else {
    selectedEmojis.push(emoji);
    element.classList.add("selected");
  }
  updatePreview();
}

// Custom Buttons
function addCustomButtonRow() {
  customButtons.push({ text: "Saytga o'tish", url: "https://" });
  renderCustomButtons();
  updatePreview();
}

function removeCustomButton(index) {
  customButtons.splice(index, 1);
  renderCustomButtons();
  updatePreview();
}

function updateCustomButton(index, field, value) {
  if (customButtons[index]) {
    customButtons[index][field] = value;
    updatePreview();
  }
}

function renderCustomButtons() {
  const list = document.getElementById("custom-buttons-list");
  list.innerHTML = "";
  customButtons.forEach((btn, idx) => {
    const row = document.createElement("div");
    row.className = "custom-btn-item";
    row.innerHTML = `
      <input type="text" class="text-input" placeholder="Tugma matni" value="${btn.text}" oninput="updateCustomButton(${idx}, 'text', this.value)">
      <input type="text" class="text-input" placeholder="URL" value="${btn.url}" oninput="updateCustomButton(${idx}, 'url', this.value)">
      <button type="button" class="btn-small-del" onclick="removeCustomButton(${idx})">×</button>
    `;
    list.appendChild(row);
  });
}

// Publish Mode Toggle
function togglePublishMode() {
  const mode = document.querySelector('input[name="publish_mode"]:checked').value;
  const schedBox = document.getElementById("schedule-inputs");
  const submitText = document.getElementById("btn-submit-text");
  const submitIcon = document.getElementById("btn-submit-icon");

  if (mode === "schedule") {
    schedBox.style.display = "block";
    submitText.innerText = "Vaqtga rejalashtirish";
    submitIcon.innerText = "⏰";
  } else {
    schedBox.style.display = "none";
    submitText.innerText = "Kanalga joylash";
    submitIcon.innerText = "🚀";
  }
}

// Live Preview Updater
function updatePreview() {
  const channel = document.getElementById("channel-input").value.trim() || "@kanal_nomi";
  const rawText = document.getElementById("post-text").value;
  const prevChannel = document.getElementById("prev-channel-name");
  const prevMediaBox = document.getElementById("prev-media-box");
  const prevTextBox = document.getElementById("prev-text-box");
  const prevKbBox = document.getElementById("prev-buttons-box");
  const charCount = document.getElementById("char-count");

  charCount.innerText = rawText.length;
  prevChannel.innerText = channel;

  // Media preview
  if (uploadedImages.length === 0) {
    prevMediaBox.style.display = "none";
    prevMediaBox.innerHTML = "";
  } else if (uploadedImages.length === 1) {
    prevMediaBox.style.display = "block";
    prevMediaBox.innerHTML = `<img src="${uploadedImages[0].url}" alt="Rasm">`;
  } else {
    prevMediaBox.style.display = "block";
    const previewCount = Math.min(uploadedImages.length, 4);
    let gridHtml = `<div class="preview-media-grid">`;
    for (let i = 0; i < previewCount; i++) {
      gridHtml += `<img src="${uploadedImages[i].url}" alt="Rasm ${i+1}" style="height: 110px; width:100%; object-fit: cover;">`;
    }
    gridHtml += `</div>`;
    if (uploadedImages.length > 4) {
      gridHtml += `<div style="font-size:11px; text-align:center; padding:4px; color:var(--hint-color);">+ yana ${uploadedImages.length - 4} ta rasm (Albom galereyasi)</div>`;
    }
    prevMediaBox.innerHTML = gridHtml;
  }

  // Text preview
  prevTextBox.innerHTML = rawText.trim() ? rawText.replace(/\n/g, "<br>") : "<i>Post matni bu yerda ko'rinadi...</i>";

  // Inline Buttons Preview
  prevKbBox.innerHTML = "";

  // 1. Reactions row
  const reactionsEnabled = document.getElementById("toggle-reactions").checked;
  if (reactionsEnabled && selectedEmojis.length > 0) {
    const row = document.createElement("div");
    row.className = "preview-kb-row";
    selectedEmojis.forEach(emoji => {
      row.innerHTML += `<div class="preview-kb-btn">${emoji} 0</div>`;
    });
    prevKbBox.appendChild(row);
  }

  // 2. Share & Comment row
  const shareEnabled = document.getElementById("toggle-share").checked;
  const commentEnabled = document.getElementById("toggle-comments").checked;

  if (shareEnabled || commentEnabled) {
    const row = document.createElement("div");
    row.className = "preview-kb-row";
    if (shareEnabled) {
      const shareTitle = document.getElementById("share-btn-text").value || "↗️ Ulashish";
      row.innerHTML += `<div class="preview-kb-btn">${shareTitle}</div>`;
    }
    if (commentEnabled) {
      const commentTitle = document.getElementById("comment-btn-text").value || "💬 Izohlar";
      row.innerHTML += `<div class="preview-kb-btn">${commentTitle}</div>`;
    }
    prevKbBox.appendChild(row);
  }

  // 3. Custom buttons
  const customEnabled = document.getElementById("toggle-custom-btn").checked;
  if (customEnabled) {
    customButtons.forEach(btn => {
      if (btn.text) {
        const row = document.createElement("div");
        row.className = "preview-kb-row";
        row.innerHTML = `<div class="preview-kb-btn">🔗 ${btn.text}</div>`;
        prevKbBox.appendChild(row);
      }
    });
  }
}

// Submit Post (Publish now or Schedule)
async function submitPost() {
  const channel = document.getElementById("channel-input").value.trim();
  const text = document.getElementById("post-text").value.trim();
  const publishMode = document.querySelector('input[name="publish_mode"]:checked').value;
  const pinPost = document.getElementById("toggle-pin").checked;
  const silent = document.getElementById("toggle-silent").checked;

  if (!channel) {
    showToast("Kanal nomini (@kanal_nomi) kiriting!", true);
    return;
  }

  if (!text && uploadedImages.length === 0) {
    showToast("Post uchun matn yoki rasm kiriting!", true);
    return;
  }

  const maxLimit = uploadedImages.length > 0 ? 1024 : 4096;
  if (text.length > maxLimit) {
    showToast(`Matn uzunligi ${maxLimit} belgidan oshmasligi kerak!`, true);
    return;
  }

  let scheduledAt = null;
  if (publishMode === "schedule") {
    const schedVal = document.getElementById("schedule-datetime").value;
    if (!schedVal) {
      showToast("Rejalashtirish vaqtini tanlang!", true);
      return;
    }
    scheduledAt = new Date(schedVal).toISOString();
  }

  const buttonsConfig = {};
  if (document.getElementById("toggle-reactions").checked && selectedEmojis.length > 0) {
    buttonsConfig.reactions = selectedEmojis.map(e => ({ emoji: e }));
  }

  if (document.getElementById("toggle-share").checked) {
    const shareText = document.getElementById("share-custom-text").value;
    const shareUrl = channel.startsWith("@") ? `https://t.me/${channel.replace("@", "")}` : "";
    buttonsConfig.share = {
      enabled: true,
      text: document.getElementById("share-btn-text").value || "↗️ Ulashish",
      url: shareUrl,
      share_text: shareText
    };
  }

  if (document.getElementById("toggle-comments").checked) {
    const cUrl = document.getElementById("comment-url").value.trim();
    buttonsConfig.comments = {
      enabled: true,
      text: document.getElementById("comment-btn-text").value || "💬 Izohlar",
      url: cUrl
    };
  }

  if (document.getElementById("toggle-custom-btn").checked && customButtons.length > 0) {
    buttonsConfig.custom_buttons = customButtons.filter(b => b.text && b.url);
  }

  const payload = {
    user_id: currentUser.id,
    target_channel: channel,
    text: text,
    images: uploadedImages.map(img => img.filename),
    buttons_config: buttonsConfig,
    scheduled_at: scheduledAt,
    pin_post: pinPost,
    silent: silent,
    send_now: (publishMode === "now")
  };

  const btn = document.getElementById("btn-submit");
  btn.disabled = true;
  btn.style.opacity = "0.7";
  showToast("Yuborilmoqda...");

  try {
    const res = await fetch("/api/posts/create", {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    btn.disabled = false;
    btn.style.opacity = "1";

    if (data.ok) {
      showToast(data.message || "Muvaffaqiyatli bajarildi!");
      uploadedImages = [];
      document.getElementById("post-text").value = "";
      renderImages();
      updatePreview();

      if (publishMode === "schedule") {
        setTimeout(() => switchTab("scheduled"), 1000);
      }
    } else {
      showToast(data.error || "Xatolik yuz berdi", true);
    }
  } catch (e) {
    btn.disabled = false;
    btn.style.opacity = "1";
    showToast("Tarmoq xatosi yuz berdi", true);
  }
}

// Scheduled Posts Tab Management
async function loadScheduledPosts() {
  const container = document.getElementById("scheduled-posts-list");
  const counter = document.getElementById("scheduled-counter");

  try {
    const res = await fetch(`/api/posts?user_id=${currentUser.id}`);
    const data = await res.json();
    if (!data.ok) return;

    const posts = data.posts || [];
    const scheduled = posts.filter(p => p.status === "scheduled");

    if (scheduled.length > 0) {
      counter.innerText = scheduled.length;
      counter.style.display = "inline-block";
    } else {
      counter.style.display = "none";
    }

    if (posts.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--hint-color); padding: 40px 20px;">
          <div style="font-size: 32px; margin-bottom: 8px;">📭</div>
          Hozircha hech qanday post mavjud emas.
        </div>
      `;
      return;
    }

    container.innerHTML = "";
    posts.forEach(p => {
      const card = document.createElement("div");
      card.className = "post-item-card";

      const isScheduled = p.status === "scheduled";
      const statusClass = `status-${p.status}`;
      const statusText = p.status === "scheduled" ? "Rejalashtirilgan" : (p.status === "published" ? "Chop etilgan" : "Xato");
      const timeStr = p.scheduled_at ? new Date(p.scheduled_at).toLocaleString("uz-UZ") : (p.created_at || "");

      card.innerHTML = `
        <div class="post-item-header">
          <span class="post-item-channel">📢 ${p.target_channel}</span>
          <span class="post-status-badge ${statusClass}">${statusText}</span>
        </div>
        <div class="post-item-body">${p.text ? p.text : "<i>(Faqat media)</i>"}</div>
        <div class="post-item-meta">
          <span>📸 ${p.images?.length || 0} ta rasm</span>
          <span>⏰ ${timeStr}</span>
        </div>
        ${isScheduled ? `
          <div class="post-item-actions">
            <button class="btn-small-send" onclick="sendPostNow(${p.id})">⚡ Hozir yuborish</button>
            <button class="btn-small-del" onclick="deleteScheduledPost(${p.id})">🗑️ Bekor qilish</button>
          </div>
        ` : ""}
      `;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = `<div style="text-align:center; color:var(--danger-color); padding:20px;">Yuklashda xatolik yuz berdi</div>`;
  }
}

async function sendPostNow(postId) {
  if (!confirm("Ushbu postni hoziroq kanalga yuborishni tasdiqlaysizmi?")) return;
  showToast("Yuborilmoqda...");
  try {
    const res = await fetch(`/api/posts/${postId}/send-now?user_id=${currentUser.id}`, { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      showToast("Post muvaffaqiyatli kanalga yuborildi!");
      loadScheduledPosts();
    } else {
      showToast(data.error || "Yuborishda xatolik", true);
    }
  } catch (e) {
    showToast("Aloqa xatosi", true);
  }
}

async function deleteScheduledPost(postId) {
  if (!confirm("Rejalashtirilgan postni bekor qilmoqchimisiz?")) return;
  try {
    const res = await fetch(`/api/posts/${postId}?user_id=${currentUser.id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.ok) {
      showToast("Post bekor qilindi");
      loadScheduledPosts();
    }
  } catch (e) {
    showToast("O'chirishda xatolik", true);
  }
}

// ==========================================
// TEMPLATES & RECURRING AUTO-POSTING LOGIC
// ==========================================

async function loadTemplates() {
  const container = document.getElementById("templates-list-container");
  const quickBar = document.getElementById("quick-template-bar");
  const quickSelect = document.getElementById("editor-template-select");

  try {
    const res = await fetch(`/api/templates?user_id=${currentUser.id}`);
    const data = await res.json();
    if (!data.ok) return;

    userTemplates = data.templates || [];

    // Populate quick template select in editor
    if (userTemplates.length > 0) {
      quickBar.style.display = "block";
      quickSelect.innerHTML = '<option value="">-- Shablondan yuklash --</option>';
      userTemplates.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t.id;
        opt.innerText = `${t.name} (${t.target_channel})`;
        quickSelect.appendChild(opt);
      });
    } else {
      quickBar.style.display = "none";
    }

    if (userTemplates.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--hint-color); padding: 40px 20px;">
          <div style="font-size: 32px; margin-bottom: 8px;">📑</div>
          Hozircha shablonlar mavjud emas.<br>
          Yuqoridagi <b>➕ Yangi shablon</b> tugmasini bosib doimiy post jadvalini yarating!
        </div>
      `;
      return;
    }

    container.innerHTML = "";
    userTemplates.forEach(t => {
      const card = document.createElement("div");
      card.className = "post-item-card";

      const isActive = Boolean(t.is_active);
      const isRecurring = Boolean(t.is_recurring);
      const statusBadge = isRecurring ? (isActive ? "🟢 Avto-faol" : "⏸️ To'xtatilgan") : "📑 Faqat shablon";
      const statusClass = isActive ? "status-published" : "status-scheduled";

      let scheduleText = "Qo'lda yuborish";
      if (isRecurring) {
        if (t.interval_type === "daily") {
          scheduleText = `Har kuni ${t.daily_time || "09:00"} da`;
        } else if (t.interval_type === "interval_hours") {
          scheduleText = `Har ${t.interval_value} soatda bir marta`;
        } else if (t.interval_type === "interval_minutes") {
          scheduleText = `Har ${t.interval_value} daqiqada bir marta`;
        }
      }

      const nextRunStr = t.next_run_at ? new Date(t.next_run_at).toLocaleString("uz-UZ") : "Belgilanmagan";

      card.innerHTML = `
        <div class="post-item-header">
          <div>
            <span style="font-weight:700; font-size:15px; color:var(--text-color);">${t.name}</span>
            <div style="font-size:12px; color:var(--link-color);">📢 ${t.target_channel}</div>
          </div>
          <span class="post-status-badge ${statusClass}">${statusBadge}</span>
        </div>
        <div class="post-item-body">${t.text ? t.text : "<i>(Matnsiz)</i>"}</div>
        <div class="post-item-meta" style="flex-direction:column; align-items:flex-start; gap:4px; margin-bottom:8px;">
          <span>🔄 Davriylik: <b>${scheduleText}</b></span>
          ${isRecurring && isActive ? `<span>⏳ Keyingi yuborish: <b>${nextRunStr}</b></span>` : ""}
        </div>
        <div class="post-item-actions">
          <button class="btn-small-send" onclick="triggerTemplateDirectly(${t.id})">⚡ Hozir chiqarish</button>
          ${isRecurring ? `
            <button class="action-btn-sm" style="padding: 8px 12px; font-size:12px;" onclick="toggleTemplateStatus(${t.id}, ${isActive ? "false" : "true"})">
              ${isActive ? "⏸️ To'xtatish" : "▶️ Yoqish"}
            </button>
          ` : ""}
          <button class="action-btn-sm" style="padding: 8px 10px; font-size:12px; background: rgba(59,130,246,0.2); color:var(--link-color);" onclick="onLoadTemplateToEditor(${t.id})">
            ✍️ Postga
          </button>
          <button class="btn-small-del" onclick="deleteTemplateAction(${t.id})">🗑️</button>
        </div>
      `;
      container.appendChild(card);
    });

  } catch (e) {
    container.innerHTML = `<div style="text-align:center; color:var(--danger-color); padding:20px;">Yuklashda xatolik yuz berdi</div>`;
  }
}

function openCreateTemplateModal() {
  const card = document.getElementById("template-create-card");
  card.style.display = "block";
  // Prefill channel from input if present
  const currentCh = document.getElementById("channel-input").value.trim();
  if (currentCh) {
    document.getElementById("tpl-channel").value = currentCh;
  }
}

function closeCreateTemplateCard() {
  document.getElementById("template-create-card").style.display = "none";
}

function toggleRecurringOptions() {
  const isRec = document.getElementById("tpl-is-recurring").checked;
  document.getElementById("tpl-recurring-options").style.display = isRec ? "block" : "none";
}

function onIntervalTypeChange() {
  const val = document.getElementById("tpl-interval-type").value;
  const dailyBox = document.getElementById("tpl-daily-time-box");
  const intervalBox = document.getElementById("tpl-interval-val-box");
  const label = document.getElementById("tpl-interval-label");

  if (val === "daily") {
    dailyBox.style.display = "block";
    intervalBox.style.display = "none";
  } else {
    dailyBox.style.display = "none";
    intervalBox.style.display = "block";
    label.innerText = (val === "interval_minutes") ? "Har necha daqiqada:" : "Har necha soatda:";
  }
}

async function saveTemplateFromForm() {
  const name = document.getElementById("tpl-name").value.trim();
  const channel = document.getElementById("tpl-channel").value.trim();
  const text = document.getElementById("tpl-text").value.trim();
  const isRecurring = document.getElementById("tpl-is-recurring").checked;
  const intervalType = document.getElementById("tpl-interval-type").value;
  const dailyTime = document.getElementById("tpl-daily-time").value;
  const intervalValue = parseInt(document.getElementById("tpl-interval-value").value) || 1;

  if (!name) {
    showToast("Shablon nomini kiriting!", true);
    return;
  }
  if (!channel) {
    showToast("Biriktirilgan kanalni (@kanal_nomi) kiriting!", true);
    return;
  }
  if (!text) {
    showToast("Post matnini kiriting!", true);
    return;
  }

  // Inherit current buttons setup
  const buttonsConfig = {};
  if (document.getElementById("toggle-reactions").checked && selectedEmojis.length > 0) {
    buttonsConfig.reactions = selectedEmojis.map(e => ({ emoji: e }));
  }
  if (document.getElementById("toggle-share").checked) {
    buttonsConfig.share = { enabled: true, text: "↗️ Ulashish" };
  }

  const payload = {
    user_id: currentUser.id,
    name: name,
    target_channel: channel,
    text: text,
    images: [],
    buttons_config: buttonsConfig,
    is_recurring: isRecurring,
    interval_type: intervalType,
    interval_value: intervalValue,
    daily_time: dailyTime,
    weekdays: [],
    pin_post: false,
    silent: false,
    is_active: true
  };

  showToast("Saqlanmoqda...");
  try {
    const res = await fetch("/api/templates", {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.ok) {
      showToast("Shablon va avto-post jadvali saqlandi!");
      closeCreateTemplateCard();
      loadTemplates();
    } else {
      showToast(data.error || "Xatolik yuz berdi", true);
    }
  } catch (e) {
    showToast("Server bilan aloqa uzildi", true);
  }
}

async function toggleTemplateStatus(tplId, makeActive) {
  try {
    const res = await fetch(`/api/templates/${tplId}/toggle?is_active=${makeActive}`, { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      showToast(makeActive ? "Avto-post faollashtirildi!" : "Avto-post to'xtatildi!");
      loadTemplates();
    }
  } catch (e) {
    showToast("Xatolik", true);
  }
}

async function triggerTemplateDirectly(tplId) {
  if (!confirm("Ushbu shablon asosida postni hoziroq kanalga chiqarishni xohlaysizmi?")) return;
  showToast("Yuborilmoqda...");
  try {
    const res = await fetch(`/api/templates/${tplId}/run-now?user_id=${currentUser.id}`, { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      showToast("Post muvaffaqiyatli kanalga chiqarildi!");
      loadTemplates();
    } else {
      showToast(data.error || "Yuborishda xatolik", true);
    }
  } catch (e) {
    showToast("Xatolik", true);
  }
}

async function deleteTemplateAction(tplId) {
  if (!confirm("Ushbu shablonni o'chirishni tasdiqlaysizmi?")) return;
  try {
    const res = await fetch(`/api/templates/${tplId}?user_id=${currentUser.id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.ok) {
      showToast("Shablon o'chirildi");
      loadTemplates();
    }
  } catch (e) {
    showToast("Xatolik", true);
  }
}

function onLoadTemplateToEditor(tplId) {
  if (!tplId) return;
  const tpl = userTemplates.find(t => t.id == tplId);
  if (!tpl) return;

  document.getElementById("channel-input").value = tpl.target_channel || "";
  document.getElementById("post-text").value = tpl.text || "";
  updatePreview();
  switchTab("editor");
  showToast(`"${tpl.name}" shabloni muharrirga yuklandi!`);
}
