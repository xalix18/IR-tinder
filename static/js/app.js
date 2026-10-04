// دریافت توکن احراز هویت تلگرام
const tg = window.Telegram?.WebApp;
let initData = "";
let currentUser = null;
let currentOptions = {};
let candidatesQueue = [];
let currentFilters = { city: "همه", gender: "any", min_age: 16, max_age: 60 };

document.addEventListener("DOMContentLoaded", async () => {
    if (tg) {
        tg.expand();
        tg.enableClosingConfirmation();
        initData = tg.initData || "";
    }

    setupTabs();
    setupFilters();
    await initApp();
});

// ارتباط با بک‌اند
async function fetchAPI(endpoint, method = "GET", body = null) {
    const headers = {
        "Content-Type": "application/json",
        "X-Telegram-Init-Data": initData
    };

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(`/api/${endpoint}`, options);
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "خطایی رخ داد");
    }
    return res.json();
}

// مقداردهی اولیه برنامه
async function initApp() {
    try {
        const data = await fetchAPI("init");
        currentUser = data.user;
        currentOptions = data.options;

        document.getElementById("loading-screen").classList.add("hidden");

        // اگر پروفایل کامل نبود، فرم را نشان بده
        if (!currentUser.is_complete) {
            openProfileModal(true);
        } else {
            renderMyProfile();
            await loadCandidates();
        }
    } catch (e) {
        alert("خطا در بارگذاری اولیه: " + e.message);
    }
}

// بارگذاری گزینه‌های کاندیدا
async function loadCandidates() {
    const data = await fetchAPI("candidates", "POST", currentFilters);
    candidatesQueue = data.candidates || [];
    renderCards();
}

// رندر کارت‌های سوایپ
function renderCards() {
    const container = document.getElementById("card-container");
    const emptyState = document.getElementById("empty-state");
    container.innerHTML = "";

    if (candidatesQueue.length === 0) {
        emptyState.classList.remove("hidden");
        return;
    }
    emptyState.classList.add("hidden");

    candidatesQueue.forEach((user, index) => {
        const card = document.createElement("div");
        card.className = "tinder-card";
        card.style.zIndex = candidatesQueue.length - index;

        const photoUrl = user.photo_path || "/static/images/default-avatar.png";
        card.style.backgroundImage = `url('${photoUrl}')`;

        card.innerHTML = `
            <div class="badge-swipe badge-like">LIKE</div>
            <div class="badge-swipe badge-pass">NOPE</div>
            <div class="card-gradient">
                <div class="card-title">${user.name}، ${user.age}</div>
                <div class="card-subtitle"><i class="fa-solid fa-location-dot"></i> ${user.city} ${user.job ? '• ' + user.job : ''}</div>
                ${user.bio ? `<div class="card-bio">${user.bio}</div>` : ''}
            </div>
        `;

        if (index === 0) {
            initCardSwipe(card, user);
        }
        container.appendChild(card);
    });
}

// قابلیت کشیدن کارت با لمس و ماوس
function initCardSwipe(card, user) {
    let startX = 0, currentX = 0, isDragging = false;
    const likeBadge = card.querySelector(".badge-like");
    const passBadge = card.querySelector(".badge-pass");

    const onStart = (e) => {
        isDragging = true;
        startX = e.clientX || e.touches[0].clientX;
        card.classList.add("dragging");
    };

    const onMove = (e) => {
        if (!isDragging) return;
        currentX = (e.clientX || e.touches[0].clientX) - startX;
        const rotate = currentX * 0.08;
        card.style.transform = `translateX(${currentX}px) rotate(${rotate}deg)`;

        // نمایش برچسب‌ها
        if (currentX > 30) {
            likeBadge.style.opacity = Math.min(currentX / 100, 1);
            passBadge.style.opacity = 0;
        } else if (currentX < -30) {
            passBadge.style.opacity = Math.min(-currentX / 100, 1);
            likeBadge.style.opacity = 0;
        } else {
            likeBadge.style.opacity = 0;
            passBadge.style.opacity = 0;
        }
    };

    const onEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        card.classList.remove("dragging");

        if (currentX > 120) {
            swipeAction(user.user_id, "like", card);
        } else if (currentX < -120) {
            swipeAction(user.user_id, "pass", card);
        } else {
            card.style.transform = "";
            likeBadge.style.opacity = 0;
            passBadge.style.opacity = 0;
        }
    };

    card.addEventListener("mousedown", onStart);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onEnd);

    card.addEventListener("touchstart", onStart);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", onEnd);
}

// ارسال لایک یا رد
async function swipeAction(targetId, action, cardElement) {
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred("medium");

    const direction = action === "like" ? 500 : -500;
    if (cardElement) {
        cardElement.style.transform = `translateX(${direction}px) rotate(${direction * 0.1}deg)`;
        cardElement.style.opacity = "0";
    }

    try {
        const res = await fetchAPI("swipe", "POST", { target_id: targetId, action });
        candidatesQueue.shift();
        setTimeout(() => renderCards(), 200);

        if (res.match && res.matched_user) {
            showMatchModal(res.matched_user);
        }
    } catch (e) {
        alert(e.message);
        renderCards();
    }
}

// پاپ‌آپ مچ شدن
function showMatchModal(targetUser) {
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
    const modal = document.getElementById("match-popup");
    document.getElementById("match-my-img").src = currentUser.photo_path || "/static/images/default-avatar.png";
    document.getElementById("match-target-img").src = targetUser.photo_path || "/static/images/default-avatar.png";

    const chatBtn = document.getElementById("match-chat-btn");
    if (targetUser.username) {
        chatBtn.href = `https://t.me/${targetUser.username}`;
        chatBtn.classList.remove("hidden");
    } else {
        chatBtn.classList.add("hidden");
    }

    modal.classList.remove("hidden");
    document.getElementById("match-close-btn").onclick = () => modal.classList.add("hidden");
}

// ناوبری تب‌ها
function setupTabs() {
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-view").forEach(t => t.classList.add("hidden"));

            btn.classList.add("active");
            const tabId = btn.getAttribute("data-tab");
            document.getElementById(tabId).classList.remove("hidden");

            if (tabId === "tab-matches") loadMatches();
        });
    });

    // دکمه‌های سوایپ دستی
    document.getElementById("btn-like").onclick = () => {
        if (candidatesQueue.length) swipeAction(candidatesQueue[0].user_id, "like", document.querySelector(".tinder-card"));
    };
    document.getElementById("btn-pass").onclick = () => {
        if (candidatesQueue.length) swipeAction(candidatesQueue[0].user_id, "pass", document.querySelector(".tinder-card"));
    };
    document.getElementById("btn-restart").onclick = async () => {
        await fetchAPI("reset-seen", "POST");
        await loadCandidates();
    };
}

// بارگذاری مچ‌ها
async function loadMatches() {
    const list = document.getElementById("matches-list");
    list.innerHTML = "<p>در حال دریافت...</p>";
    try {
        const data = await fetchAPI("matches");
        if (!data.matches.length) {
            list.innerHTML = "<p class='text-center'>هنوز مچی ندارید. افراد بیشتری را لایک کنید!</p>";
            return;
        }
        list.innerHTML = data.matches.map(m => `
            <div class="match-item">
                <img src="${m.photo_path || '/static/images/default-avatar.png'}">
                <h4>${m.name}، ${m.age}</h4>
                <p class="card-subtitle">${m.city}</p>
                ${m.username ? `<a href="https://t.me/${m.username}" target="_blank" class="btn btn-primary"><i class="fa-brands fa-telegram"></i> گفت‌وگو</a>` : ''}
            </div>
        `).join("");
    } catch (e) {
        list.innerHTML = "<p>خطا در بارگذاری مچ‌ها</p>";
    }
}

// پروفایل
function renderMyProfile() {
    document.getElementById("my-name-age").textContent = `${currentUser.name}، ${currentUser.age}`;
    document.getElementById("my-location").innerHTML = `<i class="fa-solid fa-location-dot"></i> ${currentUser.city}`;
    document.getElementById("my-bio").textContent = currentUser.bio || "بیوگرافی هنوز وارد نشده است.";
    if (currentUser.photo_path) document.getElementById("my-avatar").src = currentUser.photo_path;

    // آپلود عکس
    document.getElementById("photo-upload").onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append("photo", file);

        const res = await fetch("/api/photo", {
            method: "POST",
            headers: { "X-Telegram-Init-Data": initData },
            body: fd
        });
        if (res.ok) {
            const data = await res.json();
            currentUser.photo_path = data.photo_url;
            document.getElementById("my-avatar").src = data.photo_url;
        } else {
            alert("خطا در آپلود عکس");
        }
    };

    document.getElementById("btn-edit-profile").onclick = () => openProfileModal(false);
}

// فرم تکمیل/ویرایش پروفایل
function openProfileModal(isNew = false) {
    const modal = document.getElementById("register-modal");
    const citySelect = document.getElementById("reg-city");
    const eduSelect = document.getElementById("reg-education");
    const goalSelect = document.getElementById("reg-goal");
    const chipsBox = document.getElementById("interests-chips");

    citySelect.innerHTML = currentOptions.cities.map(c => `<option value="${c}">${c}</option>`).join("");
    eduSelect.innerHTML = currentOptions.education_levels.map(e => `<option value="${e}">${e}</option>`).join("");
    goalSelect.innerHTML = currentOptions.goals.map(g => `<option value="${g}">${g}</option>`).join("");

    let selectedInterests = currentUser.interests || [];
    chipsBox.innerHTML = currentOptions.interests.map(i => {
        const isSel = selectedInterests.includes(i) ? "selected" : "";
        return `<div class="chip ${isSel}" data-val="${i}">${i}</div>`;
    }).join("");

    chipsBox.querySelectorAll(".chip").forEach(chip => {
        chip.onclick = () => {
            const val = chip.getAttribute("data-val");
            if (selectedInterests.includes(val)) {
                selectedInterests = selectedInterests.filter(x => x !== val);
                chip.classList.remove("selected");
            } else {
                if (selectedInterests.length >= 5) return alert("حداکثر ۵ مورد!");
                selectedInterests.push(val);
                chip.classList.add("selected");
            }
        };
    });

    if (!isNew) {
        document.getElementById("reg-name").value = currentUser.name || "";
        document.getElementById("reg-age").value = currentUser.age || "";
        document.getElementById("reg-gender").value = currentUser.gender || "male";
        document.getElementById("reg-city").value = currentUser.city || currentOptions.cities[0];
        document.getElementById("reg-job").value = currentUser.job || "";
        document.getElementById("reg-bio").value = currentUser.bio || "";
    }

    modal.classList.remove("hidden");

    document.getElementById("profile-form").onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById("reg-name").value,
            age: parseInt(document.getElementById("reg-age").value),
            gender: document.getElementById("reg-gender").value,
            city: document.getElementById("reg-city").value,
            job: document.getElementById("reg-job").value,
            education: eduSelect.value,
            goal: goalSelect.value,
            bio: document.getElementById("reg-bio").value,
            interests: selectedInterests
        };

        try {
            await fetchAPI("profile", "POST", payload);
            Object.assign(currentUser, payload);
            currentUser.is_complete = 1;
            modal.classList.add("hidden");
            renderMyProfile();
            await loadCandidates();
        } catch (err) {
            alert(err.message);
        }
    };
}

// فیلترها
function setupFilters() {
    const modal = document.getElementById("filter-modal");
    document.getElementById("btn-open-filter").onclick = () => {
        document.getElementById("filter-city").innerHTML = `<option value="همه">همه شهرها</option>` +
            currentOptions.cities.map(c => `<option value="${c}">${c}</option>`).join("");
        modal.classList.remove("hidden");
    };

    document.getElementById("btn-close-filter").onclick = () => modal.classList.add("hidden");

    document.getElementById("btn-apply-filter").onclick = async () => {
        currentFilters.gender = document.getElementById("filter-gender").value;
        currentFilters.city = document.getElementById("filter-city").value;
        currentFilters.min_age = parseInt(document.getElementById("filter-min-age").value);
        currentFilters.max_age = parseInt(document.getElementById("filter-max-age").value);

        modal.classList.add("hidden");
        await loadCandidates();
    };
}