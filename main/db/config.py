"""
DB 접속 설정
환경변수 우선 → 없으면 기본값 사용
"""
import os

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root1234"),
    "database": os.getenv("DB_NAME", "skn34_1st"),
    "charset":  "utf8mb4",
}
