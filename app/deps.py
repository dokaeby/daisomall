from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.deps import current_user_dep, require_admin, require_user
from app.auth.service import User
from app.db import get_db

# 라우터마다 같은 Annotated 별칭을 반복 정의하지 않도록 한 곳에 모은다.
# Conn is duck-typed: sqlite3.Connection | psycopg cursor (both support
# execute(), fetchone(), fetchall(), __getitem__()).
Conn = Annotated[object, Depends(get_db)]
CurrentUser = Annotated[User, Depends(require_user)]
OptionalUser = Annotated[User | None, Depends(current_user_dep)]
AdminUser = Annotated[User, Depends(require_admin)]
