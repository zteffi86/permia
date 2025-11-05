from typing import NamedTuple


class MimePolicy(NamedTuple):
    """MIME type policy per evidence type"""

    allowed_mimes: set[str]
    max_size_mb: int
    duration_limit_seconds: int | None = None


EVIDENCE_POLICIES = {
    "photo": MimePolicy(
        allowed_mimes={"image/jpeg"},  # PNG support deferred (no EXIF requirement)
        max_size_mb=10,
    ),
    "video": MimePolicy(
        allowed_mimes={"video/mp4", "video/quicktime"},
        max_size_mb=50,
        duration_limit_seconds=60,  # TODO: Enforce in Week 5-8 with ffprobe
    ),
    "document": MimePolicy(
        allowed_mimes={"application/pdf"},
        max_size_mb=25,
    ),
}


def get_policy(evidence_type: str) -> MimePolicy:
    """Get policy for evidence type"""
    return EVIDENCE_POLICIES.get(
        evidence_type,
        MimePolicy(allowed_mimes=set(), max_size_mb=50),
    )
