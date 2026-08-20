import { createContext, useContext, useEffect, useState } from 'react';
import { getCurrentUser } from '../services/apiClient';
import { clearStoredAuthUser, getStoredAuthUser, normalizeAuthUser, setStoredAuthUser } from '../utils/authStorage';

const defaultAuthValue = {
    user: null,
    ready: true,
    isAuthenticated: false,
    login: () => {},
    logout: () => {},
};

const AuthContext = createContext(defaultAuthValue);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        const cachedUser = getStoredAuthUser();
        if (cachedUser) {
            setUser(normalizeAuthUser(cachedUser));
            getCurrentUser()
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
        setUser(normalized);
        setStoredAuthUser(normalized);
    };

    const logout = () => {
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
