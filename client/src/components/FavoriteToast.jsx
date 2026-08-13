const Ic = ({ d, size = 20, color = 'currentColor', fill = 'none', sw = 1.8 }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill={fill}
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="inline-block shrink-0 align-middle"
    >
        {(Array.isArray(d) ? d : [d]).map((p, i) => (
            <path key={i} d={p} />
        ))}
    </svg>
);

const I = {
    heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    x: 'M18 6 6 18M6 6l12 12',
};

export default function FavoriteToast({ visible, onClose, message = '좋아요가 취소되었어요' }) {
    return (
        <div
            className={`fixed bottom-7 left-1/2 z-[9999] flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full bg-[#211C26] px-[18px] py-[11px] pr-[18px] text-[13.5px] font-semibold text-white shadow-[0_8px_32px_-8px_rgba(33,28,38,0.32)] transition-all duration-200 ${visible ? 'translate-y-0 opacity-100 pointer-events-auto' : 'translate-y-3 opacity-0 pointer-events-none'}`}
        >
            <Ic d={I.heart} size={14} color="#FF6B5E" fill="#FF6B5E" sw={0} />
            {message}
            <button
                type="button"
                onClick={onClose}
                className="ml-1 flex cursor-pointer items-center border-0 bg-transparent pl-1 text-[rgba(255,255,255,0.45)]"
                aria-label="닫기"
            >
                <Ic d={I.x} size={13} color="rgba(255,255,255,0.45)" />
            </button>
        </div>
    );
}
