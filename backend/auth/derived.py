import os
import logging
from typing import Dict, Optional

import jwt
from fastapi import HTTPException, status

logger = logging.getLogger("community_resilience.auth.derived")

DERIVED_JWT_SECRET = os.getenv("DERIVED_JWT_SECRET", "change-me")
DERIVED_JWT_ALG = os.getenv("DERIVED_JWT_ALG", "HS256")
DERIVED_JWT_ISS = os.getenv("DERIVED_JWT_ISS", None)


def _mask_token(t: Optional[str]) -> str:
    if not t:
        return ""
    t = str(t)
    if len(t) <= 16:
        return t[:4] + "...(masked)"
    return t[:8] + "...(masked)..." + t[-8:]


def verify_derived_token_raw(token: str) -> Dict:
    """
    Verify a derived HS256 JWT issued by SvelteKit.

    Returns the decoded payload on success, raises HTTPException(401) on failure.
    Expected minimal claims: sub, role, exp (exp enforced by PyJWT).
    """
    logger.debug(
        "auth.derived.verify.attempt", extra={"token_mask": _mask_token(token)}
    )
    try:
        payload = jwt.decode(
            token,
            DERIVED_JWT_SECRET,
            algorithms=[DERIVED_JWT_ALG],
            options={"require_sub": False, "require_exp": True},
            # issuer check is optional; only enforce if DERIVED_JWT_ISS is set
            issuer=DERIVED_JWT_ISS if DERIVED_JWT_ISS else None,
        )
    except jwt.ExpiredSignatureError:
        logger.info(
            "auth.derived.verify.expired", extra={"token_mask": _mask_token(token)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Derived token expired"
        )
    except jwt.InvalidIssuerError:
        logger.warning(
            "auth.derived.verify.invalid_issuer",
            extra={"token_mask": _mask_token(token)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer"
        )
    except jwt.PyJWTError as e:
        logger.warning(
            "auth.derived.verify.failed",
            extra={"error": str(e), "token_mask": _mask_token(token)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid derived token"
        )

    # minimal claim checks
    if "sub" not in payload or "role" not in payload:
        logger.warning(
            "auth.derived.verify.invalid_claims",
            extra={
                "payload_keys": list(payload.keys()),
                "token_mask": _mask_token(token),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid derived token claims",
        )

    logger.info(
        "auth.derived.verify.success",
        extra={"sub": payload.get("sub"), "role": payload.get("role")},
    )
    return payload
