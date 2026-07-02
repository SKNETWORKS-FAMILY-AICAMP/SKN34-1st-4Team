import os
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# 🚨 DB 연동 함수 임포트 추가
from db import get_all_shops, get_shops_filtered, get_sido_list, get_sigungu_list

# 1. 스트림릿 풀스크린 및 페이지 대시보드 기본 환경 설정
st.set_page_config(page_title="전국 자동차 정비소 통합 관제 시스템", layout="wide", page_icon="🚗")

# 2. 🚨 지도 붕괴 방지 및 uBlock 필터 이식을 통한 상단바 정밀 소거
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 0rem !important; padding-right: 0rem !important; max-width: 100% !important; }
        
        /* 🚨 유저 제보 uBlock 정밀 타격: 검은색 헤더 및 디플로이 버튼만 완벽하게 소거 */
        .e1yxiy6j1.st-emotion-cache-wyoiad.stAppHeader { 
            display: none !important; 
        }
    </style>
""", unsafe_allow_html=True)

TMAP_APP_KEY = "bGSNiJ1mln1F3bRKqoCVz3P6uikC5B7rGvFPh1Fe"

# ---------------------------------------------------------
# [기존 로컬 CSV 로드 방식 주석 처리]
# @st.cache_data
# def load_data():
#     file_path = "전국_자동차정비업체_통합데이터.csv"
#     if not os.path.exists(file_path):
#         st.error(f"❌ '{file_path}' 파일이 존재하지 않습니다.")
#         return None
#     return pd.read_csv(file_path, encoding='utf-8-sig')
# ---------------------------------------------------------

# 🚨 [신규 DB 연동 방식] SQL 데이터를 불러오고 5분(300초) 단위로 캐싱
@st.cache_data(ttl=300)
def load_data():
    return get_all_shops()

df = load_data()

if df is not None:
    # 좌표 결측치 전처리 및 시군구 키 값 동기화
    clean_df = df.dropna(subset=['위도', '경도'])
    if 'sigungu' not in clean_df.columns and '시군구' in clean_df.columns:
        clean_df['sigungu'] = clean_df['시군구']
        
    shops_json = clean_df.to_json(orient='records', force_ascii=False)

    tmap_all_in_one_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            html, body { margin: 0; padding: 0; width: 100%; height: 850px; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; overflow: hidden; }
            #wrapper { position: relative; width: 100%; height: 850px; overflow: hidden; background: #eee; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            #map_container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
            
            #floating_panel {
                position: absolute; top: 20px; left: 20px; z-index: 10;
                width: 360px; max-height: 800px;
                background: rgba(255, 255, 255, 0.98); border-radius: 14px;
                box-shadow: 0 6px 25px rgba(0,0,0,0.18);
                display: flex; flex-direction: column; border: 1px solid rgba(0,0,0,0.08);
                pointer-events: auto;
            }
            
            .accordion-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; font-size: 15px; font-weight: 800; color: #111; cursor: pointer; user-select: none; border-bottom: 1px solid #f0f0f0; }
            .accordion-header:hover { color: #018aea; }
            .toggle-icon { transition: transform 0.3s ease; font-size: 14px; color: #888; display: inline-block; }
            
            #filter_content { overflow-y: auto; max-height: 0px; transition: max-height 0.3s ease; }
            
            .filter-group { padding: 14px 20px; border-bottom: 1px solid #f5f5f5; }
            .group-title { font-size: 13px; font-weight: 800; color: #444; margin-bottom: 8px; display: block; }
            .radio-option { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 600; color: #333; cursor: pointer; }
            .radio-option input { margin-right: 8px; vertical-align: middle; }
            
            select { width: 100%; padding: 9px; font-size: 13px; font-weight: bold; border-radius: 6px; border: 1px solid #ddd; outline: none; margin-bottom: 8px; cursor: pointer; background: #fff; }
            .btn-gps { width: 100%; padding: 11px; background: #018aea; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
            .btn-gps:hover { background: #0070c0; }
            #gps_status { margin-top: 6px; font-size: 12px; font-weight: bold; color: #ff3b30; text-align: center; }
            
            #info_panel { padding: 20px; overflow-y: auto; background: #fafafa; border-radius: 0 0 14px 14px; border-top: 1px solid #eee; display: none; }
            .shop-title { font-size: 19px; font-weight: 800; color: #111; margin: 0 0 10px 0; letter-spacing: -0.5px; line-height: 1.3; }
            .tag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; }
            .tag-grade { background: #e8f3fa; color: #018aea; }
            .tag-status { background: #e6f8ec; color: #00b050; border: 1px solid #00b050; }
            .info-row { font-size: 13px; color: #555; margin-top: 8px; line-height: 1.5; word-break: keep-all; }
            #navi_info { margin-top: 15px; padding: 12px; background: #fff; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 4px solid #018aea; font-size: 13px; font-weight: bold; color: #333; line-height: 1.6; }

            #empty_state { padding: 25px 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #999; font-size: 13px; font-weight: bold; text-align: center; }
            
            #custom_control { position: absolute; bottom: 30px; right: 20px; z-index: 10; display: flex; flex-direction: column; gap: 8px; }
            .map_btn { width: 42px; height: 42px; background: #fff; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); cursor: pointer; font-size: 20px; font-weight: bold; color: #555; display: flex; justify-content: center; align-items: center; user-select: none; }
            .map_btn:hover { color: #018aea; }
        </style>
        
        <script src="https://apis.openapi.sk.com/tmap/jsv2?version=1&appKey=__TMAP_KEY__"></script>
    </head>
    <body onload="initTmap()">
        <div id="wrapper">
            <div id="map_container"></div>

            <div id="floating_panel">
                <div class="accordion-header" onclick="toggleFilters()">
                    <span>🔍 추가 검색 옵션 및 필터 설정</span>
                    <span id="toggle_icon">▼</span>
                </div>
                
                <div id="filter_content">
                    <div class="filter-group">
                        <span class="group-title">🚙 1단계: 차종 선택</span>
                        <label class="radio-option">
                            <input type="radio" name="vehicle_type" value="car" checked onchange="onVehicleChange()"> 🚗 일반 승용 / SUV / 소형차
                        </label>
                        <label class="radio-option">
                            <input type="radio" name="vehicle_type" value="truck" onchange="onVehicleChange()"> 🚚 대형 화물 / 버스 / 특수차량
                        </label>
                    </div>
                    
                    <div class="filter-group" id="purpose_group">
                        <span class="group-title">🛠️ 2단계: 정비 목적</span>
                        <label class="radio-option">
                            <input type="radio" name="purpose" value="light" checked onchange="applyFilters()"> 🔧 간단한 소모품 교체 / 경정비
                        </label>
                        <label class="radio-option">
                            <input type="radio" name="purpose" value="heavy" onchange="applyFilters()"> 💥 사고 수리 / 외형 복원 (판금,도색)
                        </label>
                    </div>
                    <div id="truck_notice" class="filter-group" style="display:none; color:#d50000; font-size:12px; font-weight:bold;">
                        ⚠️ 대형 화물, 버스, 특수차량은 규격상 오직 1급 종합정비업소에서만 통합 정비가 가능합니다.
                    </div>

                    <div class="filter-group">
                        <span class="group-title">📍 3단계: 지역 행정구역 필터</span>
                        <select id="sido_select" onchange="onSidoChange()"></select>
                        <select id="sigungu_select" onchange="applyFilters()"></select>
                    </div>

                    <div class="filter-group">
                        <span class="group-title">🎯 4단계: 내 주변 반경 조건</span>
                        <select id="radius_sel" onchange="applyFilters()">
                            <option value="0">거리 제한 없음 (전체)</option>
                            <option value="3000">반경 3km 이내만</option>
                            <option value="5000" selected>반경 5km 이내만</option>
                            <option value="10000">반경 10km 이내만</option>
                        </select>
                        <button class="btn-gps" onclick="getGPS()">🎯 내 위치(GPS) 연동하기</button>
                        <div id="gps_status">⚠️ 위 버튼을 눌러 GPS를 활성화해주세요.</div>
                    </div>
                </div>

                <div id="empty_state">
                    <div style="font-size: 30px; margin-bottom: 5px;">☝️</div>
                    지도 위 정비소 마커를 선택하시면<br>상세 정보가 이곳에 바인딩됩니다.
                </div>

                <div id="info_panel">
                    <div class="shop-title" id="info_title">정비소명</div>
                    <div style="margin-bottom: 12px;">
                        <span id="info_grade" class="tag tag-grade">등급</span>
                        <span class="tag tag-status">영업중</span>
                    </div>
                    <div class="info-row"><b>📞 전화:</b> <span id="info_tel"></span></div>
                    <div class="info-row"><b>⏰ 영업:</b> <span id="info_time"></span></div>
                    <div class="info-row"><b>📍 주소:</b> <span id="info_addr"></span></div>
                    <div id="navi_info"></div>
                </div>
            </div>

            <div id="custom_control">
                <div class="map_btn" onclick="map.zoomIn()">＋</div>
                <div class="map_btn" onclick="map.zoomOut()">－</div>
            </div>
        </div>

        <script id="shops_json_data" type="application/json">__SHOPS_DATA__</script>

        <script type="text/javascript">
            var map;
            var markerCluster = null;
            var allMarkers = [];
            var routePolylines = [];
            var myMarker = null;
            var myLat = null;
            var myLng = null;
            
            var shopsData = JSON.parse(document.getElementById('shops_json_data').textContent);

            function initTmap() {
                map = new Tmapv2.Map("map_container", {
                    center: new Tmapv2.LatLng(37.4810, 126.8820),
                    width: "100%", height: "100%",
                    zoom: 13, zoomControl: false, scrollwheel: false 
                });

                var isZooming = false;
                document.getElementById('map_container').addEventListener('wheel', function(e) {
                    e.preventDefault(); e.stopPropagation();
                    if (isZooming) return;
                    isZooming = true;
                    var currentZoom = map.getZoom();
                    if (e.deltaY > 0) map.setZoom(currentZoom - 1); 
                    else map.setZoom(currentZoom + 1); 
                    setTimeout(function() { isZooming = false; }, 150);
                }, { passive: false });

                populateSidoDropdown();
                applyFilters();
            }

            function toggleFilters() {
                var content = document.getElementById("filter_content");
                var icon = document.getElementById("toggle_icon");
                if (content.style.maxHeight === "0px" || content.style.maxHeight === "") {
                    content.style.maxHeight = "480px";
                    content.style.marginTop = "10px";
                    icon.style.transform = "rotate(180deg)";
                } else {
                    content.style.maxHeight = "0px";
                    content.style.marginTop = "0px";
                    icon.style.transform = "rotate(0deg)";
                }
            }

            function populateSidoDropdown() {
                var sidoSet = new Set();
                shopsData.forEach(function(s) { if(s.시도) sidoSet.add(s.시도); });
                var sidoArray = Array.from(sidoSet).sort();
                
                var sidoSel = document.getElementById("sido_select");
                sidoSel.innerHTML = '<option value="전체">전체 지역 (전국 모드)</option>';
                sidoArray.forEach(function(s) {
                    sidoSel.innerHTML += '<option value="' + s + '">' + s + '</option>';
                });
                onSidoChange();
            }

            function onSidoChange() {
                var selectedSido = document.getElementById("sido_select").value;
                var sigunguSel = document.getElementById("sigungu_select");
                sigunguSel.innerHTML = '<option value="전체">전체 시군구</option>';
                
                if (selectedSido !== "전체") {
                    var sigunguSet = new Set();
                    shopsData.forEach(function(s) {
                        if (s.시도 === selectedSido && (s.sigungu || s.시군구)) {
                            sigunguSet.add(s.sigungu || s.시군구);
                        }
                    });
                    Array.from(sigunguSet).sort().forEach(function(sg) {
                        sigunguSel.innerHTML += '<option value="' + sg + '">' + sg + '</option>';
                    });
                    sigunguSel.style.display = "block";
                } else {
                    sigunguSel.style.display = "none";
                }
                applyFilters();
            }

            function onVehicleChange() {
                var vType = document.querySelector('input[name="vehicle_type"]:checked').value;
                var purposeGroup = document.getElementById("purpose_group");
                var notice = document.getElementById("truck_notice");
                
                if (vType === "truck") {
                    purposeGroup.style.display = "none";
                    notice.style.display = "block";
                } else {
                    purposeGroup.style.display = "block";
                    notice.style.display = "none";
                }
                applyFilters();
            }

            function applyFilters() {
                var vType = document.querySelector('input[name="vehicle_type"]:checked').value;
                var selectedSido = document.getElementById("sido_select").value;
                var selectedSigungu = document.getElementById("sigungu_select").value;
                
                var targetClasses = [];
                if (vType === "car") {
                    var purpose = document.querySelector('input[name="purpose"]:checked').value;
                    targetClasses = (purpose === "light") ? [1, 2, 3] : [1, 2];
                } else {
                    targetClasses = [1];
                }

                var filtered = shopsData.filter(function(shop) {
                    if (!targetClasses.includes(parseInt(shop.자동차정비업체종류))) return false;
                    if (selectedSido !== "전체" && shop.시도 !== selectedSido) return false;
                    if (selectedSido !== "전체" && selectedSigungu !== "전체" && (shop.sigungu || shop.시군구) !== selectedSigungu) return false;
                    return true;
                });

                renderMarkers(filtered);
            }

            function renderMarkers(dataToRender) {
                if (markerCluster) { markerCluster.destroy(); markerCluster = null; }
                allMarkers.forEach(function(m) { m.setMap(null); });
                allMarkers = [];

                // 🚨 어떤 반경 조건이든 지역구 마커 윤곽선을 캡처하도록 처리 완료
                var regionBounds = new Tmapv2.LatLngBounds();
                var hasValidCoords = false;
                
                for (var i = 0; i < dataToRender.length; i++) {
                    var lat = parseFloat(dataToRender[i].위도);
                    var lng = parseFloat(dataToRender[i].경도);
                    if (!isNaN(lat) && !isNaN(lng)) {
                        regionBounds.extend(new Tmapv2.LatLng(lat, lng));
                        hasValidCoords = true;
                    }
                }

                var radiusMeters = parseInt(document.getElementById("radius_sel").value);
                var centerPt = (myLat && myLng) ? new Tmapv2.LatLng(myLat, myLng) : null;
                var renderCount = 0;

                for (var i = 0; i < dataToRender.length; i++) {
                    var shop = dataToRender[i];
                    var lat = parseFloat(shop.위도);
                    var lng = parseFloat(shop.경도);
                    if (isNaN(lat) || isNaN(lng)) continue;
                    
                    var shopPt = new Tmapv2.LatLng(lat, lng);

                    if (radiusMeters > 0 && centerPt) {
                        if (centerPt.distanceTo(shopPt) > radiusMeters) continue;
                    }

                    if (renderCount >= 1500) break;

                    var marker = new Tmapv2.Marker({ position: shopPt, map: map, title: shop.자동차정비업체명 });

                    (function(marker, shop, lat, lng) {
                        marker.addListener("click", function() {
                            document.getElementById('empty_state').style.display = "none";
                            document.getElementById('info_panel').style.display = "block";
                            
                            var typeCode = parseInt(shop.자동차정비업체종류);
                            var typeName = typeCode === 1 ? "1급 (종합)" : (typeCode === 2 ? "2급 (소형)" : "3급 (전문/카센터)");
                            
                            document.getElementById('info_title').innerText = shop.자동차정비업체명;
                            document.getElementById('info_grade').innerText = typeName;
                            document.getElementById('info_tel').innerText = shop.전화번호 ? shop.전화번호 : "정보 없음";
                            document.getElementById('info_time').innerText = (shop.운영시작시각 || "09:00") + " ~ " + (shop.운영종료시각 || "18:00");
                            document.getElementById('info_addr').innerText = shop.소재지주소;

                            document.getElementById("filter_content").style.maxHeight = "0px";
                            document.getElementById("filter_content").style.marginTop = "0px";
                            document.getElementById("toggle_icon").style.transform = "rotate(0deg)";

                            var naviBox = document.getElementById('navi_info');
                            if (myLat && myLng) {
                                naviBox.innerHTML = "📡 실시간 경로 탐색 중...";
                                drawRoute(lat, lng);
                            } else {
                                naviBox.innerHTML = "⚠️ '내 위치 연동' 버튼을 누르시면<br>예상 소요시간과 거리가 즉시 계산됩니다.";
                            }
                        });
                    })(marker, shop, lat, lng);

                    allMarkers.push(marker);
                    renderCount++;
                }

                if (allMarkers.length > 0) {
                    markerCluster = new Tmapv2.extension.MarkerCluster({
                        markers: allMarkers, map: map, minClusterCount: 10,
                        icons: [{
                            html: '<div style="display:flex; justify-content:center; align-items:center; width:45px; height:45px; border-radius:50%; background:rgba(255, 140, 0, 0.9); color:#fff; font-weight:bold; font-size:15px; box-shadow:0 4px 10px rgba(255, 140, 0, 0.4); border:2px solid #fff;">{c}</div>',
                            size: new Tmapv2.base.Size(45, 45)
                        }]
                    });
                }
                
                var selectedSido = document.getElementById("sido_select").value;
                if (selectedSido !== "전체" && hasValidCoords) {
                    map.fitBounds(regionBounds);
                } else if (selectedSido === "전체" && allMarkers.length > 0) {
                    if (radiusMeters > 0 && centerPt) {
                        map.setCenter(centerPt);
                        if (radiusMeters <= 3000) map.setZoom(13);
                        else if (radiusMeters <= 5000) map.setZoom(12);
                        else map.setZoom(11);
                    } else {
                        map.setCenter(allMarkers[0].getPosition());
                        map.setZoom(12);
                    }
                }
            }

            function getGPS() {
                var statusText = document.getElementById("gps_status");
                if (myLat && myLng) {
                    map.setCenter(new Tmapv2.LatLng(myLat, myLng));
                    map.setZoom(14);
                    return; 
                }
                if (navigator.geolocation) {
                    statusText.innerText = "📡 GPS 위성 신호 탐색 중...";
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            myLat = position.coords.latitude;
                            myLng = position.coords.longitude;
                            var myPosition = new Tmapv2.LatLng(myLat, myLng);
                            map.setCenter(myPosition); map.setZoom(14); 

                            if (myMarker) myMarker.setMap(null);
                            myMarker = new Tmapv2.Marker({
                                position: myPosition, map: map,
                                icon: "https://apis.openapi.sk.com/upload/tmap/marker/pin_r_m_s.png"
                            });
                            statusText.innerText = "✅ GPS 연동 성공";
                            statusText.style.color = "#018aea";
                            applyFilters();
                        },
                        function(error) { statusText.innerText = "❌ 위치 허용 차단됨 (오른쪽 위 브라우저 주소창 확인)"; },
                        { timeout: 5000, enableHighAccuracy: false, maximumAge: 0 }
                    );
                }
            }

            function drawRoute(destLat, destLng) {
                routePolylines.forEach(function(p) { p.setMap(null); });
                routePolylines = [];

                var params = new URLSearchParams();
                params.append("startX", myLng.toString()); params.append("startY", myLat.toString());
                params.append("endX", destLng.toString()); params.append("endY", destLat.toString());
                params.append("reqCoordType", "WGS84GEO"); params.append("resCoordType", "WGS84GEO");
                params.append("searchOption", "0"); params.append("trafficInfo", "Y"); 

                fetch("https://apis.openapi.sk.com/tmap/routes?version=1&format=json", {
                    method: "POST", headers: { "appKey": "__TMAP_KEY__", "Content-Type": "application/x-www-form-urlencoded" },
                    body: params
                })
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    var naviBox = document.getElementById('navi_info');
                    if (data.features) {
                        var firstProp = data.features[0].properties;
                        var totalTimeMin = Math.round(parseInt(firstProp.totalTime) / 60); 
                        
                        // 🚨 [시간 포맷 변환 소스 탑재] 60분 이상 유무 검수 후 분기 처리
                        var timeString = "";
                        if (totalTimeMin >= 60) {
                            var hours = Math.floor(totalTimeMin / 60);
                            var mins = totalTimeMin % 60;
                            timeString = mins > 0 ? hours + "시간 " + mins + "분" : hours + "시간";
                        } else {
                            timeString = totalTimeMin + "분";
                        }

                        var totalDistKm = (parseInt(firstProp.totalDistance) / 1000).toFixed(1); 
                        var tollFare = parseInt(firstProp.totalFare) || 0; 
                        var fareStr = (tollFare > 0) ? '<br>💵 톨게이트 요금: ' + tollFare.toLocaleString() + '원' : "";

                        // 가공해둔 timeString 결합 출력
                        naviBox.innerHTML = '⏱️ 예상시간: <span style="color:#018aea">' + timeString + '</span><br>🚗 주행거리: ' + totalDistKm + ' km' + fareStr;

                        var trafficColors = {
                            "trafficDefaultColor": "#018aea", "trafficType1Color": "#00E676", 
                            "trafficType2Color": "#FFD600", "trafficType3Color": "#FF6D00", "trafficType4Color": "#D50000"  
                        };

                        for (var i in data.features) {
                            var feature = data.features[i];
                            if (feature.geometry.type === "LineString") {
                                var pathCoords = [];
                                var trafficIdx = feature.properties.congestion; 
                                var strokeColor = trafficColors.trafficDefaultColor;

                                if (trafficIdx == 1) strokeColor = trafficColors.trafficType1Color;
                                else if (trafficIdx == 2) strokeColor = trafficColors.trafficType2Color;
                                else if (trafficIdx == 3) strokeColor = trafficColors.trafficType3Color;
                                else if (trafficIdx == 4) strokeColor = trafficColors.trafficType4Color;

                                for (var j in feature.geometry.coordinates) {
                                    var coord = feature.geometry.coordinates[j];
                                    pathCoords.push(new Tmapv2.LatLng(coord[1], coord[0]));
                                }

                                var polyline = new Tmapv2.Polyline({
                                    path: pathCoords, strokeColor: strokeColor, strokeWeight: 6, strokeOpacity: 0.9, map: map
                                });
                                routePolylines.push(polyline);
                            }
                        }
                        
                        var bounds = new Tmapv2.LatLngBounds();
                        bounds.extend(new Tmapv2.LatLng(myLat, myLng));
                        bounds.extend(new Tmapv2.LatLng(destLat, destLng));
                        map.fitBounds(bounds);
                    }
                });
            }
        </script>
    </head>
    <body onload="initTmap()">
        <div id="wrapper">
            <div id="map_container"></div>

            <div id="floating_panel">
                <div class="accordion-header" onclick="toggleFilters()">
                    <span>🔍 추가 검색 옵션 및 필터 설정</span>
                    <span id="toggle_icon">▼</span>
                </div>
                
                <div id="filter_content">
                    <div class="filter-group">
                        <span class="group-title">🚙 1단계: 차종 선택</span>
                        <label class="radio-option">
                            <input type="radio" name="vehicle_type" value="car" checked onchange="onVehicleChange()"> 🚗 일반 승용 / SUV / 소형차
                        </label>
                        <label class="radio-option">
                            <input type="radio" name="vehicle_type" value="truck" onchange="onVehicleChange()"> 🚚 대형 화물 / 버스 / 특수차량
                        </label>
                    </div>
                    
                    <div class="filter-group" id="purpose_group">
                        <span class="group-title">🛠️ 2단계: 정비 목적</span>
                        <label class="radio-option">
                            <input type="radio" name="purpose" value="light" checked onchange="applyFilters()"> 🔧 간단한 소모품 교체 / 경정비
                        </label>
                        <label class="radio-option">
                            <input type="radio" name="purpose" value="heavy" onchange="applyFilters()"> 💥 사고 수리 / 외형 복원 (판금,도색)
                        </label>
                    </div>
                    <div id="truck_notice" class="filter-group" style="display:none; color:#d50000; font-size:12px; font-weight:bold;">
                        ⚠️ 대형 화물, 버스, 특수차량은 규격상 오직 1급 종합정비업소에서만 통합 정비가 가능합니다.
                    </div>

                    <div class="filter-group">
                        <span class="group-title">📍 3단계: 지역 행정구역 필터</span>
                        <select id="sido_select" onchange="onSidoChange()"></select>
                        <select id="sigungu_select" onchange="applyFilters()"></select>
                    </div>

                    <div class="filter-group">
                        <span class="group-title">🎯 4단계: 내 주변 반경 조건</span>
                        <select id="radius_sel" onchange="applyFilters()">
                            <option value="0">거리 제한 없음 (전체)</option>
                            <option value="3000">반경 3km 이내만</option>
                            <option value="5000" selected>반경 5km 이내만</option>
                            <option value="10000">반경 10km 이내만</option>
                        </select>
                        <button class="btn-gps" onclick="getGPS()">🎯 내 위치(GPS) 연동하기</button>
                        <div id="gps_status">⚠️ 위 버튼을 눌러 GPS를 활성화해주세요.</div>
                    </div>
                </div>

                <div id="empty_state">
                    <div style="font-size: 30px; margin-bottom: 5px;">☝️</div>
                    지도 위 정비소 마커를 선택하시면<br>상세 정보가 이곳에 바인딩됩니다.
                </div>

                <div id="info_panel">
                    <div class="shop-title" id="info_title">정비소명</div>
                    <div style="margin-bottom: 12px;">
                        <span id="info_grade" class="tag tag-grade">등급</span>
                        <span class="tag tag-status">영업중</span>
                    </div>
                    <div class="info-row"><b>📞 전화:</b> <span id="info_tel"></span></div>
                    <div class="info-row"><b>⏰ 영업:</b> <span id="info_time"></span></div>
                    <div class="info-row"><b>📍 주소:</b> <span id="info_addr"></span></div>
                    <div id="navi_info"></div>
                </div>
            </div>

            <div id="custom_control">
                <div class="map_btn" onclick="map.zoomIn()">＋</div>
                <div class="map_btn" onclick="map.zoomOut()">－</div>
            </div>
        </div>
    </body>
    </html>
    """

    final_html = tmap_all_in_one_html.replace("__TMAP_KEY__", TMAP_APP_KEY).replace("__SHOPS_DATA__", shops_json)
    
    # 850px 컴포넌트 렌더링
    components.html(final_html, height=850, scrolling=False)