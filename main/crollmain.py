import os
import re
import time
import requests
from bs4 import BeautifulSoup

# 1. 저장 폴더 설정
DOWNLOAD_DIR = os.path.abspath("./repair_shop_data")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 2. 세션 및 패킷 헤더 설정
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3"
})

page = 1
MAX_RETRIES = 3  # 에러 발생 시 최대 재시도 횟수

print("🚀 [시작] 45페이지 전수 다운로드 시퀀스를 가동합니다. (정제/필터링 없음)")

while True:
    list_url = "https://www.data.go.kr/tcs/dss/stdFileList.do"
    list_params = {
        "publicDataPk": "15028204",
        "searchKeyword2": "",
        "pageIndex": page,
        "url": "/tcs/dss/stdFileList.do"
    }
    
    try:
        res = session.get(list_url, params=list_params, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.select("#stdFileListDiv ul li div.tit a")
        
        # 마지막 페이지를 지나 데이터가 없으면 즉시 종료
        if not items:
            print(f"\n🏁 모든 페이지 스캔 완료. (최종 {page-1}페이지까지 수집됨)")
            break
            
        print(f"\n📄 [현재 {page} 페이지 분석 중... ({len(items)}개 지자체 발견)]")
        
        for item in items:
            file_name = item.get_text(strip=True).replace("/", "_")
            onclick_text = item.get("onclick", "")
            match = re.search(r"'(.*?)'", onclick_text)
            if not match:
                continue
            public_data_detail_pk = match.group(1)
            
            print(f"  └ 🔍 {file_name} 수집 시작")
            
            # 💡 에러 발생 시 곧바로 넘기지 않고 최대 3번 다시 시도하는 구역
            download_success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # [1단계] 파일 저장소 ID 조회를 위한 내부 API 호출
                    ajax_url = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
                    ajax_params = {
                        "publicDataPk": "15028204",
                        "publicDataDetailPk": public_data_detail_pk,
                        "fileExtsn": "csv"
                    }
                    
                    current_referer = f"{list_url}?publicDataPk=15028204&searchKeyword2=&pageIndex={page}&url=%2Ftcs%2Fdss%2FstdFileList.do#layer_data_infomation"
                    ajax_res = session.get(ajax_url, params=ajax_params, headers={"Referer": current_referer}, timeout=10)
                    json_data = ajax_res.json()
                    
                    # JSON 구조 분해 및 ID 매핑
                    atchFileId = json_data.get("atchFileId")
                    fileDetailSn = json_data.get("fileDetailSn")
                    
                    if not atchFileId and "fileDataRegistVO" in json_data:
                        vo = json_data["fileDataRegistVO"]
                        if vo:
                            atchFileId = vo.get("atchFileId")
                            fileDetailSn = vo.get("fileDetailSn")
                            
                    if not fileDetailSn:
                        fileDetailSn = "1"
                        
                    if not atchFileId:
                        raise ValueError("JSON 메타데이터 내에 파일 식별자(atchFileId)가 누락되었습니다.")
                        
                    # [2단계] 최종 실데이터 다운로드 스트림 호출
                    download_url = "https://www.data.go.kr/cmm/cmm/fileDownload.do"
                    dl_params = {
                        "atchFileId": atchFileId,
                        "fileDetailSn": str(fileDetailSn)
                    }
                    
                    file_res = session.get(download_url, params=dl_params, timeout=20)
                    
                    # 순정 바이트 그대로 디스크에 파일 저장
                    file_path = os.path.join(DOWNLOAD_DIR, f"{file_name}.csv")
                    with open(file_path, "wb") as f:
                        f.write(file_res.content)
                    
                    print(f"    💾 저장 성공: {file_name}.csv")
                    download_success = True
                    break  # 성공 시 재시도 루프 즉시 탈출
                    
                except Exception as item_err:
                    print(f"    ⚠️ 에러 발생 (시도 {attempt}/{MAX_RETRIES}): {item_err}")
                    if attempt < MAX_RETRIES:
                        time.sleep(2)  # 일시적 딜레이 방어로 2초 쉬고 재요청
                    else:
                        print(f"    ❌ [다운로드 최종 실패] 3회 시도 모두 실패하여 다음 지자체로 넘어갑니다.")
            
            time.sleep(0.3)  # 디스크 안전 쓰기 유예 시간
            
        page += 1
        
    except Exception as page_err:
        print(f"  ❌ {page} 페이지 목록 획득 실패 (2초 후 재시도): {page_err}")
        time.sleep(2)
        continue

print("\n🏁 [전체 완료] 누락 방지 재시도 기반 222건 일괄 순정 다운로드가 종료되었습니다.")