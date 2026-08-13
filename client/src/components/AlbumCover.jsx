import { useState } from 'react';

const DEFAULT_GRADIENT = 'linear-gradient(135deg, #FFEAE6 0%, #ECEDFD 55%, #FFF3DE 100%)';

const MusicNote = ({ size = 14, color = '#A39CAC' }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 18V5l12-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="18" cy="16" r="3" />
    </svg>
);

export default function AlbumCover({ track, src, title, size = 40, radius = 10, className = '' }) {
    const [imageFailed, setImageFailed] = useState(false);
    const imageUrl = src || track?.album_image_url || '';
    const albumTitle = title || track?.album_name || track?.name || '앨범';
    const hasImage = Boolean(imageUrl) && !imageFailed;
    const radiusClass = radius >= 14 ? 'rounded-[14px]' : radius >= 10 ? 'rounded-[10px]' : 'rounded-lg';
    const sizeClass = size === 64 ? 'h-16 w-16' : size === 42 ? 'h-[42px] w-[42px]' : 'h-10 w-10';
    const labelSizeClass = size === 64 ? 'text-[12px]' : size === 42 ? 'text-[10px]' : 'text-[9px]';

    return (
        <div className={`${className} ${sizeClass} shrink-0 overflow-hidden ${radiusClass} bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)]`}>
            {hasImage ? (
                <img
                    src={imageUrl}
                    alt={`${albumTitle} 앨범 커버`}
                    onError={() => setImageFailed(true)}
                    className="block h-full w-full object-cover"
                />
            ) : (
                <div className="flex h-full w-full flex-col items-center justify-center gap-[3px] bg-[linear-gradient(135deg,#FFEAE6_0%,#ECEDFD_55%,#FFF3DE_100%)] p-[6px] text-center">
                    <MusicNote size={Math.max(12, Math.floor(size * 0.3))} />
                    <span
                        className={`overflow-hidden font-bold leading-[1.1] text-[#6E6678] [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] ${labelSizeClass}`}
                    >
                        {albumTitle}
                    </span>
                </div>
            )}
        </div>
    );
}
