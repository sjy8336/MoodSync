import { createContext, useContext, useEffect, useState } from 'react';
import { getCurrentUser, getDemoSession } from '../services/apiClient';
import { clearStoredAuthUser, getStoredAuthUser, normalizeAuthUser, setStoredAuthUser } from '../utils/authStorage';

const defaultAuthValue = {
    user: null,
    ready: true,
    isAuthenticated: false,
    login: () => {},
    logout: () => {},
};

const AuthContext = createContext(defaultAuthValue);
const RECOMMENDATION_STORAGE_KEY = 'mood-sync:last-recommendation';

const clearRecommendationCache = () => {
    if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem(RECOMMENDATION_STORAGE_KEY);
    }
};

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        const cachedUser = getStoredAuthUser();
        if (cachedUser) {
            setUser(normalizeAuthUser(cachedUser));
            const refreshSession = cachedUser.auth_provider === 'demo'
                ? getDemoSession
                : getCurrentUser;
            refreshSession()
                .then((data) => {
                    if (data?.user) {
                        const nextUser = normalizeAuthUser(data.user);
                        setUser(nextUser);
                        setStoredAuthUser(nextUser);
                    }
                })
                .catch(() => {
                    clearStoredAuthUser();
                    setUser(null);
                })
                .finally(() => {
                    setReady(true);
                });
            return;
        }

        setReady(true);
    }, []);

    const login = (nextUser) => {
        const normalized = normalizeAuthUser(nextUser);
        clearRecommendationCache();
        setUser(normalized);
        setStoredAuthUser(normalized);
    };

    const logout = () => {
        clearRecommendationCache();
        setUser(null);
        clearStoredAuthUser();
    };

    const value = {
        user,
        ready,
        isAuthenticated: Boolean(user),
        login,
        logout,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const context = useContext(AuthContext);
    return context;
}
