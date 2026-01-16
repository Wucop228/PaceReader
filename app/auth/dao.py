from datetime import datetime, timezone
from sqlalchemy import select, update
from app.core.base_dao import BaseDAO
from app.auth.models import RefreshToken

class RefreshTokenDAO(BaseDAO):
    model = RefreshToken

    async def revoke(self, token_hash: str) -> None:
        q = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.execute(q)