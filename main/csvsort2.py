import pandas as pd

# 1. 통합된 CSV 파일 로드
file_path = "./전국_자동차정비업체_통합데이터.csv"

try:
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    
    # 2. 삭제할 컬럼 목록 명시
    columns_to_drop = [
        '사업등록일자', '면적', '영업상태', '폐업일자', 
        '휴업시작일자', '휴업종료일자', '관리기관명', 
        '관리기관전화번호', '데이터기준일자'
    ]
    
    # 3. 해당 컬럼들만 데이터프레임에서 제거 (실제 존재하는 컬럼만 매칭하여 삭제)
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # 4. 동일한 파일명으로 덮어쓰기 저장
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"🏁 [완료] 불필요한 9개 컬럼 삭제가 완료되었습니다. 파일이 업데이트되었습니다: {file_path}")
    
    # 5. 남은 컬럼 목록 확인 출력
    print("\n📊 현재 남은 컬럼 목록:")
    print(list(df.columns))

except Exception as e:
    print(f"❌ 파일 처리 중 에러 발생: {e}")