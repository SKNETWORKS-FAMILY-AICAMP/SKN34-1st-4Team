import pandas as pd
import pymysql
from datetime import datetime
 
DB_CONFIG = dict(
    host="localhost",
    port=3306,
    user="root",
    password="root1234",   
    database="skn34_1st",
    charset="utf8mb4",
)
 
CSV_PATH = r"C:\Users\playdata2\project_first\SKN34-1st-4Team\main\전국_자동차정비업체_통합데이터.csv"
 
 
def load_brand_keywords(cur):
    """BRAND_KEYWORD 테이블에서 brand_id별 키워드 목록을 읽어옴"""
    cur.execute("""
        SELECT b.brand_id, bk.keyword
        FROM BRAND b
        JOIN BRAND_KEYWORD bk ON b.brand_id = bk.brand_id
    """)
    brand_keywords = {}  
    for brand_id, keyword in cur.fetchall():
        brand_keywords.setdefault(brand_id, []).append(keyword)
    return brand_keywords
 
 
def detect_brand_id(shop_name: str, brand_keywords: dict):
    """업체명에서 브랜드 키워드를 찾아 brand_id 반환 (없으면 None)"""
    name = str(shop_name)
    for brand_id, keywords in brand_keywords.items():
        for kw in keywords:
            if kw in name:
                return brand_id
    return None
 
 
def parse_time(value):
    """CSV 시간 문자열 → TIME 형식. 결측이면 None."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    
    s = s.replace(".", ":")
    if ":" not in s and len(s) in (3, 4):
        s = s.zfill(4)
        s = f"{s[:2]}:{s[2:]}"
    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        return None
 
 
def main():
    print("CSV 로딩 중...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    print(f"전체 {len(df):,}건 로드 완료")
 
    # 결측 위경도 제거 (지도에 못 띄우는 데이터는 적재 제외)
    before = len(df)
    df = df.dropna(subset=["위도", "경도"])
    print(f"위경도 결측 {before - len(df):,}건 제외 → {len(df):,}건 적재 예정")
 
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
 
    # ── 1. REGION 적재 (중복 시도+시군구는 1번만) ──────────────────
    print("\n[1/3] REGION 테이블 적재 중...")
    region_pairs = df[["시도", "시군구"]].drop_duplicates().values.tolist()
 
    region_map = {}  # (sido, sigungu) -> region_id
    for sido, sigungu in region_pairs:
        cur.execute(
            """INSERT INTO REGION (sido, sigungu) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE region_id = LAST_INSERT_ID(region_id)""",
            (sido, sigungu),
        )
        region_id = cur.lastrowid
        region_map[(sido, sigungu)] = region_id
    conn.commit()
    print(f"REGION {len(region_map):,}건 적재 완료")
 
    # ── 2. 브랜드 키워드 매핑 DB에서 로드 ──────────────────────────
    brand_keywords = load_brand_keywords(cur)
    print(f"브랜드 키워드 {sum(len(v) for v in brand_keywords.values())}개 로드 완료")
 
    # ── 3. SHOP 적재 (+ SHOP_BRAND 동시 처리) ─────────────────────
    print("\n[2/3] SHOP 테이블 적재 중... (수 분 소요될 수 있습니다)")
 
    insert_shop_sql = """
        INSERT INTO SHOP
            (shop_name, region_id, address, latitude, longitude, phone, open_time, close_time, repair_type_code)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    insert_sb_sql = "INSERT IGNORE INTO SHOP_BRAND (shop_id, brand_id) VALUES (%s, %s)"
 
    shop_count = 0
    brand_link_count = 0
    BATCH = 1000
    buffer = []
 
    for idx, row in df.iterrows():
        region_id = region_map.get((row["시도"], row["시군구"]))
        if region_id is None:
            continue
 
        repair_type = row["자동차정비업체종류"]
        repair_type = int(repair_type) if pd.notna(repair_type) else 99
 
        buffer.append((
            row["자동차정비업체명"],
            region_id,
            row["소재지주소"] if pd.notna(row["소재지주소"]) else None,
            float(row["위도"]),
            float(row["경도"]),
            row["전화번호"] if pd.notna(row["전화번호"]) else None,
            parse_time(row.get("운영시작시각")),
            parse_time(row.get("운영종료시각")),
            repair_type,
        ))
 
        if len(buffer) >= BATCH:
            print(f"컬럼 수: 9, %s 수: {insert_shop_sql.count('%s')}, 튜플 길이: {len(buffer[0])}")
            print(buffer[0])
            cur.executemany(insert_shop_sql, buffer)
            conn.commit()
            shop_count += len(buffer)
            buffer = []
            print(f"  {shop_count:,}건 적재됨...")
 
    if buffer:
        print(f"컬럼 수: 9, %s 수: {insert_shop_sql.count('%s')}, 튜플 길이: {len(buffer[0])}")
        print(buffer[0])
        cur.executemany(insert_shop_sql, buffer)
        conn.commit()
        shop_count += len(buffer)
 
    print(f"SHOP {shop_count:,}건 적재 완료")
 
    # ── 4. SHOP_BRAND 연결 (적재 끝난 SHOP 기준으로 재조회 후 매칭) ──
    print("\n[3/3] SHOP_BRAND 브랜드 매칭 중...")
    cur.execute("SELECT shop_id, shop_name FROM SHOP")
    all_shops = cur.fetchall()
 
    sb_buffer = []
    for shop_id, shop_name in all_shops:
        brand_id = detect_brand_id(shop_name, brand_keywords)
        if brand_id:
            sb_buffer.append((shop_id, brand_id))
 
    if sb_buffer:
        cur.executemany(insert_sb_sql, sb_buffer)
        conn.commit()
        brand_link_count = len(sb_buffer)
 
    print(f"SHOP_BRAND {brand_link_count:,}건 연결 완료")
 
    cur.close()
    conn.close()
 
    print("\n" + "=" * 40)
    print("적재 완료 요약")
    print("=" * 40)
    print(f"REGION       : {len(region_map):,}건")
    print(f"SHOP         : {shop_count:,}건")
    print(f"SHOP_BRAND   : {brand_link_count:,}건")
 
 
if __name__ == "__main__":
    main()