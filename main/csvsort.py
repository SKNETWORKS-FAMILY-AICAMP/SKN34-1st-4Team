import os
import glob
import pandas as pd

# 1. CSV 파일들이 들어있는 폴더 경로 지정
DATA_DIR = "./repair_shop_data"

# 2. 폴더 내의 모든 CSV 파일 목록 확보 및 가나다라 순서대로 정렬
all_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
all_files.sort()  # 파일명 순서대로 정렬

if not all_files:
    print("❌ 지정된 폴더에 CSV 파일이 존재하지 않습니다. 경로를 확인해주세요.")
    exit()

print(f"📂 총 {len(all_files)}개의 지자체 CSV 파일 통합 및 지역 컬럼 추가 작업을 시작합니다.")

df_list = []

# 3. 모든 파일을 순서대로 순회하며 데이터 로드 및 파일명 분리
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
        
        # 💡 핵심: 맨 앞(인덱스 0번)에 '시군구'와 '시도'를 차례로 인서트하여 순서를 고정합니다.
        df.insert(0, '시군구', sigungu)
        df.insert(0, '시도', sido)
        
        df_list.append(df)
        print(f"  └ 📑 매칭 성공: {filename} -> [{sido} / {sigungu}]")
    except UnicodeDecodeError:
        try:
            # CP949 인코딩 재시도
            df = pd.read_csv(file, encoding='cp949')
            df.insert(0, '시군구', sigungu)
            df.insert(0, '시도', sido)
            df_list.append(df)
            print(f"  └ 📑 읽기 성공(CP949): {filename} -> [{sido} / {sigungu}]")
        except Exception as e:
            print(f"  ❌ 인코딩 오류로 파일 읽기 실패 ({filename}): {e}")
    except Exception as e:
        print(f"  ❌ 파일 읽기 에러 스킵 ({filename}): {e}")

# 4. 하나의 데이터프레임으로 순정 상태 그대로 병합
if df_list:
    integrated_df = pd.concat(df_list, ignore_index=True)
    
    # 5. 최종 통합본 CSV 파일 1개로 출력 저장
    output_path = "./전국_자동차정비업체_통합데이터.csv"
    integrated_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n🏁 [통합 완료] '{output_path}' 파일 맨 앞에 '시도', '시군구' 컬럼이 정렬되어 저장되었습니다.")
else:
    print("❌ 통합할 데이터가 정상적으로 로드되지 않았습니다.")