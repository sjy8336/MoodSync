import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getFavorites, getHealth, getMoodDashboard, removeFavorite, saveFavorite } from '../services/apiClient';
import Header from '../components/Header';
import Footer from '../components/Footer';
import FavoriteToast from '../components/FavoriteToast';
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
    waveform: 'M2 12h2M6 8v8M10 5v14M14 9v6M18 6v12M22 12h2',
    sparkles:
        'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z',
    arrowR: 'M5 12h14M12 5l7 7-7 7',
    smile: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M8 14s1.5 2 4 2 4-2 4-2',
        'M9 9h.01M15 9h.01',
    ],
    cloud: 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z',
    rain: ['M20 16.2A4.5 4.5 0 0 0 17.5 8H16.74A7 7 0 1 0 7 17.97', 'M16 20v2M8 20v2M12 20v2'],
    sparkle: 'M12 3l1.9 5.87L20 10l-5.87 1.9L12 18l-1.9-5.87L4 10l5.87-1.9z',
    sun: [
        'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
        'M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42',
    ],
    moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    play: 'M6 3l15 9-15 9V3z',
    calHeart: [
        'M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H3z',
        'M12 17a2 2 0 0 0 2-2c0-1-1-2-2-3-1 1-2 2-2 3a2 2 0 0 0 2 2z',
    ],
    check: 'M20 6 9 17l-5-5',
    bulb: [
        'M9 18h6M10 22h4M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z',
    ],
    user: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
    chevRight: 'M9 18l6-6-6-6',
    clock: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 6v6l4 2'],
    refresh: 'M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6',
    x: 'M18 6 6 18M6 6l12 12',

    flame: [
        'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z',
    ],
    meh: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M8 15h8', 'M9 9h.01M15 9h.01'],
    droplets: [
        'M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z',
        'M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97',
    ],
    target: [
        'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z',
        'M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12z',
        'M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
    ],
    coffee: ['M17 8h1a4 4 0 0 1 0 8h-1', 'M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8z', 'M6 1v3M10 1v3M14 1v3'],
    alertCirc: ['M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z', 'M12 8v4M12 16h.01'],
};


const SpotifyMark = ({ size = 16 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" className="inline-block shrink-0">
        <circle cx="12" cy="12" r="12" fill="#1ED760" />
        <path
            d="M17.5 10.7c-3-1.8-7.9-2-10.7-1.1a.7.7 0 1 1-.4-1.4c3.2-1 8.7-.8 12.1 1.2a.7.7 0 0 1-.7 1.3h-.3zm-.1 2.9c-2.5-1.5-6.3-2-9.3-1.1a.6.6 0 1 1-.3-1.1c3.4-1 7.6-.5 10.5 1.2a.6.6 0 0 1-.6 1h-.3zm-.3 2.8c-2.2-1.3-4.9-1.6-8-.9a.5.5 0 1 1-.2-1c3.4-.8 6.4-.4 8.8 1a.5.5 0 0 1-.6.9z"
            fill="white"
        />
    </svg>
);


const AlbumCover = ({ src, title, size = 64, radius = 10 }) => {
    const [failed, setFailed] = useState(false);
    const hasSrc = Boolean(src) && !failed;
    const sizeClass = size === 42 ? 'w-[42px] h-[42px]' : size === 64 ? 'w-16 h-16' : '';
    const radiusClass = radius === 10 ? 'rounded-[10px]' : radius === 12 ? 'rounded-[12px]' : 'rounded-[10px]';

    return (
        <div className={`shrink-0 overflow-hidden ${sizeClass} ${radiusClass} bg-[linear-gradient(135deg,#FFEAE6,#ECEDFD)]`}>
            {hasSrc ? (
                <img
                    src={src}
                    alt={title ? `${title} 앨범 커버` : '앨범 커버'}
                    onError={() => setFailed(true)}
                    className="w-full h-full object-cover block"
                />
            ) : (
                <div className="w-full h-full flex items-center justify-center relative bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)]">

                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.5)_0%,transparent_36%)]" />
                    <Ic
                        d={I.music}
                        size={Math.max(12, Math.round(size * 0.28))}
                        color="#A39CAC"
                        className="relative z-10"
                    />
                </div>
            )}
        </div>
    );
};


const RECENT_MOODS = [
    { day: '어제', label: '지침', icon: I.moon, color: '#7B7FF0', soft: '#ECEDFD' },
    { day: '3일 전', label: '설렘', icon: I.sparkle, color: '#FFB648', soft: '#FFF3DE' },
    { day: '5일 전', label: '기쁨', icon: I.smile, color: '#FF6B5E', soft: '#FFEAE6' },
];

const RECENT_TRACKS = [
    {
        cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
        title: 'Dynamite',
        artist: 'BTS',
        mood: '기쁨',
        moodColor: '#FF6B5E',
        spotifyUrl: 'https://open.spotify.com',
    },
    {
        cover: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
        title: 'Good Days',
        artist: 'SZA',
        mood: '설렘',
        moodColor: '#FFB648',
        spotifyUrl: 'https://open.spotify.com',
    },
    {
        cover: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80',
        title: 'Blinding Lights',
        artist: 'The Weeknd',
        mood: '활기',
        moodColor: '#FF6B5E',
        spotifyUrl: 'https://open.spotify.com',
    },
];

const TODAY_MOOD_RECORDED = {
    label: '기쁨',
    icon: I.smile,
    color: '#FF6B5E',
    soft: '#FFEAE6',
    time: '오전 9:42',
    analysis: [
        { label: '활기', pct: 72, color: '#FF6B5E' },
        { label: '편안함', pct: 45, color: '#7B7FF0' },
        { label: '설렘', pct: 58, color: '#FFB648' },
    ],
    track: {
        cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
        title: 'Dynamite',
        artist: 'BTS',
    },
};


const MOOD_STYLE_MAP = {
    happy: { label: '기쁨', icon: I.smile, color: '#9C3D33', soft: '#FFEAE6' },
    excited: { label: '설렘', icon: I.sparkle, color: '#B9791E', soft: '#FFF3DE' },
    calm: { label: '평온', icon: I.cloud, color: '#6E6678', soft: '#F1ECE3' },
    tired: { label: '피곤', icon: I.moon, color: '#6E6678', soft: '#F1ECE3' },
    sad: { label: '우울', icon: I.rain, color: '#3D3D8F', soft: '#ECEDFD' },
    anxious: { label: '불안', icon: I.alertCirc, color: '#C97EB6', soft: '#FAEAF7' },
    angry: { label: '화남', icon: I.flame, color: '#FF6B5E', soft: '#FFEAE6' },
    lonely: { label: '외로움', icon: I.droplets, color: '#7B7FF0', soft: '#ECEDFD' },
    grateful: { label: '감사', icon: I.heart, color: '#E8805A', soft: '#FFF0EC' },
    neutral: { label: '보통', icon: I.meh, color: '#A39CAC', soft: '#F1ECE3' },
    focused: { label: '집중', icon: I.target, color: '#FFB648', soft: '#FFF3DE' },
    nostalgic: { label: '그리움', icon: I.coffee, color: '#C97EB6', soft: '#FAEAF7' },
};

const getMoodVisual = (mood) =>
    MOOD_STYLE_MAP[mood] || { label: mood || '기분', icon: I.cloud, color: '#A39CAC', soft: '#F1ECE3' };

const getSoftBgClass = (soft) => {
    switch (soft) {
        case '#FFEAE6':
            return 'bg-[#FFEAE6]';
        case '#ECEDFD':
            return 'bg-[#ECEDFD]';
        case '#FFF3DE':
            return 'bg-[#FFF3DE]';
        case '#EDEAFC':
            return 'bg-[#EDEAFC]';
        case '#FAEAF7':
            return 'bg-[#FAEAF7]';
        case '#FFF0EC':
            return 'bg-[#FFF0EC]';
        case '#F1ECE3':
            return 'bg-[#F1ECE3]';
        default:
            return 'bg-[#F1ECE3]';
    }
};

const getMoodTintClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'bg-[rgba(255,107,94,0.11)] text-[#FF6B5E]';
        case '#FFB648':
            return 'bg-[rgba(255,182,72,0.11)] text-[#FFB648]';
        case '#7B7FF0':
            return 'bg-[rgba(123,127,240,0.11)] text-[#7B7FF0]';
        default:
            return 'bg-[rgba(163,156,172,0.11)] text-[#A39CAC]';
    }
};

const getMoodTintSoftClass = (soft) => {
    switch (soft) {
        case '#FFEAE6':
            return 'bg-[#FFEAE6]';
        case '#ECEDFD':
            return 'bg-[#ECEDFD]';
        case '#FFF3DE':
            return 'bg-[#FFF3DE]';
        case '#EDEAFC':
            return 'bg-[#EDEAFC]';
        case '#FAEAF7':
            return 'bg-[#FAEAF7]';
        case '#FFF0EC':
            return 'bg-[#FFF0EC]';
        default:
            return 'bg-[#F1ECE3]';
    }
};

const getTrackMoodChipClass = (color) => {
    switch (color) {
        case '#9C3D33':
            return 'bg-[#FFEAE6] text-[#9C3D33]';
        case '#B9791E':
            return 'bg-[#FFF3DE] text-[#B9791E]';
        case '#3D3D8F':
            return 'bg-[#ECEDFD] text-[#3D3D8F]';
        case '#6E6678':
            return 'bg-[#F1ECE3] text-[#6E6678]';
        case '#FF6B5E':
            return 'bg-[rgba(255,107,94,0.11)] text-[#FF6B5E]';
        case '#FFB648':
            return 'bg-[rgba(255,182,72,0.11)] text-[#FFB648]';
        case '#7B7FF0':
            return 'bg-[rgba(123,127,240,0.11)] text-[#7B7FF0]';
        default:
            return 'bg-[rgba(163,156,172,0.11)] text-[#A39CAC]';
    }
};

const getBarColorClass = (color) => {
    switch (color) {
        case '#FF6B5E':
            return 'bg-[#FF6B5E]';
        case '#FFB648':
            return 'bg-[#FFB648]';
        case '#7B7FF0':
            return 'bg-[#7B7FF0]';
        default:
            return 'bg-[#D6CFC1]';
    }
};

const getPctWidthClass = (pct) => {
    const map = {
        36: 'w-[36%]',
        40: 'w-[40%]',
        42: 'w-[42%]',
        45: 'w-[45%]',
        50: 'w-[50%]',
        58: 'w-[58%]',
        60: 'w-[60%]',
        68: 'w-[68%]',
        72: 'w-[72%]',
        76: 'w-[76%]',
        84: 'w-[84%]',
    };
    return map[pct] || 'w-0';
};

const formatTimeLabel = (value) => {
    if (!value) return '방금';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '방금';
    return date.toLocaleTimeString('ko-KR', { hour: 'numeric', minute: '2-digit' });
};

const formatRelativeDayLabel = (value) => {
    if (!value) return '오늘';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '오늘';
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diffDays = Math.round((startOfToday - startOfDate) / 86400000);
    if (diffDays <= 0) return '오늘';
    if (diffDays === 1) return '어제';
    if (diffDays < 7) return `${diffDays}일 전`;
    return date.toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
};

const buildTodayMoodCard = (todayMood, latestRecommendation) => {
    if (!todayMood) return null;
    const visual = getMoodVisual(todayMood.mood);
    const firstTrack = latestRecommendation?.tracks?.[0];
    const track = firstTrack
        ? { cover: firstTrack.album_image_url || null, title: firstTrack.name, artist: firstTrack.artist_name }
        : TODAY_MOOD_RECORDED.track;
    return {
        label: visual.label,
        icon: visual.icon,
        color: visual.color,
        soft: visual.soft,
        time: formatTimeLabel(todayMood.created_at),
        analysis: [
            { label: '현재 감정', pct: 84, color: visual.color },
            { label: '추천 매칭', pct: latestRecommendation ? 76 : 42, color: '#FFB648' },
            { label: 'Spotify', pct: latestRecommendation ? 68 : 36, color: '#7B7FF0' },
        ],
        track,
    };
};

const buildRecentMoodItems = (moodRecords) =>
    moodRecords.map((item) => {
        const visual = getMoodVisual(item.mood);
        return {
            day: formatRelativeDayLabel(item.created_at),
            label: visual.label,
            icon: visual.icon,
            color: visual.color,
            soft: visual.soft,
        };
    });

const buildRecentTrackItems = (recommendation) => {
    const moodVisual = getMoodVisual(recommendation?.mood);
    return (recommendation?.tracks || []).map((track) => ({
        trackId: track.track_id,
        cover: track.album_image_url || null,
        title: track.name,
        artist: track.artist_name,
        mood: moodVisual.label,
        moodKey: recommendation?.mood || null,
        moodColor: moodVisual.color,
        albumName: track.album_name || null,
        durationMs: track.duration_ms || null,
        reason: track.reason || null,
        spotifyUrl: track.spotify_url || 'https://open.spotify.com',
    }));
};


const DEMO_HOME_SNAPSHOTS = {
    focus: {
        todayMood: {
            label: '집중',
            icon: I.target,
            color: '#FFB648',
            soft: '#FFF3DE',
            time: '오전 10:12',
            analysis: [
                { label: '집중력', pct: 84, color: '#FFB648' },
                { label: '편안함', pct: 58, color: '#7B7FF0' },
                { label: '몰입', pct: 76, color: '#FF6B5E' },
            ],
            track: {
                cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
                title: 'Take Five',
                artist: 'The Dave Brubeck Quartet',
            },
        },
        recentMoods: [
            { day: '오늘', label: '집중', icon: I.target, color: '#FFB648', soft: '#FFF3DE' },
            { day: '어제', label: '평온', icon: I.cloud, color: '#7B7FF0', soft: '#ECEDFD' },
            { day: '3일 전', label: '집중', icon: I.target, color: '#FFB648', soft: '#FFF3DE' },
        ],
        recentTracks: [
            {
                trackId: 'demo-focus-1',
                cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
                title: 'Take Five',
                artist: 'The Dave Brubeck Quartet',
                mood: '집중',
                moodKey: 'focused',
                moodColor: '#FFB648',
                albumName: 'Time Out',
                durationMs: 324000,
                reason: '재즈 특유의 리듬감이 또렷하면서도 비교적 안정적으로 이어지는 곡이에요. 너무 조용하지 않은 음악을 들으며 집중하고 싶을 때 잘 맞아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-focus-2',
                cover: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80',
                title: 'Blue in Green',
                artist: 'Miles Davis',
                mood: '집중',
                moodKey: 'focused',
                moodColor: '#FFB648',
                albumName: 'Kind of Blue',
                durationMs: 337000,
                reason: '차분하고 여유로운 피아노와 트럼펫의 분위기가 이어지는 곡이에요. 생각이 많을 때 배경을 복잡하게 만들지 않는 음악을 듣고 싶다면 잘 어울려요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-focus-3',
                cover: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80',
                title: 'Cantaloupe Island',
                artist: 'Herbie Hancock',
                mood: '집중',
                moodKey: 'focused',
                moodColor: '#FFB648',
                albumName: 'Empyrean Isles',
                durationMs: 308000,
                reason: '재즈의 그루브와 반복되는 리듬이 비교적 선명하게 느껴지는 곡이에요. 집중하는 흐름에 약간의 활기를 더하고 싶을 때 듣기 좋아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
        ],
    },
    jazz: {
        todayMood: {
            label: '재즈',
            icon: I.music,
            color: '#7B7FF0',
            soft: '#ECEDFD',
            time: '오후 2:18',
            analysis: [
                { label: '스윙', pct: 76, color: '#FFB648' },
                { label: '여유', pct: 68, color: '#7B7FF0' },
                { label: '활기', pct: 61, color: '#FF6B5E' },
            ],
            track: {
                cover: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
                title: 'Blue Bossa',
                artist: 'Joe Henderson',
            },
        },
        recentMoods: [
            { day: '오늘', label: '집중', icon: I.target, color: '#FFB648', soft: '#FFF3DE' },
            { day: '어제', label: '설렘', icon: I.sparkle, color: '#FF6B5E', soft: '#FFEAE6' },
            { day: '3일 전', label: '평온', icon: I.cloud, color: '#7B7FF0', soft: '#ECEDFD' },
        ],
        recentTracks: [
            {
                trackId: 'demo-jazz-1',
                cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
                title: 'Sing, Sing, Sing',
                artist: 'Benny Goodman',
                mood: '재즈',
                moodKey: 'jazz',
                moodColor: '#7B7FF0',
                albumName: 'The Essential Benny Goodman',
                durationMs: 515000,
                reason: '큰 편성의 스윙 리듬과 브라스가 밝고 활기차게 느껴지는 곡이에요. 지친 기분을 가볍게 환기하며 재즈를 듣고 싶을 때 잘 맞아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-jazz-2',
                cover: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=200&q=80',
                title: 'Blue Bossa',
                artist: 'Joe Henderson',
                mood: '재즈',
                moodKey: 'jazz',
                moodColor: '#7B7FF0',
                albumName: 'Page One',
                durationMs: 250000,
                reason: '보사노바의 여유로운 리듬과 재즈의 즉흥적인 결이 함께 느껴지는 곡이에요. 복잡하지 않은 분위기에서 잠시 숨을 고르고 싶을 때 어울려요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-jazz-3',
                cover: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80',
                title: 'Birdland',
                artist: 'Weather Report',
                mood: '재즈',
                moodKey: 'jazz',
                moodColor: '#7B7FF0',
                albumName: 'Heavy Weather',
                durationMs: 355000,
                reason: '록에 가까운 추진력과 재즈의 복잡한 앙상블이 함께 느껴지는 퓨전 재즈 곡이에요. 차분한 곡만 이어 듣기보다 조금 더 선명한 변화를 원할 때 듣기 좋아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
        ],
    },
    drive: {
        todayMood: {
            label: '설렘',
            icon: I.sparkle,
            color: '#FF6B5E',
            soft: '#FFEAE6',
            time: '오후 4:20',
            analysis: [
                { label: '에너지', pct: 91, color: '#FF6B5E' },
                { label: '리듬감', pct: 85, color: '#FFB648' },
                { label: '기분 전환', pct: 78, color: '#7B7FF0' },
            ],
            track: {
                cover: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80',
                title: 'Shut Up and Dance',
                artist: 'WALK THE MOON',
            },
        },
        recentMoods: [
            { day: '오늘', label: '설렘', icon: I.sparkle, color: '#FF6B5E', soft: '#FFEAE6' },
            { day: '어제', label: '기쁨', icon: I.smile, color: '#FF6B5E', soft: '#FFEAE6' },
            { day: '3일 전', label: '설렘', icon: I.sparkle, color: '#FFB648', soft: '#FFF3DE' },
        ],
        recentTracks: [
            {
                trackId: 'demo-drive-1',
                cover: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=200&q=80',
                title: 'Shut Up and Dance',
                artist: 'WALK THE MOON',
                mood: '드라이브',
                moodKey: 'excited',
                moodColor: '#FF6B5E',
                albumName: 'TALKING IS HARD',
                durationMs: 199000,
                reason: '밝은 기타 리프와 반복되는 팝 록 후렴이 경쾌하게 이어지는 곡이에요. 이동을 시작하며 분위기를 가볍게 띄우고 싶을 때 잘 맞아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-drive-2',
                cover: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=200&q=80',
                title: 'Uptown Funk',
                artist: 'Mark Ronson ft. Bruno Mars',
                mood: '드라이브',
                moodKey: 'excited',
                moodColor: '#FF6B5E',
                albumName: 'Uptown Special',
                durationMs: 270000,
                reason: '펑키한 베이스와 타이트한 리듬이 선명하게 느껴지는 곡이에요. 함께 듣는 사람들과 차 안의 분위기를 생생하게 만들고 싶을 때 어울려요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-drive-3',
                cover: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&q=80',
                title: 'Blinding Lights',
                artist: 'The Weeknd',
                mood: '드라이브',
                moodKey: 'excited',
                moodColor: '#FF6B5E',
                albumName: 'After Hours',
                durationMs: 200000,
                reason: '반복되는 신스팝 비트와 복고적인 질감이 강하게 드러나는 곡이에요. 익숙한 리듬을 따라가며 이동 시간을 즐기고 싶을 때 듣기 좋아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
        ],
    },
    dreamy: {
        todayMood: {
            label: '몽환',
            icon: I.smile,
            color: '#FFB648',
            soft: '#FFF3DE',
            time: '오후 10:18',
            analysis: [
                { label: '공간감', pct: 88, color: '#7B7FF0' },
                { label: '신비로움', pct: 82, color: '#C97EB6' },
                { label: '몰입', pct: 75, color: '#FFB648' },
            ],
            track: {
                cover: 'https://images.unsplash.com/photo-1470225636490-405e5d1b5c9b?w=200&q=80',
                title: 'Midnight City',
                artist: 'M83',
            },
        },
        recentMoods: [
            { day: '오늘', label: '몽환', icon: I.sparkle, color: '#7B7FF0', soft: '#ECEDFD' },
            { day: '어제', label: '설렘', icon: I.sparkle, color: '#FF6B5E', soft: '#FFEAE6' },
            { day: '3일 전', label: '몽환', icon: I.sparkle, color: '#C97EB6', soft: '#FAEAF7' },
        ],
        recentTracks: [
            {
                trackId: 'demo-dreamy-1',
                cover: 'https://images.unsplash.com/photo-1470225636490-405e5d1b5c9b?w=200&q=80',
                title: 'Midnight City',
                artist: 'M83',
                mood: '몽환',
                moodKey: 'excited',
                moodColor: '#7B7FF0',
                albumName: "Hurry Up, We're Dreaming",
                durationMs: 244000,
                reason: '반짝이는 신스 사운드와 반복되는 리듬이 도시적인 몽환을 만들어내는 곡이에요. 현실의 속도에서 잠시 벗어난 듯한 음악을 듣고 싶을 때 잘 맞아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-dreamy-2',
                cover: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=200&q=80',
                title: 'Enjoy the Silence',
                artist: 'Depeche Mode',
                mood: '몽환',
                moodKey: 'calm',
                moodColor: '#7B7FF0',
                albumName: 'Violator',
                durationMs: 252000,
                reason: '어두운 신스 질감과 절제된 반복 비트가 차분하게 이어지는 곡이에요. 말없이 분위기에 머물며 음악을 듣고 싶을 때 어울려요.',
                spotifyUrl: 'https://open.spotify.com',
            },
            {
                trackId: 'demo-dreamy-3',
                cover: 'https://images.unsplash.com/photo-1516280440614-37939bbacd81?w=200&q=80',
                title: 'Sweet Disposition',
                artist: 'The Temper Trap',
                mood: '몽환',
                moodKey: 'excited',
                moodColor: '#7B7FF0',
                albumName: 'Conditions',
                durationMs: 231000,
                reason: '점층적으로 커지는 기타와 넓게 펼쳐지는 보컬이 인상적인 곡이에요. 한 장면처럼 천천히 분위기가 변하는 음악을 원할 때 듣기 좋아요.',
                spotifyUrl: 'https://open.spotify.com',
            },
        ],
    },
};

const getDemoHomeSnapshot = (preset) => DEMO_HOME_SNAPSHOTS[preset] || DEMO_HOME_SNAPSHOTS.focus;


const getTodayString = () => {
    const d = new Date();
    return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
};


const TrackCard = ({ track, onLike, onUnlike, initialLiked = false }) => {
    const [liked, setLiked] = useState(false);
    const [hov, setHov] = useState(false);
    const favoriteTrackId = track.trackId || `${track.title}-${track.artist}`;

    useEffect(() => {
        setLiked(Boolean(initialLiked));
    }, [initialLiked]);

    const spotifyUrl = track.spotifyUrl || 'https://open.spotify.com';
    const favoritePayload = {
        track_id: favoriteTrackId,
        track_name: track.title,
        artist_name: track.artist,
        album_name: track.albumName || null,
        album_image_url: track.cover || null,
        spotify_url: track.spotifyUrl || null,
        duration_ms: track.durationMs || null,
        mood: track.moodKey || null,
        reason: track.reason || null,
    };

    const handleLikeToggle = async () => {
        try {
            if (liked) {
                await removeFavorite(favoriteTrackId);
                setLiked(false);
                onUnlike?.(favoriteTrackId);
            } else {
                await saveFavorite(favoritePayload);
                setLiked(true);
                onLike?.(favoriteTrackId);
            }
        } catch (error) {
            console.error('좋아요 상태를 저장하지 못했어요.', error);
        }
    };

    return (
        <div
            className={[
                'bg-white border rounded-2xl overflow-hidden transition-all duration-200',
                hov
                    ? 'border-[#D6CFC1] shadow-[0_8px_28px_-10px_rgba(33,28,38,0.13)] -translate-y-0.5'
                    : 'border-[#E5DFD3]',
            ].join(' ')}
            onMouseEnter={() => setHov(true)}
            onMouseLeave={() => setHov(false)}
        >
            <div className="flex items-stretch">

                <a
                    href={spotifyUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block shrink-0 leading-none p-3"
                    aria-label={`${track.title} Spotify에서 열기`}
                >
                    <AlbumCover src={track.cover} title={track.title} size={64} radius={10} />
                </a>


                <div className="flex-1 min-w-0 flex flex-col justify-center gap-[3px] pr-3 py-3">

                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[14px] font-bold text-[#211C26] no-underline truncate block leading-tight tracking-[-0.01em]"
                    >
                        {track.title}
                    </a>

                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] text-[#6E6678] no-underline block"
                    >
                        {track.artist}
                    </a>

                    <div className="flex items-center gap-2 mt-[2px]">
                        <span
                            className={`text-[11px] font-semibold px-[8px] py-[2px] rounded-full ${getTrackMoodChipClass(
                                track.moodColor,
                            )}`}
                        >
                            {track.mood}
                        </span>

                        <span className="flex items-center gap-[3px] text-[10.5px] text-[#A39CAC]">
                            <SpotifyMark size={10} /> Provided by Spotify
                        </span>
                    </div>
                </div>


                <div className="flex flex-col items-center justify-center gap-2 pr-3 shrink-0">
                    <button
                        onClick={handleLikeToggle}
                        aria-label={liked ? '좋아요 취소' : '좋아요'}
                        className={[
                            'w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 border cursor-pointer',
                            liked
                                ? 'border-[#FF6B5E] bg-[#FFEAE6] hover:bg-[#FF6B5E]'
                                : 'border-[#E5DFD3] bg-transparent hover:border-[#FF6B5E]',
                        ].join(' ')}
                    >
                        <Ic
                            d={I.heart}
                            size={13}
                            color={liked ? '#FF6B5E' : '#A39CAC'}
                            fill={liked ? '#FF6B5E' : 'none'}
                        />
                    </button>

                    <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label="Spotify에서 듣기"
                        className="w-8 h-8 rounded-full flex items-center justify-center bg-[#1ED760] hover:brightness-110 transition-all duration-150"
                    >
                        <Ic d={I.play} size={11} color="#191414" fill="#191414" sw={0} />
                    </a>
                </div>
            </div>


            <div className="flex items-center gap-2 px-4 py-[8px] border-t border-[#EEEBE4]">
                <Ic d={I.bulb} size={12} color="#7B7FF0" className="shrink-0 mt-[1px]" />
                <p className="text-[11.5px] text-[#A39CAC] leading-snug m-0">
                    {track.reason || `${track.mood} 감정에 맞춰 지금 분위기와 어울리는 곡으로 골랐어요.`}
                </p>
            </div>
        </div>
    );
};


const TodayMoodCard = ({ recorded }) => {
    if (!recorded) {
        return (
            <div className="bg-white border border-[#E5DFD3] rounded-3xl p-6 shadow-[0_20px_60px_-20px_rgba(33,28,38,0.13)]">
                <div className="flex items-center justify-between mb-4">
                    <p className="text-[11px] font-bold text-[#A39CAC] uppercase tracking-[0.07em]">오늘의 감정</p>
                    <span className="text-[11px] text-[#A39CAC]">미기록</span>
                </div>

                <Link to="/mood-input" className="group block no-underline mb-5">
                    <div className="flex flex-col items-center justify-center py-6 gap-3 rounded-2xl border border-dashed border-[#E5DFD3] group-hover:border-[#D6CFC1] group-hover:bg-[#FAF8F4] transition-all duration-200">

                        <div className="w-[52px] h-[52px] rounded-2xl flex items-center justify-center transition-transform duration-200 group-hover:scale-105 bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_100%)]">
                            <Ic d={I.sparkles} size={24} color="#FF6B5E" sw={1.6} />
                        </div>
                        <div className="text-center">
                            <p className="text-[13px] font-semibold text-[#211C26] leading-tight mb-[3px]">
                                아직 오늘 감정을 기록하지 않았어요
                            </p>
                            <p className="text-[12px] text-[#A39CAC] flex items-center justify-center gap-1">
                                지금 기분을 선택해보세요
                                <Ic d={I.chevRight} size={12} color="#A39CAC" />
                            </p>
                        </div>
                    </div>
                </Link>


                <div aria-hidden="true" className="opacity-40 select-none pointer-events-none">
                    <p className="text-[10.5px] font-semibold text-[#A39CAC] mb-[10px]">기록하면 이렇게 분석돼요</p>
                    <div className="flex flex-col gap-[9px]">
                        {[
                            { label: '활기', pct: 60 },
                            { label: '편안함', pct: 40 },
                            { label: '설렘', pct: 50 },
                        ].map((a) => (
                            <div key={a.label} className="flex items-center gap-[10px]">
                                <span className="text-[11.5px] text-[#A39CAC] w-[42px] shrink-0">{a.label}</span>
                                <div className="flex-1 h-[6px] rounded-full bg-[#F1ECE3] overflow-hidden">
                                    <div className={`h-full rounded-full bg-[#D6CFC1] ${getPctWidthClass(a.pct)}`} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }


    return (
        <div className="bg-white border border-[#E5DFD3] rounded-3xl p-6 shadow-[0_20px_60px_-20px_rgba(33,28,38,0.13)]">
            <div className="flex items-center justify-between mb-5">
                <p className="text-[11px] font-bold text-[#A39CAC] uppercase tracking-[0.07em]">오늘의 감정</p>
                <span className="flex items-center gap-1 text-[11px] text-[#A39CAC]">
                    <Ic d={I.check} size={11} color="#1ED760" sw={2.4} />
                    {recorded.time} 기록됨
                </span>
            </div>


            <div className="flex items-center gap-3 mb-6">
                <div
                    className={`w-[48px] h-[48px] rounded-2xl flex items-center justify-center shrink-0 ${getMoodTintSoftClass(
                        recorded.soft,
                    )}`}
                >
                    <Ic d={recorded.icon} size={24} color={recorded.color} />
                </div>
                <div>
                    <p className="text-[17px] font-extrabold text-[#211C26] tracking-[-0.01em] leading-tight">
                        {recorded.label}
                    </p>
                    <p className="text-[11.5px] text-[#A39CAC] mt-[2px]">오늘의 감정 분석</p>
                </div>
            </div>


            <div className="flex flex-col gap-[10px] mb-6">
                {recorded.analysis.map((a) => (
                    <div key={a.label} className="flex items-center gap-3">
                        <span className="text-[11.5px] text-[#6E6678] w-[48px] shrink-0 whitespace-nowrap">
                            {a.label}
                        </span>
                            <div className="flex-1 h-[6px] rounded-full bg-[#F1ECE3] overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${getPctWidthClass(
                                        a.pct,
                                    )} ${getBarColorClass(a.color)}`}
                                />
                            </div>
                        <span className="text-[11px] text-[#A39CAC] w-[28px] text-right shrink-0">{a.pct}%</span>
                    </div>
                ))}
            </div>


            <p className="text-[10.5px] font-semibold text-[#A39CAC] mb-[8px]">오늘의 추천곡</p>
            <Link
                to="/recommendations"
                className="flex items-center gap-3 bg-[#F1ECE3] hover:bg-[#ECE6D9] rounded-2xl p-[10px] no-underline transition-colors duration-150 mb-2"
            >
                <AlbumCover src={recorded.track.cover} title={recorded.track.title} size={42} radius={10} />
                <div className="flex-1 min-w-0">
                    <p className="text-[12.5px] font-bold text-[#211C26] truncate leading-tight">
                        {recorded.track.title}
                    </p>
                    <p className="text-[11px] text-[#A39CAC] truncate mt-[1px]">{recorded.track.artist}</p>
                </div>
                <Ic d={I.chevRight} size={14} color="#A39CAC" className="shrink-0" />
            </Link>


            <Link
                to="/mood-input"
                className="flex items-center justify-center gap-[6px] w-full no-underline text-[11.5px] font-medium text-[#A39CAC] hover:text-[#6E6678] pt-3 transition-colors duration-150"
            >
                <Ic d={I.refresh} size={11} color="currentColor" />
                오늘 감정 다시 기록하기
            </Link>
        </div>
    );
};


export default function HomePage() {
    const { user } = useAuth();
    const [health, setHealth] = useState(null);
    const [error, setError] = useState('');
    const [summary, setSummary] = useState(null);
    const [summaryLoaded, setSummaryLoaded] = useState(false);
    const [summaryError, setSummaryError] = useState('');
    const [favoriteIds, setFavoriteIds] = useState(new Set());
    const [toastVisible, setToastVisible] = useState(false);
    const [toastMessage, setToastMessage] = useState('좋아요가 취소되었어요');
    const [toastTimer, setToastTimer] = useState(null);

    const today = getTodayString();
    const displayName =
        user?.displayName ||
        user?.display_name ||
        user?.email ||
        user?.providerUserId ||
        user?.provider_user_id ||
        'Spotify 사용자';
    const isDemoUser = user?.auth_provider === 'demo';
    const demoPresetKey = (user?.providerUserId || user?.provider_user_id || '').split(':')[1] || 'focus';
    const demoPresetLabel = {
        focus: '집중 테스트',
        jazz: '재즈 테스트',
        drive: '드라이브 테스트',
        dreamy: '몽환 테스트',
    }[demoPresetKey] || '데모';
    const demoHomeSnapshot = isDemoUser ? getDemoHomeSnapshot(demoPresetKey) : null;

    const todayMood = summaryLoaded
        ? buildTodayMoodCard(summary?.today_mood, summary?.latest_recommendation)
        : demoHomeSnapshot?.todayMood || TODAY_MOOD_RECORDED;
    const recentMoods = summaryLoaded
        ? buildRecentMoodItems(summary?.recent_moods || [])
        : demoHomeSnapshot?.recentMoods || RECENT_MOODS;
    const recentTracks = summaryLoaded
        ? buildRecentTrackItems(summary?.latest_recommendation)
        : demoHomeSnapshot?.recentTracks || RECENT_TRACKS;

    const showFavoriteToast = (message) => {
        setToastMessage(message);
        setToastVisible(true);
        if (toastTimer) clearTimeout(toastTimer);
        const timer = setTimeout(() => setToastVisible(false), 2800);
        setToastTimer(timer);
    };

    const handleUnlike = (trackId) => {
        setFavoriteIds((prev) => {
            const next = new Set(prev);
            next.delete(trackId);
            return next;
        });
        showFavoriteToast('좋아요가 취소되었어요');
    };

    const handleLike = (trackId) => {
        setFavoriteIds((prev) => {
            const next = new Set(prev);
            next.add(trackId);
            return next;
        });
        showFavoriteToast('좋아요에 추가되었어요');
    };

    useEffect(
        () => () => {
            if (toastTimer) clearTimeout(toastTimer);
        },
        [toastTimer]
    );

    useEffect(() => {
        let active = true;

        getHealth()
            .then((data) => {
                if (active) setHealth(data);
            })
            .catch((err) => {
                if (active) setError(err.message || '헬스체크 요청 실패');
            });

        getMoodDashboard()
            .then((data) => {
                if (active) setSummary(data);
            })
            .catch((err) => {
                if (active) setSummaryError(err.message || '홈 요약을 불러오지 못했어요');
            })
            .finally(() => {
                if (active) setSummaryLoaded(true);
            });

        getFavorites()
            .then((data) => {
                if (!active) return;
                const items = Array.isArray(data) ? data : data?.items || [];
                setFavoriteIds(new Set(items.map((item) => item.track_id)));
            })
            .catch(() => {
                if (active) setFavoriteIds(new Set());
            });

        return () => {
            active = false;
        };
    }, []);

    return (
        <div className="min-h-screen bg-[#FAF8F4] font-[Pretendard,system-ui,sans-serif] antialiased overflow-x-hidden">

            <FavoriteToast visible={toastVisible} message={toastMessage} onClose={() => setToastVisible(false)} />

            <Header />

            <main className="max-w-[1240px] mx-auto px-5 sm:px-7 md:px-10 pt-24 md:pt-28 pb-20">

                {error && (
                    <div className="mt-4 px-4 py-3 bg-[#FFEAE6] border border-[rgba(255,107,94,0.22)] rounded-xl text-[12.5px] text-[#8B2218]">
                        {error}
                    </div>
                )}
                {summaryError && (
                    <div className="mt-4 px-4 py-3 bg-[#FFF3DE] border border-[rgba(255,184,70,0.22)] rounded-xl text-[12.5px] text-[#7A5010]">
                        {summaryError}
                    </div>
                )}


                <section className="relative pt-12 pb-12 md:pt-16 md:pb-16">

                    <div aria-hidden="true" className="absolute inset-0 pointer-events-none overflow-hidden -z-10">
                        <div
                            className="absolute -top-[10%] -right-[8%] w-[380px] h-[380px] rounded-full bg-[radial-gradient(circle,rgba(255,107,94,0.12)_0%,transparent_70%)] [animation:ms-orb_10s_ease-in-out_infinite]"
                        />
                        <div
                            className="absolute bottom-0 -left-[10%] w-[340px] h-[340px] rounded-full bg-[radial-gradient(circle,rgba(123,127,240,0.10)_0%,transparent_70%)] [animation:ms-orb_13s_ease-in-out_infinite_reverse] [animation-delay:-4s]"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-[1fr_328px] gap-8 md:gap-10 items-start">

                        <div>
                            {isDemoUser && (
                                <div className="ms-fu mb-5 rounded-[22px] border border-[#C7C9FA] bg-[#F2F3FF] px-4 py-4 shadow-[0_10px_30px_-18px_rgba(123,127,240,0.5)] [animation-delay:0.03s]">
                                    <div className="flex flex-wrap items-center gap-2 mb-2">
                                        <span className="inline-flex items-center rounded-full bg-[#7B7FF0] px-3 py-[6px] text-[12px] font-bold text-white">
                                            DEMO
                                        </span>
                                        <span className="text-[12.5px] font-semibold text-[#4B4FD0]">
                                            {demoPresetLabel}
                                        </span>
                                    </div>
                                    <p className="text-[13.5px] leading-[1.7] text-[#4B4FD0] m-0">
                                        샘플 감정 기록, 추천 음악, 좋아요 데이터가 미리 채워져 있어요.
                                        <br />
                                        감정 기록하기를 눌러 실제 추천 흐름도 바로 테스트해보세요.
                                    </p>
                                </div>
                            )}

                            <div className="ms-fu inline-flex items-center gap-[6px] text-[12px] font-semibold text-[#6E6678] bg-white border border-[#E5DFD3] rounded-full px-[12px] py-[5px] mb-6 shadow-[0_2px_8px_rgba(33,28,38,0.05)] [animation-delay:0.05s]">
                                <Ic d={I.clock} size={12} color="#A39CAC" />
                                {today}
                            </div>


                            <h1 className="ms-fu text-[clamp(28px,5vw,48px)] font-extrabold tracking-[-0.035em] leading-[1.2] text-[#211C26] mb-3 [animation-delay:0.12s]">
                                안녕하세요,{' '}
                                <span className="bg-[linear-gradient(110deg,#FF6B5E_0%,#FFB648_50%,#7B7FF0_100%)] bg-clip-text text-transparent">
                                    {displayName}
                                </span>
                                님.
                            </h1>

                            <p className="ms-fu text-[17px] text-[#6E6678] leading-[1.65] mb-8 max-w-[420px] [animation-delay:0.2s]">
                                오늘은 어떤 기분이신가요?
                                <br />
                                감정을 고르면 그 순간에 맞는 음악을 찾아드려요.
                            </p>


                            <div className="ms-fu flex flex-col sm:flex-row gap-3 [animation-delay:0.32s]">
                                <Link
                                    to="/mood-input"
                                    className="group inline-flex items-center justify-center gap-[9px] no-underline
                                               bg-[#211C26] text-white text-[15.5px] font-extrabold tracking-[-0.01em]
                                               px-7 py-[15px] rounded-2xl
                                               shadow-[0_4px_16px_rgba(33,28,38,0.14)]
                                               transition-all duration-[220ms] [transition-timing-function:cubic-bezier(0.34,1.56,0.64,1)]
                                               hover:-translate-y-[3px] hover:shadow-[0_16px_40px_-12px_rgba(33,28,38,0.35)]"
                                >
                                    <Ic d={I.sparkles} size={16} color="#FFB648" />
                                    감정 기록하기
                                    <Ic d={I.arrowR} size={14} color="#fff" sw={2.2} />
                                </Link>
                                <Link
                                    to="/recommendations"
                                    className="inline-flex items-center justify-center gap-2 no-underline
                                               text-[14.5px] font-semibold text-[#6E6678]
                                               px-5 py-[15px] rounded-2xl
                                               border border-[#D6CFC1] bg-white
                                               hover:border-[#211C26] hover:text-[#211C26]
                                               transition-all duration-150"
                                >
                                    <Ic d={I.music} size={15} color="currentColor" />
                                    추천 음악 보기
                                </Link>
                            </div>
                        </div>


                        <div className="ms-fu w-full md:w-[340px] shrink-0 [animation-delay:0.3s]">
                            <TodayMoodCard recorded={todayMood} />
                        </div>
                    </div>
                </section>


                <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 mt-5">

                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-[15px] font-bold text-[#211C26] flex items-center gap-2">
                                <Ic d={I.calHeart} size={15} color="#7B7FF0" />
                                최근 감정
                            </h2>
                            <Link
                                to="/history"
                                className="text-[12.5px] font-semibold text-[#A39CAC] hover:text-[#6E6678] no-underline flex items-center gap-[3px] transition-colors duration-150"
                            >
                                전체 보기
                                <Ic d={I.chevRight} size={12} color="currentColor" />
                            </Link>
                        </div>

                        <div className="flex flex-col gap-3">
                            {recentMoods.length > 0 ? (
                                recentMoods.map((m, index) => (
                                    <Link
                                        key={`${m.day}-${m.label}-${index}`}
                                        to="/history"
                                        className="group flex items-center gap-4 bg-white border border-[#E5DFD3] hover:border-[#D6CFC1] rounded-2xl px-4 py-3 no-underline transition-all duration-200 hover:-translate-y-[1px] hover:shadow-[0_4px_16px_-6px_rgba(33,28,38,0.10)]"
                                    >
                                        <div className={`w-[40px] h-[40px] rounded-[12px] flex items-center justify-center shrink-0 ${getSoftBgClass(m.soft)}`}>
                                            <Ic d={m.icon} size={18} color={m.color} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[13.5px] font-bold text-[#211C26] mb-[1px]">{m.label}</p>
                                            <p className="text-[12px] text-[#A39CAC]">{m.day}</p>
                                        </div>
                                        <Ic
                                            d={I.chevRight}
                                            size={14}
                                            color="#D6CFC1"
                                            className="group-hover:text-[#A39CAC] transition-colors duration-150"
                                        />
                                    </Link>
                                ))
                            ) : (
                                <div className="rounded-2xl border border-dashed border-[#D6CFC1] bg-white px-4 py-6 text-center">
                                    <p className="text-[13px] font-semibold text-[#211C26]">
                                        아직 기록한 감정이 없어요
                                    </p>
                                    <p className="text-[12px] text-[#A39CAC] mt-1">
                                        첫 감정을 남기면 여기서 최근 기록을 볼 수 있어요.
                                    </p>
                                </div>
                            )}

                            <Link
                                to="/mood-input"
                                className="flex items-center justify-center gap-2 bg-[#F1ECE3] hover:bg-[#E5DFD3] border border-dashed border-[#D6CFC1] rounded-2xl px-4 py-3 no-underline transition-all duration-150"
                            >
                                <Ic d={I.sparkles} size={13} color="#A39CAC" />
                                <span className="text-[12.5px] font-semibold text-[#A39CAC]">오늘 감정 기록하기</span>
                            </Link>
                        </div>
                    </section>


                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-[15px] font-bold text-[#211C26] flex items-center gap-2">
                                <Ic d={I.music} size={15} color="#FF6B5E" />
                                최근 추천 음악
                            </h2>
                            <Link
                                to="/recommendations"
                                className="text-[12.5px] font-semibold text-[#A39CAC] hover:text-[#6E6678] no-underline flex items-center gap-[3px] transition-colors duration-150"
                            >
                                전체 보기
                                <Ic d={I.chevRight} size={12} color="currentColor" />
                            </Link>
                        </div>

                        <div className="flex flex-col gap-3">
                            {recentTracks.length > 0 ? (
                                recentTracks.map((t) => (
                                    <TrackCard
                                        key={t.trackId || `${t.title}-${t.artist}`}
                                        track={t}
                                        onLike={handleLike}
                                        initialLiked={favoriteIds.has(t.trackId || `${t.title}-${t.artist}`)}
                                        onUnlike={handleUnlike}
                                    />
                                ))
                            ) : (
                                <div className="rounded-2xl border border-dashed border-[#D6CFC1] bg-white px-4 py-6">
                                    <p className="text-[13px] font-semibold text-[#211C26]">
                                        아직 추천받은 곡이 없어요
                                    </p>
                                    <p className="text-[12px] text-[#A39CAC] mt-1">
                                        감정을 기록하면 Spotify 추천 결과가 여기에 쌓입니다.
                                    </p>
                                </div>
                            )}
                        </div>


                        <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#E5DFD3] flex-wrap gap-3">
                            <a
                                href="https://open.spotify.com"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-[6px] text-[11.5px] font-semibold text-[#A39CAC] no-underline hover:text-[#6E6678] transition-colors duration-150"
                            >
                                <SpotifyMark size={14} />곡 정보:{' '}
                                <strong className="text-[#6E6678] font-bold ml-1">Provided by Spotify</strong>
                            </a>
                            <Link
                                to="/favorites"
                                className="flex items-center gap-[5px] text-[12px] font-semibold text-[#6E6678] no-underline hover:text-[#211C26] transition-colors duration-150"
                            >
                                <Ic d={I.heart} size={12} color="#FF6B5E" fill="#FF6B5E" sw={0} />
                                좋아요한 곡 보기
                            </Link>
                        </div>
                    </section>
                </div>


                <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-[#E5DFD3] z-40 flex">
                    {[
                        { to: '/', label: '홈', icon: I.waveform },
                        { to: '/mood-input', label: '기록', icon: I.sparkles },
                        { to: '/recommendations', label: '추천', icon: I.music },
                        { to: '/history', label: '히스토리', icon: I.calHeart },
                        { to: '/my', label: '마이', icon: I.user },
                    ].map(({ to, label, icon }) => (
                        <Link
                            key={to}
                            to={to}
                            className="flex-1 flex flex-col items-center gap-[3px] py-[10px] no-underline text-[#A39CAC] hover:text-[#211C26] transition-colors duration-150"
                        >
                            <Ic d={icon} size={20} color="currentColor" />
                            <span className="text-[10px] font-semibold">{label}</span>
                        </Link>
                    ))}
                </nav>

                <div className="md:hidden h-[64px]" />
            </main>

            <Footer
                wrap={{
                    width: '100%',
                    maxWidth: '1240px',
                    margin: '0 auto',
                    padding: '0 20px',
                }}
            />
        </div>
    );
}
