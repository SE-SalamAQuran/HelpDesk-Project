const API = {
    token: () => localStorage.getItem("access_token"),

    save(d) {
        for (const k of [
            "access_token",
            "refresh_token",
            "role",
            "email",
            "uid",
            "user_id"
        ]) {
            if (d[k] != null) {
                localStorage.setItem(k, d[k]);
            }
        }

        if (d.permissions) {
            localStorage.setItem(
                "permissions",
                JSON.stringify(d.permissions)
            );
        }
    },

    clear() {
        [
            "access_token",
            "refresh_token",
            "role",
            "email",
            "uid",
            "user_id",
            "permissions"
        ].forEach(k => localStorage.removeItem(k));
    },

    async request(path, opt = {}) {
        const h = new Headers(opt.headers || {});

        if (
            !(opt.body instanceof FormData) &&
            !h.has("Content-Type")
        ) {
            h.set("Content-Type", "application/json");
        }

        const t = this.token();

        if (t) {
            h.set("Authorization", `Bearer ${t}`);
        }

        const r = await fetch(
            APP_CONFIG.API_BASE + path,
            {
                ...opt,
                headers: h
            }
        );

        let d = {};

        try {
            d = await r.json();
        } catch {}

        if (!r.ok) {
            throw new Error(
                d.message ||
                d.error ||
                `Request failed (${r.status})`
            );
        }

        return d;
    }
};


function toast(m, type = "success") {
    const e = document.getElementById("toast");

    if (!e) return;

    e.textContent = m;
    e.className = `toast show ${type}`;

    setTimeout(
        () => e.className = "toast",
        2800
    );
}


function requireAuth() {
    if (!API.token()) {
        location.href = "/login";
        return false;
    }

    return true;
}


function logout() {
    API.clear();
    location.href = "/login";
}


function esc(v) {
    return String(v ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}