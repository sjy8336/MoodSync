const AUTH_STORAGE_KEY = 'mood-sync-auth-user';

export function normalizeAuthUser(user) {
    if (!user) return null;
    const displayName =
        user.displayName ||
        user.display_name ||
        user.email ||
        user.providerUserId ||
        user.provider_user_id ||
        'Spotify 사용자';

    return {
        ...user,
        displayName,
        providerUserId: user.providerUserId || user.provider_user_id || null,
    };
}

export function getStoredAuthUser() {
    try {
        const raw = localStorage.getItem(AUTH_STORAGE_KEY);
        return raw ? normalizeAuthUser(JSON.parse(raw)) : null;
    } catch {
        return null;
    }
}

export function setStoredAuthUser(user) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(normalizeAuthUser(user)));
}

export function clearStoredAuthUser() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
}
