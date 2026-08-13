from app.rag.base import KnowledgeChunk


WORKFLOW_CHUNKS: tuple[KnowledgeChunk, ...] = (
    KnowledgeChunk(
        id="favorites-patterns",
        title="좋아요 패턴 활용",
        content="좋아요한 곡은 아티스트명, 앨범 결, 장르 성향을 우선으로 묶어 해석한다. 같은 아티스트를 반복하기보다 비슷한 결의 다른 아티스트를 섞어 준다.",
        keywords=("favorite", "favorites", "좋아요", "아티스트", "앨범", "장르"),
    ),
    KnowledgeChunk(
        id="track-reasoning",
        title="추천 이유 작성",
        content="추천 이유는 추상적인 칭찬보다 한 곡의 멜로디, 보컬, 리듬, 전개, 질감 같은 구체적인 포인트를 적어야 한다.",
        keywords=("reason", "track", "멜로디", "보컬", "리듬", "전개", "질감"),
    ),
    KnowledgeChunk(
        id="playlist-flow",
        title="플레이리스트 흐름",
        content="추천 결과는 첫 곡은 현재 감정에 정확히 붙이고, 뒤로 갈수록 약간씩 확장하거나 완화하는 식으로 흐름을 만든다.",
        keywords=("playlist", "flow", "흐름", "첫 곡", "전개"),
    ),
    KnowledgeChunk(
        id="spotify-search",
        title="Spotify 검색 전략",
        content="검색이 필요한 경우 곡명과 아티스트명을 함께 쓰고, 안 되면 아티스트명만, 곡명만, 관련 검색어 순으로 넓혀 간다.",
        keywords=("spotify", "search", "검색", "곡명", "아티스트"),
    ),
)

