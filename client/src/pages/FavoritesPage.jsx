import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { getFavorites, removeFavorite } from '../services/apiClient';
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
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    play: 'M6 3l15 9-15 9V3z',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    rain: ['M20 16.2A4.5 4.5 0 0 0 17.5 8H16.74A7 7 0 1 0 7 17.97', 'M16 20v2M8 20v2M12 20v2'],
    cloud: 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z',
    sparkle: 'M12 3l1.9 5.87L20 10l-5.87 1.9L12 18l-1.9-5.87L4 10l5.87-1.9z',
    moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
    clock: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 6v6l4 2'],
    bulb: [
        'M9 18h6M10 22h4M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z',
    ],
    search: ['M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z'],
    filter: ['M22 3H2l8 9.46V19l4 2v-8.54L22 3z'],
    trash: [
        'M3 6h18M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2',
    ],
    arrowR: 'M5 12h14M12 5l7 7-7 7',
    check: 'M20 6 9 17l-5-5',
    grid: ['M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'],
    list: ['M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01'],
    x: 'M18 6 6 18M6 6l12 12',
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


const MOOD_MAP = {
    happy: { label: '기쁨', icon: I.smile, color: '#FF6B5E', soft: '#FFEAE6' },
    excited: { label: '설렘', icon: I.sparkle, color: '#FFB648', soft: '#FFF3DE' },
    sad: { label: '우울', icon: I.rain, color: '#7B7FF0', soft: '#ECEDFD' },
    lonely: { label: '외로움', icon: I.moon, color: '#7B7FF0', soft: '#ECEDFD' },
    tired: { label: '피로', icon: I.moon, color: '#6E6678', soft: '#F1ECE3' },
    calm: { label: '평온', icon: I.cloud, color: '#9B8FD4', soft: '#EDEAFC' },
    angry: { label: '분노', icon: I.sparkles, color: '#FF6B5E', soft: '#FFEAE6' },
    anxious: { label: '불안', icon: I.sparkles, color: '#7B7FF0', soft: '#ECEDFD' },
    focused: { label: '집중', icon: I.sparkles, color: '#FFB648', soft: '#FFF3DE' },
    grateful: { label: '감사', icon: I.heart, color: '#E8805A', soft: '#FFF0EC' },
    neutral: { label: '보통', icon: I.cloud, color: '#A39CAC', soft: '#F1ECE3' },
    nostalgic: { label: '그리움', icon: I.sparkle, color: '#C97EB6', soft: '#FAEAF7' },
};

const getMoodInfo = (mood) =>
    MOOD_MAP[mood] || { label: mood || '감정', icon: I.smile, color: '#A39CAC', soft: '#F1ECE3' };

const getSoftBgClass = (soft) => {
    switch (soft) {
        case '#FFEAE6':
            return 'bg-[#FFEAE6]';
        case '#FFF3DE':
            return 'bg-[#FFF3DE]';
        case '#ECEDFD':
            return 'bg-[#ECEDFD]';
        case '#EDEAFC':
            return 'bg-[#EDEAFC]';
        case '#FFF0EC':
            return 'bg-[#FFF0EC]';
        case '#FAEAF7':
            return 'bg-[#FAEAF7]';
        default:
            return 'bg-[#F1ECE3]';
    }
};

const getTextColorClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'text-[#FF6B5E]';
        case '#FFB648':
            return 'text-[#FFB648]';
        case '#7B7FF0':
            return 'text-[#7B7FF0]';
        case '#9B8FD4':
            return 'text-[#9B8FD4]';
        case '#E8805A':
            return 'text-[#E8805A]';
        case '#C97EB6':
            return 'text-[#C97EB6]';
        default:
            return 'text-[#6E6678]';
    }
};

const getMoodChipClass = (soft, color) => `${getSoftBgClass(soft)} ${getTextColorClass(color)}`;
const getAnimationDelayClass = (seconds) => `[animation-delay:${seconds}s]`;


const formatSavedAt = (dateStr) => {
    if (!dateStr) return null;
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return null;
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    return d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
};


const UnlikeToast = ({ visible, onClose }) => (
    <div
        className={`fixed bottom-7 left-1/2 z-[9999] flex items-center gap-2.5 whitespace-nowrap rounded-full bg-[#211C26] px-[18px] py-[11px] pl-[14px] text-[13.5px] font-semibold text-white shadow-[0_8px_32px_-8px_rgba(33,28,38,0.32)] transition-all duration-200 ${
            visible
                ? 'pointer-events-auto translate-x-[-50%] translate-y-0 opacity-100'
                : 'pointer-events-none translate-x-[-50%] translate-y-3 opacity-0'
        }`}
    >
        <Ic d={I.heart} size={14} color="#FF6B5E" fill="#FF6B5E" sw={0} />
        좋아요가 취소되었어요
        <button
            type="button"
            onClick={onClose}
            className="ml-1 flex cursor-pointer items-center bg-transparent border-0 p-0 text-[rgba(255,255,255,0.45)]"
            aria-label="닫기"
        >
            <Ic d={I.x} size={13} color="rgba(255,255,255,0.45)" />
        </button>
    </div>
);


const AlbumCover = ({ track, className = '', roundedClass = 'rounded-[10px]', iconSize = 14 }) => {
    const [imageFailed, setImageFailed] = useState(false);
    const hasImage = Boolean(track.album_image_url) && !imageFailed;

    return (
        <div className={`shrink-0 overflow-hidden bg-[linear-gradient(135deg,#FFEAE6,#ECEDFD)] ${roundedClass} ${className}`}>
            {hasImage ? (
                <img
                    src={track.album_image_url}
                    alt={`${track.album_name || track.name} 앨범 커버`}
                    onError={() => setImageFailed(true)}
                    className="block h-full w-full object-cover"
                />
            ) : (
                <div className="relative flex h-full w-full flex-col items-center justify-center gap-1 bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)]">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.5)_0%,transparent_36%)]" />
                    <Ic d={I.music} size={iconSize} color="#A39CAC" className="relative z-10" />
                </div>
            )}
        </div>
    );
};


const DUMMY_TRACKS = [
    {
        track_id: '1',
        name: 'Dynamite',
        artist_name: 'BTS',
        album_name: 'BE',
        album_image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
        spotify_url: 'https://open.spotify.com',
        duration_ms: 199054,
        mood: 'happy',
        reason: '밝고 리듬감 있는 곡으로, 기쁨의 활기를 더 끌어올려줄 수 있어요.',
        saved_at: new Date(Date.now() - 86400000 * 0).toISOString(),
    },
    {
        track_id: '2',
        name: 'Good Days',
        artist_name: 'SZA',
        album_name: 'Good Days',
        album_image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
        spotify_url: 'https://open.spotify.com',
        duration_ms: 274626,
        mood: 'excited',
        reason: '따뜻하고 밝은 멜로디가 설렘의 감정과 잘 어울려요.',
        saved_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    },
    {
        track_id: '3',
        name: 'Blinding Lights',
        artist_name: 'The Weeknd',
        album_name: 'After Hours',
        album_image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80',
        spotify_url: 'https://open.spotify.com',
        duration_ms: 200040,
        mood: 'excited',
        reason: '신나는 리듬감이 활기찬 기분을 더욱 살려줘요.',
        saved_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    },
    {
        track_id: '4',
        name: 'Someone Like You',
        artist_name: 'Adele',
        album_name: '21',
        album_image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=200&q=80',
        spotify_url: 'https://open.spotify.com',
        duration_ms: 285000,
        mood: 'sad',
        reason: '잔잔하고 감성적인 멜로디가 우울한 감정을 어루만져줘요.',
        saved_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    },
    {
        track_id: '5',
        name: 'Levitating',
        artist_name: 'Dua Lipa',
        album_name: 'Future Nostalgia',
        album_image_url: 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=200&q=80',
        spotify_url: 'https://open.spotify.com',
        duration_ms: 203000,
        mood: 'happy',
        reason: '경쾌하고 몽환적인 비트가 기쁜 기분과 완벽하게 어울려요.',
        saved_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    },
];

const MOOD_FILTERS = [
    { key: 'all', label: '전체' },
    { key: 'happy', label: '기쁨' },
    { key: 'excited', label: '설렘' },
    { key: 'sad', label: '우울' },
    { key: 'lonely', label: '외로움' },
    { key: 'calm', label: '평온' },
    { key: 'tired', label: '피로' },
    { key: 'angry', label: '분노' },
    { key: 'anxious', label: '불안' },
    { key: 'focused', label: '집중' },
    { key: 'grateful', label: '감사' },
    { key: 'neutral', label: '보통' },
    { key: 'nostalgic', label: '그리움' },
];


const FavoriteCard = ({ track, onUnlike }) => {
    const moodInfo = getMoodInfo(track.mood);
    const savedLabel = formatSavedAt(track.saved_at);

    const handleUnlike = () => {
        onUnlike?.(track.track_id);
    };

    return (
        <article className="bg-white border border-[#E5DFD3] rounded-2xl overflow-hidden transition-all duration-200 hover:border-[#D6CFC1] hover:shadow-[0_8px_28px_-8px_rgba(33,28,38,0.10)] group">
            <div className="flex items-stretch">

                        <a
                            href={track.spotify_url || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block shrink-0 leading-[0] p-3"
                            aria-label={`${track.name} Spotify에서 열기`}
                        >
                            <AlbumCover track={track} className="w-16 h-16" roundedClass="rounded-[10px]" iconSize={18} />
                        </a>


                <div className="flex-1 min-w-0 flex flex-col justify-center gap-[3px] pr-3 py-3">
                    {track.spotify_url ? (
                        <a
                            href={track.spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[14.5px] font-bold text-[#211C26] no-underline truncate block hover:text-[#7B7FF0] transition-colors duration-150 leading-snug"
                        >
                            {track.name}
                        </a>
                    ) : (
                        <span className="text-[14.5px] font-bold text-[#211C26] truncate block leading-snug">
                            {track.name}
                        </span>
                    )}

                    {track.spotify_url ? (
                        <a
                            href={track.spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[13px] text-[#6E6678] no-underline truncate block hover:text-[#211C26] transition-colors duration-150"
                        >
                            {track.artist_name}
                        </a>
                    ) : (
                        <span className="text-[13px] text-[#6E6678] truncate block">{track.artist_name}</span>
                    )}


                    <div className="flex flex-wrap items-center gap-1.5 mt-1">
                        <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-[2px] text-[11px] font-semibold ${getMoodChipClass(moodInfo.soft, moodInfo.color)}`}
                        >
                            <Ic d={moodInfo.icon} size={10} color={moodInfo.color} />
                            {moodInfo.label}
                        </span>
                        {savedLabel && (
                            <span className="inline-flex items-center gap-[3px] text-[11px] text-[#A39CAC]">
                                <Ic d={I.clock} size={10} color="#A39CAC" />
                                {savedLabel}
                            </span>
                        )}
                        <span className="inline-flex items-center gap-[3px] text-[11px] text-[#A39CAC]">
                            <SpotifyMark size={10} />
                            Provided by Spotify
                        </span>
                    </div>
                </div>


                <div className="flex flex-col items-center justify-center gap-2 px-3 shrink-0">
                    <button
                        type="button"
                        onClick={handleUnlike}
                        aria-label="좋아요 취소"
                        className="w-8 h-8 rounded-full flex items-center justify-center border-[1.5px] border-[#FF6B5E] bg-[#FFEAE6] hover:bg-[#FF6B5E] transition-all duration-200 cursor-pointer group/btn"
                    >
                        <Ic
                            d={I.heart}
                            size={13}
                            color="#FF6B5E"
                            fill="#FF6B5E"
                            className="group-hover/btn:!fill-white group-hover/btn:!stroke-white"
                        />
                    </button>

                    {track.spotify_url && (
                        <a
                            href={track.spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="Spotify에서 듣기"
                            className="w-8 h-8 rounded-full bg-[#1ED760] flex items-center justify-center no-underline transition-all duration-150 hover:scale-110"
                        >
                            <Ic d={I.play} size={11} color="#191414" fill="#191414" sw={0} />
                        </a>
                    )}
                </div>
            </div>


            {track.reason && (
                <div className="flex items-start gap-2 px-4 py-2.5 border-t border-[#EEEBE4]">
                    <Ic d={I.bulb} size={12} color="#7B7FF0" className="mt-[3px] shrink-0" />
                    <p className="text-[12px] text-[#A39CAC] leading-[1.6] m-0">{track.reason}</p>
                </div>
            )}
        </article>
    );
};


const EmptyState = () => (
    <div className="bg-white border border-[#E5DFD3] rounded-[28px] p-10 min-[560px]:p-14 text-center shadow-[0_8px_40px_-12px_rgba(33,28,38,0.08)] max-w-md mx-auto mt-4">
        <div className="w-14 h-14 rounded-2xl bg-[#FFEAE6] flex items-center justify-center mx-auto mb-5">
            <Ic d={I.heart} size={26} color="#FF6B5E" fill="#FF6B5E" />
        </div>
        <h2 className="text-[20px] font-extrabold text-[#211C26] tracking-[-0.02em] mb-2">아직 좋아요한 곡이 없어요</h2>
        <p className="text-[14px] text-[#6E6678] leading-[1.7] mb-7">
            추천받은 곡에서 하트를 누르면 여기에 저장돼요. 좋아요 기록이 쌓일수록 더 정확한 추천을 받을 수 있어요.
        </p>
        <Link
            to="/mood-input"
            className="inline-flex items-center gap-2 h-12 px-8 rounded-full bg-[#211C26] text-white text-[15px] font-bold no-underline transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_32px_-8px_rgba(33,28,38,0.35)]"
        >
            <Ic d={I.sparkles} size={16} color="#FFB648" />
            음악 추천받으러 가기
        </Link>
    </div>
);


export default function FavoritesPage() {
    const { user } = useAuth();
    const [tracks, setTracks] = useState([]);
    const [activeMood, setActiveMood] = useState('all');
    const [viewMode, setViewMode] = useState('list');
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const isDemoUser = user?.auth_provider === 'demo';
    const demoPresetKey = (user?.providerUserId || user?.provider_user_id || '').split(':')[1] || 'focus';
    const demoPresetLabel = {
        focus: '집중 테스트',
        jazz: '재즈 테스트',
        drive: '드라이브 테스트',
        dreamy: '몽환 테스트',
    }[demoPresetKey] || '데모';


    const [toastVisible, setToastVisible] = useState(false);
    const [toastTimer, setToastTimer] = useState(null);

    useEffect(() => {
        let active = true;

        const loadFavorites = async () => {
            setIsLoading(true);
            setLoadError('');
            try {
                const response = await getFavorites();
                if (!active) return;
                const items = Array.isArray(response) ? response : response?.items || [];
                setTracks(
                    items.map((item) => ({
                        ...item,
                        name: item.name || item.track_name || '제목 없는 곡',
                        artist_name: item.artist_name || '알 수 없는 아티스트',
                    }))
                );
            } catch (error) {
                if (!active) return;
                setLoadError(error.message || '좋아요한 곡을 불러오지 못했어요.');
            } finally {
                if (active) setIsLoading(false);
            }
        };

        loadFavorites();
        return () => {
            active = false;
        };
    }, []);


    const handleUnlike = async (trackId) => {
        try {
            await removeFavorite(trackId);
            setTracks((prev) => prev.filter((t) => t.track_id !== trackId));

            setToastVisible(true);
            if (toastTimer) clearTimeout(toastTimer);
            const timer = setTimeout(() => setToastVisible(false), 2800);
            setToastTimer(timer);
        } catch (error) {
            setLoadError(error.message || '좋아요 취소에 실패했어요.');
        }
    };

    useEffect(
        () => () => {
            if (toastTimer) clearTimeout(toastTimer);
        },
        [toastTimer]
    );


    const filtered = tracks.filter((t) => {
        const matchMood = activeMood === 'all' || t.mood === activeMood;
        const query = searchQuery.trim().toLowerCase();
        const matchQuery =
            !query || t.name.toLowerCase().includes(query) || t.artist_name.toLowerCase().includes(query);
        return matchMood && matchQuery;
    });


    const moodCounts = tracks.reduce((acc, t) => {
        acc[t.mood] = (acc[t.mood] || 0) + 1;
        return acc;
    }, {});

    return (
        <div className="font-[Pretendard,system-ui,sans-serif] bg-[#FAF8F4] text-[#211C26] antialiased overflow-x-hidden min-h-screen">

            <UnlikeToast visible={toastVisible} onClose={() => setToastVisible(false)} />

            <Header />

            <main className="pt-[100px] min-[900px]:pt-[120px] pb-20 min-[900px]:pb-28">
                <div className="fixed inset-0 pointer-events-none -z-10">
                    <div className="absolute inset-0 bg-[radial-gradient(50%_35%_at_10%_0%,rgba(255,107,94,0.06)_0%,transparent_70%)]" />
                    <div className="absolute inset-0 bg-[radial-gradient(40%_30%_at_90%_5%,rgba(123,127,240,0.06)_0%,transparent_70%)]" />
                </div>

                <div className="max-w-[1240px] mx-auto px-5 min-[560px]:px-7 min-[900px]:px-10">
                    {loadError && (
                        <div className="fav-fu mb-6 px-4 py-3 rounded-2xl border border-[rgba(255,107,94,0.22)] bg-[#FFEAE6] text-[13px] text-[#8B2218]">
                            {loadError}
                        </div>
                    )}

                    {isDemoUser && (
                        <div className="fav-fu mb-6 rounded-[24px] border border-[#C7C9FA] bg-[#F2F3FF] px-5 py-5 shadow-[0_10px_30px_-18px_rgba(123,127,240,0.4)]">
                            <div className="flex flex-col gap-4 min-[700px]:flex-row min-[700px]:items-end min-[700px]:justify-between">
                                <div>
                                    <div className="mb-2 flex flex-wrap items-center gap-2">
                                        <span className="inline-flex items-center rounded-full bg-[#7B7FF0] px-3 py-[6px] text-[12px] font-bold text-white">
                                            DEMO
                                        </span>
                                        <span className="text-[12.5px] font-semibold text-[#4B4FD0]">
                                            {demoPresetLabel}
                                        </span>
                                    </div>
                                    <h2 className="text-[18px] font-extrabold tracking-[-0.02em] text-[#211C26]">
                                        좋아요 샘플이 들어 있어요
                                    </h2>
                                    <p className="mt-1.5 max-w-[620px] text-[13.5px] leading-[1.7] text-[#4B4FD0]">
                                        좋아요를 눌렀다 취소해보면서 반영 상태를 확인해보세요. <br/>
                                        감정별 필터와 검색, Spotify 이동까지 실제 흐름으로 테스트할 수 있어요.
                                    </p>
                                </div>

                                <div className="flex flex-wrap items-center gap-2">
                                    <Link
                                        to="/mood-input"
                                        className="inline-flex items-center justify-center rounded-full bg-[#211C26] px-4 py-2.5 text-[13px] font-bold text-white no-underline transition-all duration-200 hover:-translate-y-px"
                                    >
                                        새 추천 받기
                                    </Link>
                                    <Link
                                        to="/history"
                                        className="inline-flex items-center justify-center rounded-full border border-[#C7C9FA] bg-white px-4 py-2.5 text-[13px] font-bold text-[#4B4FD0] no-underline transition-colors duration-150 hover:border-[#7B7FF0]"
                                    >
                                        기록도 보기
                                    </Link>
                                </div>
                            </div>
                        </div>
                    )}

                    <div
                        className={`fav-fu flex flex-wrap items-start justify-between gap-4 mb-8 ${getAnimationDelayClass(0.03)}`}
                    >
                        <div>
                            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#E5DFD3] text-[#6E6678] text-[12px] font-bold uppercase tracking-[0.06em] mb-3">
                                <Ic d={I.heart} size={11} color="#FF6B5E" fill="#FF6B5E" />
                                좋아요한 음악
                            </span>
                            <h1 className="text-[clamp(24px,4vw,40px)] font-extrabold leading-[1.15] tracking-[-0.035em] text-[#211C26]">
                                마음에 든 곡을
                                <br className="hidden min-[560px]:block" />
                                <span className="bg-[linear-gradient(100deg,#FF6B5E_10%,#FFB648_55%,#7B7FF0_100%)] bg-clip-text text-transparent">
                                    모아뒀어요
                                </span>
                            </h1>
                            <p className="mt-2.5 text-[14.5px] text-[#6E6678] leading-[1.7]">
                                좋아요 기록이 쌓일수록 다음 추천이 더 정확해져요.
                            </p>
                        </div>

                        <div className="flex items-center gap-2.5 pt-1 flex-wrap">
                            <div className="flex items-center gap-2 px-4 py-2.5 bg-white border border-[#E5DFD3] rounded-full">
                                <Ic d={I.heart} size={14} color="#FF6B5E" fill="#FF6B5E" />
                                <span className="text-[13px] font-bold text-[#211C26]">{tracks.length}곡</span>
                            </div>
                            <Link
                                to="/mood-input"
                                className="inline-flex items-center gap-2 h-10 px-4 rounded-full border border-[#D6CFC1] bg-white text-[#211C26] text-[13px] font-bold no-underline transition-all duration-200 hover:-translate-y-px hover:shadow-[0_6px_20px_-6px_rgba(33,28,38,0.14)]"
                            >
                                <Ic d={I.sparkles} size={13} color="#FF6B5E" />
                                추천받기
                            </Link>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="bg-white border border-dashed border-[#D6CFC1] rounded-2xl px-6 py-12 text-center">
                            <p className="text-[14px] font-semibold text-[#211C26]">좋아요한 곡을 불러오는 중이에요</p>
                            <p className="text-[12px] text-[#A39CAC] mt-1">잠시만 기다려 주세요.</p>
                        </div>
                    ) : tracks.length === 0 ? (
                        <EmptyState />
                    ) : (
                        <>

                            <div className={`fav-fu flex flex-wrap items-center gap-2.5 mb-5 ${getAnimationDelayClass(0.09)}`}>
                                <div className="flex items-center gap-1.5 flex-wrap flex-1">
                                    {MOOD_FILTERS.map((f) => (
                                        <button
                                            key={f.key}
                                            type="button"
                                            onClick={() => setActiveMood(f.key)}
                                            className={`h-8 px-3.5 rounded-full text-[12.5px] font-bold transition-all duration-150 cursor-pointer border
                                                ${
                                                    activeMood === f.key
                                                        ? 'bg-[#211C26] text-white border-[#211C26]'
                                                        : 'bg-white text-[#6E6678] border-[#E5DFD3] hover:border-[#D6CFC1] hover:text-[#211C26]'
                                                }`}
                                        >
                                            {f.label}
                                            {f.key !== 'all' && moodCounts[f.key] ? (
                                                <span className="ml-1 opacity-60">{moodCounts[f.key]}</span>
                                            ) : null}
                                        </button>
                                    ))}
                                </div>

                                <div className="relative">
                                    <Ic
                                        d={I.search}
                                        size={13}
                                        color="#A39CAC"
                                        className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                                    />
                                    <input
                                        type="text"
                                        placeholder="곡명 · 아티스트 검색"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="h-8 pl-8 pr-3 rounded-full bg-white border border-[#E5DFD3] text-[12.5px] text-[#211C26] placeholder-[#A39CAC] outline-none focus:border-[#D6CFC1] transition-colors w-[160px] min-[560px]:w-[200px]"
                                    />
                                </div>

                                <div className="flex items-center bg-white border border-[#E5DFD3] rounded-full p-[3px]">
                                    {[
                                        { mode: 'list', icon: I.list },
                                        { mode: 'compact', icon: I.grid },
                                    ].map(({ mode, icon }) => (
                                        <button
                                            key={mode}
                                            type="button"
                                            onClick={() => setViewMode(mode)}
                                            className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-150 cursor-pointer
                                                ${viewMode === mode ? 'bg-[#211C26]' : 'hover:bg-[#F1ECE3]'}`}
                                        >
                                            <Ic d={icon} size={13} color={viewMode === mode ? '#fff' : '#A39CAC'} />
                                        </button>
                                    ))}
                                </div>
                            </div>


                            {(activeMood !== 'all' || searchQuery) && (
                                <p className="text-[12.5px] text-[#A39CAC] mb-3 px-0.5">
                                    {filtered.length}개의 곡
                                    {activeMood !== 'all' && ` · ${getMoodInfo(activeMood).label}`}
                                    {searchQuery && ` · "${searchQuery}"`}
                                </p>
                            )}


                            <div className={`fav-fu ${getAnimationDelayClass(0.12)}`}>
                                {filtered.length === 0 ? (
                                    <div className="bg-white border border-[#E5DFD3] rounded-2xl px-6 py-10 text-center">
                                        <p className="text-[14px] font-semibold text-[#211C26] mb-1">
                                            검색 결과가 없어요
                                        </p>
                                        <p className="text-[13px] text-[#A39CAC]">다른 감정이나 검색어로 찾아보세요.</p>
                                    </div>
                                ) : viewMode === 'list' ? (
                                    <div className="flex flex-col gap-2.5">
                                        {filtered.map((track, index) => (
                                            <div
                                                key={track.track_id}
                                                className={`fav-fu ${getAnimationDelayClass((0.03 * index).toFixed(2))}`}
                                            >
                                                <FavoriteCard track={track} onUnlike={handleUnlike} />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 min-[560px]:grid-cols-2 min-[900px]:grid-cols-3 gap-3">
                                        {filtered.map((track, index) => (
                                            <CompactCard
                                                key={track.track_id}
                                                track={track}
                                                onUnlike={handleUnlike}
                                                index={index}
                                            />
                                        ))}
                                    </div>
                                )}
                            </div>


                            <div
                                className={`fav-fu mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#E5DFD3] bg-white px-5 py-4 ${getAnimationDelayClass(0.15)}`}
                            >
                                <span className="inline-flex items-center gap-1.5 text-[12.5px] text-[#6E6678]">
                                    <SpotifyMark size={14} />곡 정보:&nbsp;
                                    <strong className="font-bold text-[#211C26]">Provided by Spotify</strong>
                                </span>
                                <a
                                    href="https://open.spotify.com"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1ED760] text-[#191414] text-[13px] font-extrabold no-underline transition-all duration-150 hover:-translate-y-px hover:shadow-[0_6px_20px_-6px_rgba(30,215,96,0.45)]"
                                >
                                    <Ic d={I.play} size={11} color="#191414" fill="#191414" sw={0} />
                                    Spotify에서 모두 듣기
                                </a>
                            </div>


                            <div
                                className={`fav-fu mt-4 flex flex-col items-start justify-between gap-5 rounded-[24px] border border-[#E5DFD3] bg-gradient-to-br from-[#FFEAE6] via-[#FAF8F4] to-[#ECEDFD] px-6 py-7 min-[560px]:px-8 min-[560px]:py-8 min-[700px]:flex-row min-[700px]:items-center ${getAnimationDelayClass(0.18)}`}
                            >
                                <div>
                                    <p className="text-[11px] font-bold text-[#A39CAC] uppercase tracking-[0.07em] mb-1.5">
                                        좋아요 기반 추천
                                    </p>
                                    <h3 className="text-[17px] font-extrabold text-[#211C26] tracking-[-0.02em] mb-1">
                                        좋아요 {tracks.length}곡이 다음 추천에 반영돼요
                                    </h3>
                                <p className="text-[13px] text-[#6E6678] leading-[1.6]">
                                        쌓인 기록을 바탕으로 더 정확한 감정 맞춤 추천을 받아보세요.
                                    </p>
                                </div>
                                <Link
                                    to="/mood-input"
                                    className="inline-flex items-center gap-2 h-11 px-6 rounded-full bg-[#211C26] text-white text-[14px] font-bold no-underline transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_28px_-8px_rgba(33,28,38,0.30)] shrink-0"
                                >
                                    <Ic d={I.sparkles} size={14} color="#FFB648" />
                                    새 추천받기
                                    <Ic d={I.arrowR} size={14} color="#fff" />
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </main>

            <Footer />
        </div>
    );
}


function CompactCard({ track, onUnlike, index }) {
    const moodInfo = getMoodInfo(track.mood);
    const savedLabel = formatSavedAt(track.saved_at);

    const handleUnlike = () => {
        onUnlike?.(track.track_id);
    };

    return (
        <article
            className={`fav-fu bg-white border border-[#E5DFD3] rounded-2xl overflow-hidden transition-all duration-200 hover:border-[#D6CFC1] hover:shadow-[0_8px_24px_-8px_rgba(33,28,38,0.10)] hover:-translate-y-0.5 ${getAnimationDelayClass((0.03 * index).toFixed(2))}`}
        >

            <a
                href={track.spotify_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="block leading-[0]"
                aria-label={`${track.name} Spotify에서 열기`}
            >
                <div className="w-full aspect-square overflow-hidden">
                    <AlbumCover track={track} className="w-full h-full" roundedClass="rounded-none" iconSize={12} />
                </div>
            </a>

            <div className="p-3.5">
                {track.spotify_url ? (
                    <a
                        href={track.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[14px] font-bold text-[#211C26] no-underline block truncate hover:text-[#7B7FF0] transition-colors duration-150 leading-snug mb-0.5"
                    >
                        {track.name}
                    </a>
                ) : (
                    <span className="text-[14px] font-bold text-[#211C26] block truncate leading-snug mb-0.5">
                        {track.name}
                    </span>
                )}

                {track.spotify_url ? (
                    <a
                        href={track.spotify_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] text-[#6E6678] no-underline block truncate hover:text-[#211C26] transition-colors duration-150 mb-2.5"
                    >
                        {track.artist_name}
                    </a>
                ) : (
                    <span className="text-[12px] text-[#6E6678] block truncate mb-2.5">{track.artist_name}</span>
                )}

                <div className="flex items-center gap-1.5 mb-3">
                    <span
                        className={`inline-flex items-center gap-[3px] rounded-full px-2 py-[2px] text-[11px] font-semibold ${getMoodChipClass(moodInfo.soft, moodInfo.color)}`}
                    >
                        {moodInfo.label}
                    </span>
                    {savedLabel && <span className="text-[11px] text-[#A39CAC]">{savedLabel}</span>}
                </div>

                <div className="flex items-center gap-[3px] mb-3">
                    <SpotifyMark size={10} />
                    <span className="text-[10.5px] text-[#A39CAC]">Provided by Spotify</span>
                </div>

                <div className="flex items-center gap-2">
                    {track.spotify_url && (
                        <a
                            href={track.spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="Spotify에서 듣기"
                            className="flex-1 h-8 rounded-full bg-[#1ED760] flex items-center justify-center gap-1.5 no-underline transition-all duration-150 hover:brightness-105"
                        >
                            <Ic d={I.play} size={10} color="#191414" fill="#191414" sw={0} />
                            <span className="text-[11.5px] font-bold text-[#191414]">Spotify</span>
                        </a>
                    )}
                    <button
                        type="button"
                        onClick={handleUnlike}
                        aria-label="좋아요 취소"
                        className="w-8 h-8 rounded-full flex items-center justify-center border-[1.5px] border-[#FF6B5E] bg-[#FFEAE6] hover:bg-[#FF6B5E] transition-all duration-200 cursor-pointer shrink-0 group/btn"
                    >
                        <Ic
                            d={I.heart}
                            size={12}
                            color="#FF6B5E"
                            fill="#FF6B5E"
                            className="group-hover/btn:!fill-white group-hover/btn:!stroke-white"
                        />
                    </button>
                </div>
            </div>
        </article>
    );
}
