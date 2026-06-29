import os
import glob
import numpy as np
import pandas as pd

# 1. CSV 파일들이 들어있는 폴더 경로 지정
DATA_DIR = "./repair_shop_data"

# 2. 폴더 내의 모든 CSV 파일 목록 확보 및 가나다라 순서대로 정렬
all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
all_files.sort()  # 파일명 순서대로 정렬

if not all_files:
    print("❌ 지정된 폴더에 CSV 파일이 존재하지 않습니다. 경로를 확인해주세요.")
    exit()

print(f"📂 총 {len(all_files)}개의 지자체 CSV 파일 로드 및 파일명 분석을 시작합니다.")

df_list = []

# 3. 모든 원본 파일을 순서대로 순회하며 데이터 로드 및 지역 컬럼 추가
for file in all_files:
    filename = os.path.basename(file)
    name_without_ext = filename.replace('.csv', '')
    parts = name_without_ext.split('_')
    
    # 파일명에서 시도, 시군구 명칭 동적 분리
    if len(parts) >= 3:
        sido = parts[0]      # 예: 경기도
        sigungu = parts[1]   # 예: 구리시
    elif len(parts) == 2:
        sido = parts[0]      # 예: 세종특별자치시
        sigungu = parts[0]   # 시군구 구분이 없는 경우 시도명과 동일하게 삽입
    else:
        sido = "미분류"
        sigungu = "미분류"

    try:
        # UTF-8 인코딩 시도
        df = pd.read_csv(file, encoding='utf-8-sig')
        df.insert(0, '시군구', sigungu)
        df.insert(0, '시도', sido)
        df_list.append(df)
        print(f"  └ 📑 로드 완료: {filename} -> [{sido} / {sigungu}]")
    except UnicodeDecodeError:
        try:
            # CP949 인코딩 재시도
            df = pd.read_csv(file, encoding='cp949')
            df.insert(0, '시군구', sigungu)
            df.insert(0, '시도', sido)
            df_list.append(df)
            print(f"  └ 📑 로드 완료(CP949): {filename} -> [{sido} / {sigungu}]")
        except Exception as e:
            print(f"  ❌ 인코딩 오류로 파일 읽기 실패 ({filename}): {e}")
    except Exception as e:
        print(f"  ❌ 파일 읽기 에러 스킵 ({filename}): {e}")

# 4. 하나의 데이터프레임으로 수직 병합 및 후속 가공
if df_list:
    integrated_df = pd.concat(df_list, ignore_index=True)
    print(f"\n📊 원본 데이터 일차 병합 완료 (총 {len(integrated_df)}건)")

    # 💡 [주소 통합 공정] 도로명(Main) 없으면 지번(Sub)으로 대체
    if '소재지도로명주소' in integrated_df.columns and '소재지지번주소' in integrated_df.columns:
        road_name = integrated_df['소재지도로명주소'].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
        jibun_name = integrated_df['소재지지번주소'].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
        integrated_address = road_name.fillna(jibun_name)
        
        # 기존 도로명주소 자리에 '소재지주소' 삽입
        idx = integrated_df.columns.get_loc('소재지도로명주소')
        integrated_df.insert(idx, '소재지주소', integrated_address)

    # 💡 [컬럼 삭제 공정] 요청하신 불필요 컬럼 9개 + 임무 다한 기존 주소 컬럼 2개 제거
    columns_to_drop = [
        '사업등록일자', '면적', '영업상태', '폐업일자', 
        '휴업시작일자', '휴업종료일자', '관리기관명', 
        '관리기관전화번호', '데이터기준일자',
        '소재지도로명주소', '소재지지번주소'
    ]
    integrated_df = integrated_df.drop(columns=[col for col in columns_to_drop if col in integrated_df.columns], errors='ignore')

    # 5. 최종본 단 1개의 CSV 파일로 디스크 출력 저장
    output_path = "./전국_자동차정비업체_통합데이터.csv"
    integrated_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n🏁 [통합 및 가공 완료] 최종 파일 생성 성공: {output_path}")
    print(f"📊 최종 남은 컬럼 레이아웃: {list(integrated_df.columns)}")

    # 6. 🔥 [원본 파일 삭제 시퀀스] 저장이 성공했으므로 원본 경로 내 CSV 파일 일괄 제거
    print("\n🗑️ 원본 CSV 파일 정리를 시작합니다.")
    for file in all_files:
        try:
            os.remove(file)
            print(f"  └ 🗑️ 원본 삭제 완료: {os.path.basename(file)}")
        except Exception as e:
            print(f"  ❌ 원본 파일 삭제 실패 ({os.path.basename(file)}): {e}")
    print("✨ 모든 원본 파일 제거 및 디렉토리 정리가 완료되었습니다.")

else:
    print("❌ 통합할 데이터가 정상적으로 로드되지 않아 후속 공정을 중단합니다.")