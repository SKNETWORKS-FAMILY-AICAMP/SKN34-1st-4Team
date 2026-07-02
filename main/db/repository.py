"""
Repository — Streamlit 앱에서 호출하는 모든 DB 쿼리를 모아 놓은 모듈.
모든 public 함수는 pandas DataFrame 을 반환하므로
기존 CSV 기반 코드(df = pd.read_csv(...))를 그대로 대체할 수 있다.
"""
import pandas as pd
from db.connector import DBSession


# ──────────────────────────────────────────────
#  1. 전체 / 필터 조회 (CSV load_data 대체)
# ──────────────────────────────────────────────
def get_all_shops() -> pd.DataFrame:
    """CSV 로딩을 대체 — 전체 정비소를 DataFrame 으로 반환."""
    sql = """
        SELECT
            s.shop_id,
            r.sido        AS 시도,
            r.sigungu     AS 시군구,
            s.shop_name   AS 자동차정비업체명,
            s.repair_type_code AS 자동차정비업체종류,
            s.address     AS 소재지주소,
            s.latitude    AS 위도,
            s.longitude   AS 경도,
            s.open_time   AS 운영시작시각,
            s.close_time  AS 운영종료시각,
            s.phone       AS 전화번호
        FROM SHOP s
        JOIN REGION r ON s.region_id = r.region_id
    """
    with DBSession() as (conn, cur):
        cur.execute(sql)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


def get_shops_filtered(
    sido: str = None,
    sigungu: str = None,
    repair_types: list[int] = None,
) -> pd.DataFrame:
    """시도 / 시군구 / 정비업체종류 조합 필터."""
    conditions = []
    params = []

    if sido:
        conditions.append("r.sido = %s")
        params.append(sido)
    if sigungu:
        conditions.append("r.sigungu = %s")
        params.append(sigungu)
    if repair_types:
        placeholders = ",".join(["%s"] * len(repair_types))
        conditions.append(f"s.repair_type_code IN ({placeholders})")
        params.extend(repair_types)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            s.shop_id,
            r.sido        AS 시도,
            r.sigungu     AS 시군구,
            s.shop_name   AS 자동차정비업체명,
            s.repair_type_code AS 자동차정비업체종류,
            s.address     AS 소재지주소,
            s.latitude    AS 위도,
            s.longitude   AS 경도,
            s.open_time   AS 운영시작시각,
            s.close_time  AS 운영종료시각,
            s.phone       AS 전화번호
        FROM SHOP s
        JOIN REGION r ON s.region_id = r.region_id
        {where}
    """
    with DBSession() as (conn, cur):
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
#  2. 반경 검색 (GPS 기반)
# ──────────────────────────────────────────────
def get_shops_by_radius(
    lat: float,
    lng: float,
    radius_m: int = 5000,
    repair_types: list[int] = None,
    limit: int = 1500,
) -> pd.DataFrame:
    """
    현재 위치(lat, lng) 기준 반경 radius_m 미터 이내 정비소.
    ST_Distance_Sphere 사용 — SRID 4326 (위도 먼저).
    """
    type_filter = ""
    params: list = [lat, lng, lat, lng, radius_m]

    if repair_types:
        placeholders = ",".join(["%s"] * len(repair_types))
        type_filter = f"AND s.repair_type_code IN ({placeholders})"
        params.extend(repair_types)

    params.append(limit)

    sql = f"""
        SELECT
            s.shop_id,
            r.sido        AS 시도,
            r.sigungu     AS 시군구,
            s.shop_name   AS 자동차정비업체명,
            s.repair_type_code AS 자동차정비업체종류,
            s.address     AS 소재지주소,
            s.latitude    AS 위도,
            s.longitude   AS 경도,
            s.open_time   AS 운영시작시각,
            s.close_time  AS 운영종료시각,
            s.phone       AS 전화번호,
            ROUND(
                ST_Distance_Sphere(
                    s.geo,
                    ST_SRID(POINT(%s, %s), 4326)
                )
            ) AS distance_m
        FROM SHOP s
        JOIN REGION r ON s.region_id = r.region_id
        WHERE ST_Distance_Sphere(
                s.geo,
                ST_SRID(POINT(%s, %s), 4326)
              ) <= %s
        {type_filter}
        ORDER BY distance_m
        LIMIT %s
    """
    with DBSession() as (conn, cur):
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
#  3. 영업중 판별
# ──────────────────────────────────────────────
def get_shops_open_now(
    sido: str = None,
    sigungu: str = None,
    repair_types: list[int] = None,
) -> pd.DataFrame:
    """현재 시각 기준 영업중인 정비소만 반환."""
    conditions = [
        "s.open_time IS NOT NULL",
        "CURTIME() BETWEEN s.open_time AND s.close_time",
    ]
    params = []

    if sido:
        conditions.append("r.sido = %s")
        params.append(sido)
    if sigungu:
        conditions.append("r.sigungu = %s")
        params.append(sigungu)
    if repair_types:
        placeholders = ",".join(["%s"] * len(repair_types))
        conditions.append(f"s.repair_type_code IN ({placeholders})")
        params.extend(repair_types)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            s.shop_id,
            r.sido        AS 시도,
            r.sigungu     AS 시군구,
            s.shop_name   AS 자동차정비업체명,
            s.repair_type_code AS 자동차정비업체종류,
            s.address     AS 소재지주소,
            s.latitude    AS 위도,
            s.longitude   AS 경도,
            s.open_time   AS 운영시작시각,
            s.close_time  AS 운영종료시각,
            s.phone       AS 전화번호
        FROM SHOP s
        JOIN REGION r ON s.region_id = r.region_id
        {where}
    """
    with DBSession() as (conn, cur):
        cur.execute(sql, params)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
#  4. 브랜드(직영점) 필터
# ──────────────────────────────────────────────
def get_shops_by_brand(brand_name: str) -> pd.DataFrame:
    """브랜드명(현대/기아/쌍용 등)으로 직영·협력 정비소 조회."""
    sql = """
        SELECT
            s.shop_id,
            r.sido        AS 시도,
            r.sigungu     AS 시군구,
            s.shop_name   AS 자동차정비업체명,
            s.repair_type_code AS 자동차정비업체종류,
            s.address     AS 소재지주소,
            s.latitude    AS 위도,
            s.longitude   AS 경도,
            s.open_time   AS 운영시작시각,
            s.close_time  AS 운영종료시각,
            s.phone       AS 전화번호,
            b.brand_name
        FROM SHOP s
        JOIN REGION r    ON s.region_id = r.region_id
        JOIN SHOP_BRAND sb ON s.shop_id  = sb.shop_id
        JOIN BRAND b     ON sb.brand_id  = b.brand_id
        WHERE b.brand_name = %s
    """
    with DBSession() as (conn, cur):
        cur.execute(sql, (brand_name,))
        rows = cur.fetchall()
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
#  5. 자동완성용 드롭다운 목록
# ──────────────────────────────────────────────
def get_sido_list() -> list[str]:
    """시도 목록 반환."""
    with DBSession() as (conn, cur):
        cur.execute("SELECT DISTINCT sido FROM REGION ORDER BY sido")
        return [row["sido"] for row in cur.fetchall()]


def get_sigungu_list(sido: str) -> list[str]:
    """특정 시도 아래 시군구 목록 반환."""
    with DBSession() as (conn, cur):
        cur.execute(
            "SELECT DISTINCT sigungu FROM REGION WHERE sido = %s ORDER BY sigungu",
            (sido,),
        )
        return [row["sigungu"] for row in cur.fetchall()]


def get_brand_list() -> list[str]:
    """등록된 브랜드 목록 반환."""
    with DBSession() as (conn, cur):
        cur.execute("SELECT brand_name FROM BRAND ORDER BY brand_name")
        return [row["brand_name"] for row in cur.fetchall()]
