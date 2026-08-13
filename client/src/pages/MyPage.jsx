import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getFavorites, getMoodDashboard, logoutAccount } from '../services/apiClient';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { useAuth } from '../contexts/AuthContext';

const Ic = ({ d, size = 20, color = 'currentColor', fill = 'none', sw = 1.8, className = '' }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill={fill}
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`inline-block shrink-0 align-middle ${className}`}
    >
        {(Array.isArray(d) ? d : [d]).map((p, i) => (
            <path key={i} d={p} />
        ))}
    </svg>
);

const I = {
    user: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
    mail: ['M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'm22 6-10 7L2 6'],
    calHeart: [
        'M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H3z',
        'M12 17a2 2 0 0 0 2-2c0-1-1-2-2-3-1 1-2 2-2 3a2 2 0 0 0 2 2z',
    ],
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    flame: 'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z',
    chevRight: 'M9 18l6-6-6-6',
    check: 'M20 6 9 17l-5-5',
    bell: ['M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9', 'M10.3 21a1.94 1.94 0 0 0 3.4 0'],
    link: [
        'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71',
        'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71',
    ],
    shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'],
    logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
    trash: ['M3 6h18', 'M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6', 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'],
    waveform: 'M2 12h2M6 8v8M10 5v14M14 9v6M18 6v12M22 12h2',
};

const SpotifyMark = ({ size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);

const AlbumCover = ({ src, title }) => {
    const [failed, setFailed] = useState(false);
    const hasSrc = Boolean(src) && !failed;

    return (
        <div className="w-11 h-11 rounded-[10px] overflow-hidden shrink-0 bg-[linear-gradient(135deg,#FFEAE6,#ECEDFD)]">
            {hasSrc ? (
                <img
                    src={src}
                    alt={title ? `${title} 앨범 커버` : '앨범 커버'}
                    onError={() => setFailed(true)}
                    className="w-full h-full object-cover block"
                />
            ) : (
                <div className="w-full h-full flex items-center justify-center bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)]">
                    <Ic d={I.music} size={16} color="#A39CAC" />
                </div>
            )}
        </div>
    );
};

const StatCard = ({ icon, color, soft, value, label }) => {
    const bgClass =
        soft === '#ECEDFD'
            ? 'bg-[#ECEDFD]'
            : soft === '#FFEAE6'
              ? 'bg-[#FFEAE6]'
              : soft === '#FFF3DE'
                ? 'bg-[#FFF3DE]'
                : 'bg-[#F1ECE3]';

    return (
        <div className="min-w-0 flex flex-col gap-2 rounded-2xl border border-[#E5DFD3] bg-white px-3 py-3.5 sm:px-4 sm:py-4">
            <div className={`flex h-7 w-7 items-center justify-center rounded-[10px] sm:h-8 sm:w-8 ${bgClass}`}>
                <Ic d={icon} size={14} color={color} className="sm:hidden" />
                <Ic d={icon} size={15} color={color} className="hidden sm:inline-block" />
            </div>
            <p className="truncate text-[17px] font-extrabold leading-none tracking-[-0.02em] text-[#211C26] sm:text-[20px]">
                {value}
            </p>
            <p className="truncate text-[11px] font-medium text-[#A39CAC] sm:text-[11.5px]">{label}</p>
        </div>
    );
};

const SettingRow = ({ icon, label, danger = false, onClick, to }) => {
    const content = (
        <>
            <span
                className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${
                    danger ? 'bg-[#FDEDEC]' : 'bg-[#F1ECE3]'
                }`}
            >
                <Ic d={icon} size={16} color={danger ? '#E0473E' : '#6E6678'} />
            </span>
            <span className={`flex-1 text-[14px] font-semibold ${danger ? 'text-[#E0473E]' : 'text-[#211C26]'}`}>
                {label}
            </span>
            {!danger && <Ic d={I.chevRight} size={15} color="#D6CFC1" />}
        </>
    );

    const className =
        'flex items-center gap-3 w-full px-4 py-3.5 rounded-2xl text-left transition-colors duration-150 hover:bg-[#FAF8F4]';

    if (to) {
        return (
            <Link to={to} className={`${className} no-underline`}>
                {content}
            </Link>
        );
    }

    return (
        <button type="button" onClick={onClick} className={className}>
            {content}
        </button>
    );
};

export default function MyPage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const [favorites, setFavorites] = useState([]);
    const [favoritesLoaded, setFavoritesLoaded] = useState(false);
    const [moodCount, setMoodCount] = useState(null);
    const [streak, setStreak] = useState(null);

    const displayName =
        user?.displayName ||
        user?.display_name ||
        user?.email ||
        user?.providerUserId ||
        user?.provider_user_id ||
        'Spotify 사용자';
    const email = user?.email || null;
    const initial = displayName?.trim()?.[0]?.toUpperCase() || 'M';

    useEffect(() => {
        let active = true;

        getFavorites()
            .then((data) => {
                if (!active) return;
                const items = Array.isArray(data) ? data : data?.items || [];
                setFavorites(items.slice(0, 3));
            })
            .catch(() => {
                if (active) setFavorites([]);
            })
            .finally(() => {
                if (active) setFavoritesLoaded(true);
            });

        getMoodDashboard()
            .then((data) => {
                if (!active) return;
                setMoodCount(data?.total_mood_count ?? data?.recent_moods?.length ?? 0);
                setStreak(data?.streak_days ?? 0);
            })
            .catch(() => {
                if (active) {
                    setMoodCount(0);
                    setStreak(0);
                }
            });

        return () => {
            active = false;
        };
    }, []);

    const handleLogout = async () => {
        try {
            await logoutAccount();
        } catch {
            // 서버 쿠키 정리가 실패하더라도 로컬 로그아웃은 보장한다.
        } finally {
            logout();
            navigate('/login', { replace: true });
        }
    };

    const favoriteCount = favorites.length;

    return (
        <div className="min-h-screen bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif] antialiased overflow-x-hidden">
            <Header />

            <main className="max-w-[760px] mx-auto px-5 sm:px-7 md:px-8 pt-24 md:pt-28 pb-24 md:pb-20">
                {/* ── 프로필 헤더 ── */}
                <section className="flex items-center gap-4 mb-6">
                    <div className="w-16 h-16 rounded-full flex items-center justify-center text-[22px] font-extrabold text-white shrink-0 bg-[linear-gradient(135deg,#FF6B5E_0%,#7B7FF0_100%)]">
                        {initial}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[18px] font-extrabold text-[#211C26] tracking-[-0.02em] truncate">
                            {displayName}
                        </p>
                        {email && (
                            <p className="flex items-center gap-1.5 text-[12.5px] text-[#A39CAC] mt-[2px] truncate">
                                <Ic d={I.mail} size={12} color="#A39CAC" />
                                {email}
                            </p>
                        )}
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#1a9e4c] bg-[#EAFBF0] rounded-full px-2.5 py-1 mt-2">
                            <SpotifyMark size={12} />
                            Spotify 계정으로 연결됨
                        </span>
                    </div>
                </section>

                {/* ── 통계 카드 ── */}
                <section className="grid grid-cols-3 gap-2.5 sm:gap-3 mb-8">
                    <StatCard
                        icon={I.calHeart}
                        color="#7B7FF0"
                        soft="#ECEDFD"
                        value={moodCount ?? '–'}
                        label="감정 기록"
                    />
                    <StatCard
                        icon={I.heart}
                        color="#FF6B5E"
                        soft="#FFEAE6"
                        value={favoritesLoaded ? favoriteCount : '–'}
                        label="좋아요한 곡"
                    />
                    <StatCard icon={I.flame} color="#FFB648" soft="#FFF3DE" value={streak ?? '–'} label="연속 기록일" />
                </section>

                {/* ── 좋아요한 곡 미리보기 (Spotify 정책 준수) ── */}
                <section className="mb-8">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-[15px] font-bold text-[#211C26] flex items-center gap-2">
                            <Ic d={I.heart} size={14} color="#FF6B5E" fill="#FF6B5E" sw={0} />
                            좋아요한 곡
                        </h2>
                        <Link
                            to="/favorites"
                            className="text-[12.5px] font-semibold text-[#A39CAC] hover:text-[#6E6678] no-underline flex items-center gap-[3px] transition-colors duration-150"
                        >
                            전체 보기
                            <Ic d={I.chevRight} size={12} color="currentColor" />
                        </Link>
                    </div>

                    {favoritesLoaded && favorites.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-[#D6CFC1] bg-white px-4 py-6 text-center">
                            <p className="text-[13px] font-semibold text-[#211C26]">아직 좋아요한 곡이 없어요</p>
                            <p className="text-[12px] text-[#A39CAC] mt-1">
                                추천받은 곡에 좋아요를 남기면 여기 모아볼 수 있어요.
                            </p>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-2">
                            {(favorites.length > 0
                                ? favorites
                                : [{ track_id: 'skeleton-1', track_name: '', artist_name: '', spotify_url: '' }]
                            ).map((track, i) => (
                                <a
                                    key={track.track_id || i}
                                    href={track.spotify_url || 'https://open.spotify.com'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2.5 sm:gap-3 bg-white border border-[#E5DFD3] rounded-2xl px-2.5 sm:px-3 py-2.5 no-underline transition-colors duration-150 hover:bg-[#FAF8F4]"
                                >
                                    <AlbumCover src={track.album_image_url} title={track.track_name} />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-[13px] font-bold text-[#211C26] truncate leading-tight">
                                            {track.track_name || '곡 정보 없음'}
                                        </p>
                                        <p className="text-[11.5px] text-[#A39CAC] truncate mt-[1px]">
                                            {track.artist_name || '-'}
                                        </p>
                                        <p className="flex items-center gap-[4px] text-[10px] text-[#A39CAC] mt-[3px] sm:hidden">
                                            <SpotifyMark size={10} />
                                            Provided by Spotify
                                        </p>
                                    </div>
                                    <span className="hidden sm:flex items-center gap-[4px] text-[10px] text-[#A39CAC] shrink-0 whitespace-nowrap">
                                        <SpotifyMark size={11} />
                                        Provided by Spotify
                                    </span>
                                    <span className="w-7 h-7 rounded-full flex items-center justify-center bg-[#1ED760] shrink-0">
                                        <Ic d={I.chevRight} size={12} color="#191414" sw={2.4} />
                                    </span>
                                </a>
                            ))}
                        </div>
                    )}
                </section>

                {/* ── 설정 ── */}
                <section className="mb-8">
                    <h2 className="text-[13px] font-bold text-[#A39CAC] uppercase tracking-[0.06em] mb-2 px-1">
                        계정 및 설정
                    </h2>
                    <div className="bg-white border border-[#E5DFD3] rounded-2xl p-1.5 flex flex-col gap-0.5">
                        <SettingRow icon={I.user} label="프로필 정보" to="/my" />
                        <SettingRow icon={I.bell} label="알림 설정" to="/my" />
                        <SettingRow icon={I.link} label="Spotify 연결 관리" to="/my" />
                        <SettingRow icon={I.shield} label="개인정보 및 보안" to="/my" />
                    </div>
                </section>

                <section>
                    <div className="bg-white border border-[#E5DFD3] rounded-2xl p-1.5 flex flex-col gap-0.5">
                        <SettingRow icon={I.logout} label="로그아웃" onClick={handleLogout} />
                        <SettingRow icon={I.trash} label="회원 탈퇴" danger onClick={() => {}} />
                    </div>
                </section>

                {/* ── 모바일 전용 하단 nav ── */}
                <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-[#E5DFD3] z-40 flex">
                    {[
                        { to: '/home', label: '홈', icon: I.waveform },
                        { to: '/mood-input', label: '기록', icon: I.heart },
                        { to: '/recommendations', label: '추천', icon: I.music },
                        { to: '/history', label: '히스토리', icon: I.calHeart },
                        { to: '/my', label: '마이', icon: I.user },
                    ].map(({ to, label, icon }) => (
                        <Link
                            key={to}
                            to={to}
                            className={`flex-1 flex flex-col items-center gap-[3px] py-[10px] no-underline transition-colors duration-150 ${
                                to === '/my' ? 'text-[#211C26]' : 'text-[#A39CAC] hover:text-[#211C26]'
                            }`}
                        >
                            <Ic d={icon} size={20} color="currentColor" />
                            <span className="text-[10px] font-semibold">{label}</span>
                        </Link>
                    ))}
                </nav>
            </main>

            <Footer wrap="max-w-[1240px] mx-auto px-5" />
        </div>
    );
}
