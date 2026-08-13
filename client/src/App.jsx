import { useEffect } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import FavoritesPage from './pages/FavoritesPage';
import HistoryPage from './pages/HistoryPage';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MoodInputPage from './pages/MoodInputPage';
import MyPage from './pages/MyPage';
import RecommendationPage from './pages/RecommendationPage';

function NotFoundPage() {
    return (
        <main className="p-10 font-[Pretendard,sans-serif]">
            <h1>페이지를 찾을 수 없습니다.</h1>
            <p>요청한 경로가 존재하지 않습니다.</p>
            <p>
                <Link to="/">홈으로 이동</Link>
            </p>
        </main>
    );
}

function ScrollToTop() {
    const { pathname, search } = useLocation();

    useEffect(() => {
        window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    }, [pathname, search]);

    return null;
}

function App() {
    return (
        <>
            <ScrollToTop />
            <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route
                path="/home"
                element={
                    <ProtectedRoute>
                        <HomePage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/mood-input"
                element={
                    <ProtectedRoute>
                        <MoodInputPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/recommendations"
                element={
                    <ProtectedRoute>
                        <RecommendationPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/history"
                element={
                    <ProtectedRoute>
                        <HistoryPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/favorites"
                element={
                    <ProtectedRoute>
                        <FavoritesPage />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/my"
                element={
                    <ProtectedRoute>
                        <MyPage />
                    </ProtectedRoute>
                }
            />

            <Route path="/health" element={<Navigate to="/home" replace />} />
            <Route path="/mood/recommend" element={<Navigate to="/mood-input" replace />} />
            <Route path="/auth/spotify/login" element={<Navigate to="/login" replace />} />
            <Route path="/auth/spotify/callback" element={<LoginPage />} />
            <Route path="*" element={<NotFoundPage />} />
            </Routes>
        </>
    );
}

export default App;
