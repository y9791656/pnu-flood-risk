"""
부산대학교 캠퍼스 우수(빗물) 유출 위험 분석기
PNU Campus Stormwater Runoff Risk Analyzer
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="PNU 캠퍼스 침수 위험 분석기",
    page_icon="🌧️",
    layout="wide",
)

# ── 스타일 ───────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

  .hero {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white; padding: 2.2rem 2rem 1.8rem;
    border-radius: 14px; margin-bottom: 1.6rem;
  }
  .hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0 0 .4rem; }
  .hero p  { font-size: .95rem; opacity: .82; margin: 0; }

  .metric-card {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
  }
  .metric-card .label { font-size: .78rem; color: #64748b; margin-bottom: .3rem; }
  .metric-card .value { font-size: 1.7rem; font-weight: 700; }
  .risk-HIGH   { color: #dc2626; }
  .risk-MEDIUM { color: #d97706; }
  .risk-LOW    { color: #16a34a; }

  .weather-box {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 10px; padding: .9rem 1.2rem; margin-bottom: 1rem;
    font-size: .88rem;
  }
  .detail-box {
    border-radius: 12px; padding: 1.4rem 1.6rem; margin-top: .5rem;
  }
  .detail-box h3 { margin: 0 0 .8rem; font-size: 1.1rem; }
  .cause-item  { background: rgba(0,0,0,.06); border-radius: 8px;
                 padding: .5rem .8rem; margin-bottom: .4rem; font-size: .88rem; }
  .action-item { background: rgba(255,255,255,.55); border-radius: 8px;
                 padding: .5rem .8rem; margin-bottom: .4rem; font-size: .88rem; }
  .legend-box {
    background: white; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: .8rem 1rem; font-size: .84rem;
  }
  .dot { display:inline-block; width:12px; height:12px;
         border-radius:50%; margin-right:6px; vertical-align:middle; }
</style>
""", unsafe_allow_html=True)

# ── 기상청 API ───────────────────────────────────────────────
API_KEY = "9e02a1eb28bd866d61c6898a9842d00ec0f4658b4c827d3768f545f244bbb45b"

def get_current_rainfall():
    """기상청 ASOS 부산 관측소(159) 실시간 강우량 조회"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    hour_str = now.strftime("%H")

    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    params = {
        "serviceKey": API_KEY,
        "pageNo": 1,
        "numOfRows": 1,
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": date_str,
        "startHh": hour_str,
        "endDt": date_str,
        "endHh": hour_str,
        "stnIds": "159",   # 부산 관측소
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        items = data["response"]["body"]["items"]["item"]
        if items:
            rn = items[0].get("rn", "0")
            temp = items[0].get("ta", "N/A")
            humidity = items[0].get("hm", "N/A")
            wind = items[0].get("ws", "N/A")
            rainfall = float(rn) if rn not in ("", None) else 0.0
            return {
                "success": True,
                "rainfall": rainfall,
                "temp": temp,
                "humidity": humidity,
                "wind": wind,
                "time": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {hour_str}시",
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "error": "데이터 없음"}

# ── 구역 데이터 ──────────────────────────────────────────────
# 중심 좌표: 대운동장 포함하도록 조정
PNU_LAT, PNU_LON = 35.2325, 129.0858

ZONES = [
    {
        "name": "정문·제1문화관",
        "lat": 35.2310, "lon": 129.0820,
        "area_ha": 2.1, "impervious_ratio": 0.80,
        "elevation_diff": 1.2, "drain_capacity": 0.28,
        "description": "정문 앞 광장 및 진입로. 아스팔트·보도블록 비율 높음.",
        "causes": [
            "아스팔트 포장 비율 80% — 빗물이 즉시 유출",
            "진입로 경사로 외부 빗물까지 캠퍼스 내 유입",
            "노후 배수관(1980년대 설치)으로 처리 용량 부족",
        ],
        "actions": [
            "🚨 정문 차량 통제 및 보행자 우회로 안내",
            "🪣 모래주머니 배치로 강의동 방향 유입 차단",
            "📢 학생 대피 방송 실시",
            "🔧 장기: 투수성 포장재 교체, 빗물 저류조 설치",
        ],
    },
    {
        "name": "학생회관·제2도서관",
        "lat": 35.2328, "lon": 129.0842,
        "area_ha": 1.8, "impervious_ratio": 0.72,
        "elevation_diff": 0.5, "drain_capacity": 0.22,
        "description": "학생 밀집 구역. 건물 밀도 높고 녹지 적음.",
        "causes": [
            "건물 밀도가 높아 지붕 유출수가 지면에 집중",
            "녹지 면적 부족으로 자연 흡수 기능 미비",
            "인접 구역 유출수가 저지대인 이 구역으로 합류",
        ],
        "actions": [
            "🚨 도서관 지하 1층 이용 즉시 중단",
            "📦 전산 장비·귀중 자료 상층부로 이동",
            "🚶 학생회관 → 공대 방향 우회 동선 안내",
            "🔧 장기: 옥상 녹화 및 우수 재활용 시스템 도입",
        ],
    },
    {
        "name": "공대 구역",
        "lat": 35.2345, "lon": 129.0870,
        "area_ha": 3.2, "impervious_ratio": 0.65,
        "elevation_diff": 0.3, "drain_capacity": 0.38,
        "description": "건물 및 주차장 혼재. 경사 완만.",
        "causes": [
            "주차장 포장면이 넓어 유출량 증가",
            "완만한 경사로 빗물 정체 시간이 길어짐",
            "실험동 냉각수와 빗물이 같은 배수로 사용",
        ],
        "actions": [
            "🚗 주차장 차량 이동 권고",
            "⚡ 실험동 전기 패널 점검 및 누전 차단기 확인",
            "🚶 공대 → 사범대 방향 우회로 이용",
            "🔧 장기: 주차장 투수 블록 교체, 식생 수로 조성",
        ],
    },
    {
        "name": "사범대·인문관",
        "lat": 35.2355, "lon": 129.0835,
        "area_ha": 2.4, "impervious_ratio": 0.60,
        "elevation_diff": -0.8, "drain_capacity": 0.30,
        "description": "경사지에 위치. 상대적으로 녹지 비율 있음.",
        "causes": [
            "경사지 상단이라 자체 유출량은 적음",
            "인문관 건물 사이 통로에 빗물 집중 현상 가능",
        ],
        "actions": [
            "🌬️ 강풍 동반 시 건물 외벽 균열 점검",
            "🚶 경사로 미끄러짐 주의 안내",
            "🔧 장기: 경사면 식생 강화로 토양 침식 방지",
        ],
    },
    {
        "name": "대운동장·체육관",
        "lat": 35.2306, "lon": 129.0868,
        "area_ha": 4.5, "impervious_ratio": 0.88,
        "elevation_diff": 1.8, "drain_capacity": 0.32,
        "description": "운동장 포함. 넓은 불투수면으로 유출량 최대 집중 구역.",
        "causes": [
            "운동장 전체가 포장면 — 캠퍼스 내 단일 최대 유출 발생지",
            "주변보다 1.8m 낮은 지형으로 사방 빗물이 집중",
            "체육관 지붕 유출수가 한 지점에 집중 배출",
            "배수관 용량 대비 최대 3배 이상 초과 가능",
        ],
        "actions": [
            "🚨 운동장·체육관 즉시 출입 통제",
            "🏊 지하 시설(락커룸 등) 즉각 대피",
            "🚒 침수 심화 시 소방서 신고 (119)",
            "📍 대피 경로: 체육관 → 사범대 방향 언덕",
            "🔧 장기: 투수 인조잔디 교체, 대형 지하 저류조 설치 필수",
        ],
    },
    {
        "name": "자연대·약학대",
        "lat": 35.2370, "lon": 129.0855,
        "area_ha": 2.0, "impervious_ratio": 0.55,
        "elevation_diff": -1.5, "drain_capacity": 0.26,
        "description": "언덕 상단 위치. 유출수가 아래 구역으로 흘러 하류 위험 가중.",
        "causes": [
            "상대적으로 녹지 비율이 있어 자체 흡수 가능",
            "유출수가 아래 구역(공대·운동장)으로 집중돼 하류 위험 가중",
        ],
        "actions": [
            "📡 하류 구역(운동장·공대) 침수 상황 모니터링",
            "🔬 실험실 화학약품 유출 방지 조치",
            "🔧 장기: 경사면 빗물 분산 수로 설치",
        ],
    },
    {
        "name": "생활관(기숙사)",
        "lat": 35.2295, "lon": 129.0878,
        "area_ha": 1.5, "impervious_ratio": 0.58,
        "elevation_diff": 0.6, "drain_capacity": 0.18,
        "description": "기숙사 밀집 구역. 야간 침수 시 안전 우려.",
        "causes": [
            "배수관이 가장 노후화된 구역 (설치 후 40년 이상)",
            "생활용수 + 빗물 동시 처리로 배수 과부하",
            "지하 주차장·창고가 침수에 직접 노출",
        ],
        "actions": [
            "🌙 야간 기상 악화 시 기숙사생 즉시 알림",
            "🚗 지하 주차장 차량 즉시 이동",
            "🏠 1층 기숙사생 상층 임시 대피",
            "📞 기숙사 사감실 비상연락망 가동",
            "🔧 장기: 배수관 전면 교체 및 용량 증설",
        ],
    },
    {
        "name": "넉넉한터·중앙광장",
        "lat": 35.2335, "lon": 129.0855,
        "area_ha": 0.8, "impervious_ratio": 0.92,
        "elevation_diff": 0.4, "drain_capacity": 0.10,
        "description": "캠퍼스 중심 광장. 포장율 최고 구역.",
        "causes": [
            "포장율 92% — 캠퍼스 내 불투수면 비율 1위",
            "광장 중심부로 사방 유출수가 집중되는 지형",
            "배수구 간격이 넓어 집중호우 시 즉시 포화",
        ],
        "actions": [
            "🚨 광장 내 집회·행사 즉시 중단 및 대피",
            "⚡ 야외 전기 시설 전원 차단",
            "🚶 인근 건물 내부로 대피 유도",
            "🔧 장기: 투수 포장 전환, 빗물 정원(Rain Garden) 조성",
        ],
    },
]

RAINFALL_PRESETS = {
    "보통 비 (10mm/h)": 10,
    "집중호우 기준 (30mm/h)": 30,
    "태풍급 (50mm/h)": 50,
    "극한 강우 (80mm/h — 2023 부산 기준)": 80,
}

# ── 계산 함수 ────────────────────────────────────────────────
def runoff_coeff(impervious_ratio):
    return 0.25 + 0.60 * impervious_ratio

def calc_peak_flow(area_ha, C, I_mm_h):
    return C * (I_mm_h / 1000 / 3600) * (area_ha * 10_000)

def risk_level(Q, capacity, elev_diff):
    score = (Q / capacity) * (1 + max(elev_diff, 0) * 0.25)
    if score > 1.5:   return "HIGH"
    elif score > 1.0: return "MEDIUM"
    return "LOW"

RISK_COLOR = {"HIGH": "#dc2626", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
RISK_KR    = {"HIGH": "🔴 위험", "MEDIUM": "🟡 주의", "LOW": "🟢 안전"}
RISK_BG    = {"HIGH": "#fef2f2", "MEDIUM": "#fffbeb", "LOW": "#f0fdf4"}

# ── UI 시작 ──────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🌧️ 부산대 캠퍼스 침수 위험 분석기</h1>
  <p>기상청 실시간 강우량 또는 시나리오를 선택해 캠퍼스 각 구역의 침수 위험도를 확인하세요.<br>
  배수 용량 초과율 기반 · 환경공학과 / 도시공학과 / 건축공학과 연계</p>
</div>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌦️ 강우 데이터 소스")

    mode = st.radio("데이터 입력 방식", ["🌐 기상청 실시간", "📊 시나리오 선택", "✏️ 직접 입력"])

    weather_info = None
    I = 30  # 기본값

    if mode == "🌐 기상청 실시간":
        if st.button("🔄 실시간 데이터 불러오기", use_container_width=True):
            with st.spinner("기상청 API 연결 중..."):
                weather_info = get_current_rainfall()
            if weather_info and weather_info["success"]:
                I = weather_info["rainfall"]
                st.session_state["weather"] = weather_info
                st.session_state["I"] = I
            else:
                st.error(f"API 오류: {weather_info.get('error','알 수 없음')}")

        if "weather" in st.session_state:
            w = st.session_state["weather"]
            I = st.session_state.get("I", 0)
            st.markdown(f"""
            <div class="weather-box">
              <b>📡 부산 기상 관측소 (#{159})</b><br>
              🕐 {w['time']}<br>
              🌧️ 강우량: <b>{w['rainfall']} mm/h</b><br>
              🌡️ 기온: {w['temp']}°C &nbsp; 💧 습도: {w['humidity']}%<br>
              💨 풍속: {w['wind']} m/s
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("버튼을 눌러 실시간 데이터를 불러오세요.")

    elif mode == "📊 시나리오 선택":
        preset = st.selectbox("강우 시나리오", list(RAINFALL_PRESETS.keys()))
        I = RAINFALL_PRESETS[preset]

    else:
        I = st.slider("강우강도 직접 입력 (mm/h)", 5, 120, 30, 5)

    st.markdown(f"### 💧 현재 강우강도: `{I} mm/h`")

    st.markdown("---")
    st.markdown("### 📐 위험 판정 방식")
    st.latex(r"Q = C \cdot I \cdot A")
    st.latex(r"\text{score} = \frac{Q}{Q_{cap}} \times (1 + \Delta h \cdot 0.25)")
    st.markdown("""
- score **> 1.5** → 🔴 위험
- score **> 1.0** → 🟡 주의 (배수 용량 초과)
- score **≤ 1.0** → 🟢 안전
    """)
    st.markdown("---")
    st.markdown("""
<div class="legend-box">
  <div><span class="dot" style="background:#dc2626"></span><b>위험</b> — 즉각 대피 필요</div>
  <div style="margin:.4rem 0"><span class="dot" style="background:#f59e0b"></span><b>주의</b> — 용량 초과, 모니터링</div>
  <div><span class="dot" style="background:#22c55e"></span><b>안전</b> — 배수 처리 가능</div>
</div>
    """, unsafe_allow_html=True)

# ── 계산 ─────────────────────────────────────────────────────
results = []
for z in ZONES:
    C  = runoff_coeff(z["impervious_ratio"])
    Q  = calc_peak_flow(z["area_ha"], C, I)
    ov = Q / z["drain_capacity"]
    risk = risk_level(Q, z["drain_capacity"], z["elevation_diff"])
    results.append({**z, "C": C, "Q": Q, "overflow_ratio": ov, "risk": risk})

df = pd.DataFrame(results)

# ── 요약 지표 ─────────────────────────────────────────────────
high_cnt   = (df["risk"] == "HIGH").sum()
medium_cnt = (df["risk"] == "MEDIUM").sum()
low_cnt    = (df["risk"] == "LOW").sum()
total_Q    = df["Q"].sum()

c1, c2, c3, c4 = st.columns(4)
for col, label, val, risk in [
    (c1, "🔴 위험 구역", f"{high_cnt}개소", "HIGH"),
    (c2, "🟡 주의 구역", f"{medium_cnt}개소", "MEDIUM"),
    (c3, "🟢 안전 구역", f"{low_cnt}개소", "LOW"),
    (c4, "💧 총 유출량",  f"{total_Q:.2f} m³/s", None),
]:
    cls = f"risk-{risk}" if risk else "risk-LOW"
    col.markdown(f"""
    <div class="metric-card">
      <div class="label">{label}</div>
      <div class="value {cls}">{val}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 지도 + 리스트 ─────────────────────────────────────────────
map_col, table_col = st.columns([3, 2])

with map_col:
    st.markdown("#### 🗺️ 구역별 침수 위험 지도")
    st.caption("마커를 클릭하면 침수 원인과 행동 방안을 확인할 수 있어요.")

    # 대운동장 포함하도록 zoom & 중심 조정
    m = folium.Map(
        location=[PNU_LAT, PNU_LON],
        zoom_start=15,
        tiles="CartoDB positron",
    )

    for row in results:
        color  = RISK_COLOR[row["risk"]]
        radius = min(28 + row["overflow_ratio"] * 14, 65)

        popup_html = f"""
        <div style="font-family:'Noto Sans KR',sans-serif;width:270px;padding:4px;">
          <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:6px;">
            {row['name']}
          </div>
          <div style="font-size:12px;color:#555;margin-bottom:8px;">
            {RISK_KR[row['risk']]} &nbsp;|&nbsp;
            유출량 {row['Q']:.3f} m³/s &nbsp;|&nbsp;
            배수 {row['overflow_ratio']:.1f}배 초과
          </div>
          <hr style="margin:6px 0;border-color:#eee;">
          <div style="font-size:11px;font-weight:600;margin-bottom:4px;">⚠️ 침수 원인</div>
          {"".join(f'<div style="background:#fff3f3;border-radius:4px;padding:3px 6px;margin-bottom:3px;font-size:11px;">• {c}</div>' for c in row['causes'])}
          <div style="font-size:11px;font-weight:600;margin:6px 0 4px;">✅ 행동 방안</div>
          {"".join(f'<div style="background:#f0fdf4;border-radius:4px;padding:3px 6px;margin-bottom:3px;font-size:11px;">{a}</div>' for a in row['actions'])}
        </div>
        """

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.55,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['name']} — {RISK_KR[row['risk']]} (초과 {row['overflow_ratio']:.1f}배)",
        ).add_to(m)

        folium.Marker(
            location=[row["lat"] + 0.00015, row["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:600;'
                     f'color:{color};white-space:nowrap;">{row["name"]}</div>',
                icon_size=(160, 20), icon_anchor=(0, 0))
        ).add_to(m)

    st_folium(m, width="100%", height=520)

with table_col:
    st.markdown("#### 📊 구역별 분석 결과")
    st.caption("구역을 선택하면 하단에 상세 내용이 펼쳐져요.")

    selected = st.radio(
        "구역 선택",
        [r["name"] for r in results],
        label_visibility="collapsed"
    )

    for row in results:
        color   = RISK_COLOR[row["risk"]]
        bar_pct = min(int(row["overflow_ratio"] / df["overflow_ratio"].max() * 100), 100)
        st.markdown(f"""
        <div style="border:1px solid #e2e8f0;border-left:4px solid {color};
                    border-radius:8px;padding:.65rem 1rem;margin-bottom:.5rem;">
          <div style="font-weight:600;font-size:.88rem;">{row['name']}</div>
          <div style="font-size:.76rem;color:#64748b;margin:.2rem 0;">
            {RISK_KR[row['risk']]} &nbsp;|&nbsp;
            Q: <b>{row['Q']:.3f}</b> m³/s &nbsp;|&nbsp;
            초과: <b>{row['overflow_ratio']:.1f}배</b>
          </div>
          <div style="background:#f1f5f9;border-radius:4px;height:5px;margin-top:.4rem;">
            <div style="background:{color};width:{bar_pct}%;height:5px;border-radius:4px;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ── 선택 구역 상세 패널 ───────────────────────────────────────
st.markdown("---")
sel   = next(r for r in results if r["name"] == selected)
color = RISK_COLOR[sel["risk"]]
bg    = RISK_BG[sel["risk"]]

st.markdown(f"""
<div class="detail-box" style="background:{bg};border:1.5px solid {color}30;">
  <h3 style="color:{color};">{RISK_KR[sel['risk']]} &nbsp; {sel['name']}</h3>
  <div style="font-size:.85rem;color:#555;margin-bottom:1rem;">
    유출량 <b>{sel['Q']:.3f} m³/s</b> &nbsp;/&nbsp;
    배수 용량 <b>{sel['drain_capacity']} m³/s</b> &nbsp;/&nbsp;
    초과율 <b style="color:{color}">{sel['overflow_ratio']:.1f}배</b> &nbsp;/&nbsp;
    불투수면 <b>{int(sel['impervious_ratio']*100)}%</b>
  </div>
  <div style="display:flex;gap:1.2rem;flex-wrap:wrap;">
    <div style="flex:1;min-width:240px;">
      <div style="font-weight:700;font-size:.9rem;margin-bottom:.5rem;">⚠️ 침수 원인</div>
      {"".join(f'<div class="cause-item">• {c}</div>' for c in sel['causes'])}
    </div>
    <div style="flex:1;min-width:240px;">
      <div style="font-weight:700;font-size:.9rem;margin-bottom:.5rem;">✅ 행동 방안</div>
      {"".join(f'<div class="action-item">{a}</div>' for a in sel['actions'])}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 전체 경보 ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
high_zones = [r for r in results if r["risk"] == "HIGH"]
mid_zones  = [r for r in results if r["risk"] == "MEDIUM"]

if high_zones:
    st.error(f"⚠️ **위험 구역 {len(high_zones)}개소** — 즉각 대피 및 출입 통제를 권고합니다.")
    for z in high_zones:
        st.markdown(f"- **{z['name']}** : 배수 용량 {z['overflow_ratio']:.1f}배 초과")
if mid_zones:
    st.warning(f"🟡 **주의 구역 {len(mid_zones)}개소** — 지속 모니터링이 필요합니다.")
    for z in mid_zones:
        st.markdown(f"- **{z['name']}** : 배수 용량 {z['overflow_ratio']:.1f}배 초과")
if not high_zones and not mid_zones:
    st.success("🟢 현재 강우강도에서는 모든 구역이 배수 처리 가능 범위입니다.")

# ── 상세 데이터 테이블 ────────────────────────────────────────
with st.expander("📋 전체 수치 데이터"):
    disp = df[["name","area_ha","impervious_ratio","drain_capacity","C","Q","overflow_ratio","risk"]].copy()
    disp.columns = ["구역명","면적(ha)","불투수면비율","배수용량(m³/s)","유출계수C","유출량Q(m³/s)","배수초과율","위험등급"]
    disp["불투수면비율"]   = (disp["불투수면비율"]*100).astype(int).astype(str)+"%"
    disp["유출계수C"]      = disp["유출계수C"].round(3)
    disp["유출량Q(m³/s)"] = disp["유출량Q(m³/s)"].round(4)
    disp["배수초과율"]     = disp["배수초과율"].round(2).astype(str)+"배"
    disp["위험등급"]       = disp["위험등급"].map(RISK_KR)
    st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("""
<div style="font-size:.78rem;color:#94a3b8;text-align:center;">
  제11회 PNU AI+X 문제해결 경진대회 출품작 &nbsp;|&nbsp;
  배수 용량 초과율 기반 합리식(Rational Method) 분석 &nbsp;|&nbsp;
  기상 데이터: 기상청 ASOS 부산 관측소(#159)
</div>
""", unsafe_allow_html=True)
