import streamlit as st
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image, ImageFilter, ImageOps
import time
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import random
import os
import io
import requests

# --------------------------------------------------------------------------
# [PDF 관련 라이브러리]
# --------------------------------------------------------------------------
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# --------------------------------------------------------------------------
# [0] 한글 폰트 설정 (PDF용)
# --------------------------------------------------------------------------
def register_korean_font():
    """PDF 생성을 위해 나눔고딕 폰트를 다운로드 및 등록합니다."""
    font_name = "NanumGothic"
    file_name = "NanumGothic.ttf"
    
    if not os.path.exists(file_name):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        try:
            response = requests.get(url)
            with open(file_name, "wb") as f:
                f.write(response.content)
            pdfmetrics.registerFont(TTFont(font_name, file_name))
        except:
            pass # 인터넷 연결 없으면 패스 (기본 폰트 사용 시 깨질 수 있음)
            
    try:
        pdfmetrics.registerFont(TTFont(font_name, file_name))
    except:
        pass
    return font_name

KOREAN_FONT = register_korean_font()

# --------------------------------------------------------------------------
# [1] 앱 설정 & CSS
# --------------------------------------------------------------------------
st.set_page_config(page_title="AI Construction Diagnosis Pro", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        p, div, h1, h2, h3, h4, span, button {font-family: 'Pretendard', 'Suit', sans-serif;}
        header, footer {visibility: hidden;}
        .block-container {padding-top: 1rem !important;}
        
        .badge-base { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-right: 5px; vertical-align: middle; }
        .badge-best { background: linear-gradient(135deg, #0d47a1, #1976d2); color: white; }
        .badge-diy { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
        .badge-pro { background-color: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
        
        .risk-box { background-color: #fff5f5; border-left: 5px solid #ff6b6b; padding: 20px; margin: 20px 0; border-radius: 4px; }
        .risk-title { font-weight: 700; color: #c92a2a; margin-bottom: 10px; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# [2] 데이터베이스 (시공 시나리오 데이터)
# --------------------------------------------------------------------------
SCENARIOS = {
    "tile_crack": {
        "title": "화장실 바닥 타일 파손/균열",
        "grade": "심각 (Critical Leak Risk)",
        "color": "#e53935",
        "radar": [90, 85, 80, 70, 95],
        "risk_report": """
            **🚨 예상되는 문제점 및 영향 분석**<br>
            1. **아래층 누수 피해**: 바닥 타일 균열은 방수층 손상으로 이어질 가능성이 매우 높습니다.<br>
            2. **신체 부상 위험**: 깨진 타일의 날카로운 단면에 발바닥 열상(찢어짐) 등 안전사고 위험이 큽니다.<br>
            3. **위생 문제**: 균열 사이로 오수가 스며들어 악취 및 곰팡이의 서식지가 됩니다.
        """,
        "msg": "타일 균열은 단순 미관 문제가 아닙니다. '방수층' 손상 여부가 핵심입니다.",
        "best_pick": 4, 
        "solutions": [
            {
                "lvl": 1, "name": "보수용 퍼티/실리콘 마감", "diy": True,
                "duration": "1시간", "tools": "헤라, 실리콘건, 커터칼",
                "desc": "미세한 실금(Hair Crack) 수분 침투 방지용 임시 조치입니다. 급한 누수를 막을 수 있습니다.",
                "steps": ["건조 상태 확인", "균열 부위 이물질 제거", "실리콘/퍼티 깊숙이 충전", "헤라로 표면 평탄화", "24시간 건조"],
                "estimate_detail": [
                    {"cat": "자재", "item": "바이오 실리콘", "spec": "300ml(백색)", "unit": "개", "qty": 1, "u_price": 8000, "t_price": 8000},
                    {"cat": "자재", "item": "보수용 퍼티(메꾸미)", "spec": "100g 튜브", "unit": "개", "qty": 1, "u_price": 6000, "t_price": 6000},
                    {"cat": "도구", "item": "실리콘 건", "spec": "철제/보급형", "unit": "개", "qty": 1, "u_price": 3000, "t_price": 3000},
                    {"cat": "도구", "item": "고무 헤라", "spec": "소형", "unit": "개", "qty": 1, "u_price": 1000, "t_price": 1000},
                    {"cat": "부자재", "item": "마스킹 테이프", "spec": "25mm", "unit": "롤", "qty": 1, "u_price": 1500, "t_price": 1500}
                ]
            },
            {
                "lvl": 2, "name": "줄눈(메지) 제거 및 재시공", "diy": True,
                "duration": "3시간", "tools": "줄눈 제거기, 스펀지, 고무장갑",
                "desc": "타일 사이 줄눈 탈락 부위를 보수하여 방수력을 높이고 위생을 강화합니다.",
                "steps": ["기존 줄눈 긁어내기", "분진 제거", "백시멘트 반죽", "줄눈 채움", "타일 닦아내기"],
                "estimate_detail": [
                    {"cat": "자재", "item": "홈멘트 (백시멘트)", "spec": "2kg/속경형", "unit": "포", "qty": 2, "u_price": 5000, "t_price": 10000},
                    {"cat": "도구", "item": "줄눈 제거기", "spec": "다이아몬드 팁", "unit": "개", "qty": 1, "u_price": 12000, "t_price": 12000},
                    {"cat": "도구", "item": "작업용 스펀지", "spec": "타일 세척용", "unit": "개", "qty": 2, "u_price": 1000, "t_price": 2000},
                    {"cat": "안전", "item": "고무장갑", "spec": "라텍스 코팅", "unit": "켤레", "qty": 1, "u_price": 2000, "t_price": 2000}
                ]
            },
            {
                "lvl": 3, "name": "타일 부분 교체 (1~2장)", "diy": False,
                "duration": "4시간", "tools": "그라인더, 정, 망치",
                "desc": "파손된 타일만 정밀하게 제거 후 동일 규격 타일로 교체합니다. 주변 타일 손상에 주의해야 합니다.",
                "steps": ["타일 줄눈 커팅", "파손 타일 파쇄", "기존 접착제 제거", "새 타일 압착 시공", "줄눈 마감"],
                "estimate_detail": [
                    {"cat": "자재", "item": "바닥 타일", "spec": "300x300mm", "unit": "장", "qty": 3, "u_price": 5000, "t_price": 15000},
                    {"cat": "자재", "item": "타일 접착제", "spec": "드라이픽스 5kg", "unit": "포", "qty": 1, "u_price": 10000, "t_price": 10000},
                    {"cat": "자재", "item": "줄눈 시멘트", "spec": "소포장", "unit": "봉", "qty": 1, "u_price": 3000, "t_price": 3000},
                    {"cat": "인건비", "item": "타일 기능공", "spec": "0.5품(오전)", "unit": "인", "qty": 0.5, "u_price": 400000, "t_price": 200000},
                    {"cat": "폐기물", "item": "폐기물 처리", "spec": "폐기물 마대", "unit": "장", "qty": 1, "u_price": 5000, "t_price": 5000}
                ]
            },
            {
                "lvl": 4, "name": "바닥 덧방 시공 (Tile on Tile)", "diy": False,
                "duration": "1일", "tools": "타일 절단기, 레이저 레벨기",
                "desc": "기존 타일 위에 타일용 강력 접착제를 사용하여 새 타일을 덧붙이는 공법입니다.",
                "steps": ["바닥 청소", "높이 조절", "본드 도포", "타일 압착", "줄눈 시공"],
                "estimate_detail": [
                    {"cat": "자재", "item": "논슬립 자기질 타일", "spec": "300x300 (1.5㎡)", "unit": "Box", "qty": 5, "u_price": 25000, "t_price": 125000},
                    {"cat": "자재", "item": "압착 시멘트", "spec": "드라이픽스 20kg", "unit": "포", "qty": 1, "u_price": 25000, "t_price": 25000},
                    {"cat": "자재", "item": "줄눈 시멘트", "spec": "비둘기색 2kg", "unit": "봉", "qty": 2, "u_price": 4000, "t_price": 8000},
                    {"cat": "부자재", "item": "타일 스페이서", "spec": "1.5mm 간격재", "unit": "봉", "qty": 1, "u_price": 5000, "t_price": 5000},
                    {"cat": "인건비", "item": "타일 기공", "spec": "1인 1일", "unit": "인", "qty": 1, "u_price": 350000, "t_price": 350000},
                    {"cat": "경비", "item": "식대 및 잡비", "spec": "-", "unit": "식", "qty": 1, "u_price": 30000, "t_price": 30000}
                ]
            },
            {
                "lvl": 5, "name": "전체 철거 및 방수/재시공", "diy": False,
                "duration": "3~4일", "tools": "뿌레카, 방수 믹서",
                "desc": "바닥층을 슬라브까지 완전 철거 후 3차 방수(액체+도막)를 새로 진행합니다. 누수를 원천 차단합니다.",
                "steps": ["전체 철거", "1차 액체 방수", "2차 도막 방수(고뫄스)", "담수 테스트", "타일 시공"],
                "estimate_detail": [
                    {"cat": "철거", "item": "철거 인건비", "spec": "바닥 전체 파쇄", "unit": "인", "qty": 1, "u_price": 300000, "t_price": 300000},
                    {"cat": "폐기물", "item": "폐콘크리트 처리", "spec": "1톤 트럭 분량", "unit": "대", "qty": 1, "u_price": 300000, "t_price": 300000},
                    {"cat": "자재", "item": "액체 방수액", "spec": "18L (완결)", "unit": "통", "qty": 1, "u_price": 40000, "t_price": 40000},
                    {"cat": "자재", "item": "고뫄스 (도막방수)", "spec": "18L", "unit": "통", "qty": 1, "u_price": 60000, "t_price": 60000},
                    {"cat": "자재", "item": "레미탈 (바닥용)", "spec": "40kg", "unit": "포", "qty": 10, "u_price": 6000, "t_price": 60000},
                    {"cat": "자재", "item": "타일/도기 세트", "spec": "중급형", "unit": "식", "qty": 1, "u_price": 800000, "t_price": 800000},
                    {"cat": "인건비", "item": "설비/방수/타일팀", "spec": "3일 소요", "unit": "식", "qty": 1, "u_price": 1200000, "t_price": 1200000}
                ]
            }
        ]
    },
    "wall_crack": {
        "title": "벽체/구조체 균열 (Wall Crack)",
        "grade": "주의 (Structural Issue)",
        "color": "#ff9800",
        "radar": [95, 80, 50, 40, 60],
        "risk_report": """
            **🚨 예상되는 문제점 및 영향 분석**<br>
            1. **구조 내력 저하**: 0.3mm 이상의 관통 균열은 건물의 지지력을 약화시킬 수 있습니다.<br>
            2. **외벽 누수**: 빗물이 균열을 타고 내부로 침투하여 콘크리트 중성화를 가속화합니다.
        """,
        "msg": "벽면의 균열은 건물의 움직임에 의해 발생합니다. 균열 깊이에 맞는 공법 선정이 중요합니다.",
        "best_pick": 3,
        "solutions": [
            {
                "lvl": 1, "name": "수성 코킹/퍼티 마감", "diy": True,
                "duration": "30분", "tools": "헤라, 수성실리콘, 사포",
                "desc": "페인트 도장 전 미세한 실금(0.1mm 이하)을 가리기 위한 작업입니다.",
                "steps": ["이물질 제거", "실리콘 도포", "평탄화", "샌딩", "부분 도장"],
                "estimate_detail": [
                    {"cat": "자재", "item": "수성 실리콘", "spec": "300ml(도장가능)", "unit": "개", "qty": 1, "u_price": 3000, "t_price": 3000},
                    {"cat": "도구", "item": "스크래퍼(헤라)", "spec": "플라스틱", "unit": "개", "qty": 1, "u_price": 1500, "t_price": 1500},
                    {"cat": "도구", "item": "사포(샌딩페이퍼)", "spec": "#220", "unit": "장", "qty": 2, "u_price": 500, "t_price": 1000},
                    {"cat": "마감", "item": "터치업 페인트", "spec": "소용량", "unit": "개", "qty": 1, "u_price": 5000, "t_price": 5000}
                ]
            },
            {
                "lvl": 2, "name": "크랙 보수 테이프 및 퍼티", "diy": True,
                "duration": "1시간", "tools": "망사 테이프, 퍼티, 헤라",
                "desc": "섬유질 망사 테이프를 붙여 재균열을 방지하고 퍼티로 면을 잡습니다.",
                "steps": ["테이프 부착", "1차 퍼티", "2차 퍼티", "샌딩"],
                "estimate_detail": [
                    {"cat": "자재", "item": "조인트 망사 테이프", "spec": "50mm x 90m", "unit": "롤", "qty": 1, "u_price": 5000, "t_price": 5000},
                    {"cat": "자재", "item": "핸디코트(퍼티)", "spec": "5kg", "unit": "통", "qty": 1, "u_price": 10000, "t_price": 10000},
                    {"cat": "도구", "item": "샌딩 블럭", "spec": "스펀지형", "unit": "개", "qty": 1, "u_price": 2000, "t_price": 2000},
                    {"cat": "도구", "item": "고무 헤라", "spec": "대형", "unit": "개", "qty": 1, "u_price": 2000, "t_price": 2000},
                    {"cat": "도구", "item": "퍼티판(트레이)", "spec": "플라스틱", "unit": "개", "qty": 1, "u_price": 3000, "t_price": 3000}
                ]
            },
            {
                "lvl": 3, "name": "V-컷팅 및 우레탄 씰링", "diy": False,
                "duration": "4시간", "tools": "4인치 그라인더, 코킹건",
                "desc": "균열 부위를 V자로 파내어 접착 면적을 넓힌 뒤 탄성 씰링재를 깊숙이 충전합니다.",
                "steps": ["V자 커팅", "프라이머 도포", "실란트 충전", "표면 마감"],
                "estimate_detail": [
                    {"cat": "자재", "item": "변성 우레탄 실란트", "spec": "500ml 소세지", "unit": "개", "qty": 5, "u_price": 8000, "t_price": 40000},
                    {"cat": "자재", "item": "전용 프라이머", "spec": "1L", "unit": "통", "qty": 1, "u_price": 15000, "t_price": 15000},
                    {"cat": "도구", "item": "그라인더 날", "spec": "V컷팅용", "unit": "개", "qty": 1, "u_price": 20000, "t_price": 20000},
                    {"cat": "인건비", "item": "방수/코킹 전문가", "spec": "0.5품", "unit": "인", "qty": 0.5, "u_price": 300000, "t_price": 150000}
                ]
            },
            {
                "lvl": 4, "name": "에폭시 저압 주사기 주입", "diy": False,
                "duration": "1일", "tools": "주사기 좌대, 에폭시 주입제",
                "desc": "콘크리트 내부 깊은 균열까지 에폭시 수지를 강제로 주입하여 일체화시킵니다.",
                "steps": ["좌대 부착", "주사기 설치", "주입 및 경화", "철거"],
                "estimate_detail": [
                    {"cat": "자재", "item": "에폭시 주입제", "spec": "주제/경화제 세트", "unit": "세트", "qty": 1, "u_price": 60000, "t_price": 60000},
                    {"cat": "자재", "item": "주입용 주사기", "spec": "저압용", "unit": "개", "qty": 30, "u_price": 800, "t_price": 24000},
                    {"cat": "자재", "item": "좌대", "spec": "부착용", "unit": "개", "qty": 30, "u_price": 200, "t_price": 6000},
                    {"cat": "자재", "item": "씰링제(에폭시퍼티)", "spec": "10kg", "unit": "캔", "qty": 1, "u_price": 40000, "t_price": 40000},
                    {"cat": "인건비", "item": "구조 보수 전문가", "spec": "1인 1일", "unit": "인", "qty": 1, "u_price": 300000, "t_price": 300000}
                ]
            },
            {
                "lvl": 5, "name": "탄소섬유 시트 구조 보강", "diy": False,
                "duration": "2일", "tools": "특수 롤러, 탈포기",
                "desc": "철보다 인장강도가 10배 강한 탄소섬유 시트를 부착하여 구조 내력을 복원합니다.",
                "steps": ["표면 그라인딩", "프라이머 도포", "시트 부착", "탈포", "마감"],
                "estimate_detail": [
                    {"cat": "자재", "item": "탄소섬유 시트", "spec": "1Layer 보강용", "unit": "롤", "qty": 1, "u_price": 300000, "t_price": 300000},
                    {"cat": "자재", "item": "함침 레진", "spec": "전용 주제/경화제", "unit": "세트", "qty": 1, "u_price": 150000, "t_price": 150000},
                    {"cat": "자재", "item": "프라이머", "spec": "고침투성", "unit": "캔", "qty": 1, "u_price": 50000, "t_price": 50000},
                    {"cat": "도구", "item": "탈포 롤러", "spec": "알루미늄", "unit": "개", "qty": 1, "u_price": 15000, "t_price": 15000},
                    {"cat": "인건비", "item": "특수 보강 시공팀", "spec": "2인 1일", "unit": "식", "qty": 1, "u_price": 700000, "t_price": 700000}
                ]
            }
        ]
    },
    "mold": {
        "title": "결로성 곰팡이 (Mold)",
        "grade": "위생 주의 (Health Risk)",
        "color": "#7cb342",
        "radar": [30, 60, 50, 95, 90],
        "risk_report": """
            **🚨 예상되는 문제점 및 영향 분석**<br>
            1. **호흡기 질환**: 포자가 공기 중에 떠다니며 비염, 천식, 알레르기를 유발합니다.<br>
            2. **마감재 부식**: 벽지와 석고보드가 습기에 젖어 썩어 들어가며, 방치 시 석고보드 교체가 필요할 수 있습니다.
        """,
        "msg": "곰팡이는 '결과'이고 원인은 '단열 부족'입니다. 단순 제거보다는 단열 페인트나 이보드 시공 같은 근본 대책이 필요합니다.",
        "best_pick": 4,
        "solutions": [
            {
                "lvl": 1, "name": "곰팡이 제거제 청소", "diy": True,
                "duration": "30분", "tools": "분무기, 마스크, 장갑",
                "desc": "표면의 곰팡이 포자를 화학적으로 사멸시키는 기초 작업입니다.",
                "steps": ["환기", "약품 분사", "살균 대기", "닦아내기"],
                "estimate_detail": [
                    {"cat": "자재", "item": "곰팡이 제거제", "spec": "500ml 강력형", "unit": "개", "qty": 2, "u_price": 7500, "t_price": 15000},
                    {"cat": "안전", "item": "KF94 마스크", "spec": "방역용", "unit": "개", "qty": 2, "u_price": 500, "t_price": 1000},
                    {"cat": "안전", "item": "고무장갑", "spec": "라텍스", "unit": "켤레", "qty": 1, "u_price": 2000, "t_price": 2000},
                    {"cat": "소모품", "item": "물티슈/걸레", "spec": "청소용", "unit": "팩", "qty": 1, "u_price": 2000, "t_price": 2000}
                ]
            },
            {
                "lvl": 2, "name": "규조토/단열 페인트 시공", "diy": True,
                "duration": "1일", "tools": "롤러, 붓, 트레이",
                "desc": "일반 수성 페인트가 아닌, 습기 조절 능력이 있는 규조토 또는 중공 안료가 들어간 단열 페인트를 시공합니다.",
                "steps": ["곰팡이 제거 및 건조", "프라이머(젯소) 도포", "단열 페인트 1차 도포", "건조(2시간)", "단열 페인트 2차 도포"],
                "estimate_detail": [
                    {"cat": "자재", "item": "곰팡이 제거제", "spec": "500ml 강력형", "unit": "개", "qty": 2, "u_price": 8000, "t_price": 16000},
                    {"cat": "자재", "item": "항균 프라이머", "spec": "1L (결합력 강화)", "unit": "통", "qty": 1, "u_price": 15000, "t_price": 15000},
                    {"cat": "자재", "item": "규조토/단열 페인트", "spec": "4L (인슐래드)", "unit": "통", "qty": 1, "u_price": 45000, "t_price": 45000},
                    {"cat": "도구", "item": "롤러", "spec": "7인치 수성용", "unit": "개", "qty": 2, "u_price": 3000, "t_price": 6000},
                    {"cat": "도구", "item": "붓", "spec": "2인치 틈새용", "unit": "개", "qty": 1, "u_price": 2000, "t_price": 2000},
                    {"cat": "도구", "item": "페인트 트레이", "spec": "7인치용", "unit": "개", "qty": 1, "u_price": 3000, "t_price": 3000},
                    {"cat": "부자재", "item": "커버링 테이프", "spec": "보양 비닐(1500mm)", "unit": "롤", "qty": 1, "u_price": 2500, "t_price": 2500}
                ]
            },
            {
                "lvl": 3, "name": "접착식 단열 벽지 시공", "diy": True,
                "duration": "3시간", "tools": "가위, 칼, 줄자",
                "desc": "알루미늄 증착 필름과 PE폼이 부착된 스티커형 벽지를 붙여 냉기를 차단합니다.",
                "steps": ["기존 벽지 제거", "벽면 사이즈 측정", "이면지 제거 후 부착", "실리콘 마감"],
                "estimate_detail": [
                    {"cat": "자재", "item": "고급 단열 벽지", "spec": "1m x 20m (5mm)", "unit": "롤", "qty": 1, "u_price": 60000, "t_price": 60000},
                    {"cat": "자재", "item": "바이오 실리콘", "spec": "틈새 마감용", "unit": "개", "qty": 2, "u_price": 4000, "t_price": 8000},
                    {"cat": "도구", "item": "커터칼", "spec": "대형", "unit": "개", "qty": 1, "u_price": 1000, "t_price": 1000},
                    {"cat": "도구", "item": "줄자", "spec": "5m", "unit": "개", "qty": 1, "u_price": 3000, "t_price": 3000}
                ]
            },
            {
                "lvl": 4, "name": "복합 단열재(이보드) + 마감", "diy": False,
                "duration": "1일", "tools": "타카, 우레탄 폼건, 컷터",
                "desc": "아이소핑크와 PP보드가 결합된 '이보드'를 부착하여 단열성을 높이고, 그 위에 도배나 페인트로 최종 마감합니다.",
                "steps": ["벽지/곰팡이 제거", "이보드 재단 및 부착(G2본드)", "이음새 폼 충전", "실리콘 마감", "최종 도배/페인트"],
                "estimate_detail": [
                    {"cat": "자재", "item": "이보드 (복합단열재)", "spec": "23mm (900x2400)", "unit": "장", "qty": 4, "u_price": 30000, "t_price": 120000},
                    {"cat": "자재", "item": "G2 전용 본드", "spec": "10kg", "unit": "통", "qty": 1, "u_price": 25000, "t_price": 25000},
                    {"cat": "자재", "item": "우레탄 폼", "spec": "충전용 750ml", "unit": "캔", "qty": 2, "u_price": 8000, "t_price": 16000},
                    {"cat": "자재", "item": "바이오 실리콘", "spec": "항균 (틈새마감)", "unit": "개", "qty": 3, "u_price": 5000, "t_price": 15000},
                    {"cat": "도구", "item": "우레탄 폼건", "spec": "전용 건", "unit": "개", "qty": 1, "u_price": 15000, "t_price": 15000},
                    {"cat": "도구", "item": "실리콘 건", "spec": "회전형", "unit": "개", "qty": 1, "u_price": 5000, "t_price": 5000},
                    {"cat": "인건비", "item": "내장 목수", "spec": "1인 1일", "unit": "인", "qty": 1, "u_price": 350000, "t_price": 350000},
                    {"cat": "마감자재", "item": "단열 벽지/도배지", "spec": "광폭 합지", "unit": "롤", "qty": 2, "u_price": 25000, "t_price": 50000},
                    {"cat": "마감시공", "item": "도배 시공비", "spec": "인건비 포함", "unit": "식", "qty": 1, "u_price": 150000, "t_price": 150000},
                    {"cat": "폐기물", "item": "폐자재 처리", "spec": "마대 5장 분량", "unit": "식", "qty": 1, "u_price": 30000, "t_price": 30000}
                ]
            },
            {
                "lvl": 5, "name": "가벽 조성(목상+XPS) 고단열 공사", "diy": False,
                "duration": "2일", "tools": "목공 장비 일체",
                "desc": "목재 틀(목상)을 세우고 아이소핑크를 채운 뒤 석고보드로 덮는 최상급 단열법입니다. 마감은 규조토 페인트나 실크벽지를 추천합니다.",
                "steps": ["열반사 단열재 부착", "목상 틀 조성", "단열재 충전", "석고보드 2P 마감", "퍼티/샌딩", "최종 마감(도장/도배)"],
                "estimate_detail": [
                    {"cat": "자재", "item": "소송 다루끼(목재)", "spec": "30x30x3600", "unit": "단", "qty": 2, "u_price": 40000, "t_price": 80000},
                    {"cat": "자재", "item": "아이소핑크(XPS)", "spec": "50mm 특호", "unit": "장", "qty": 6, "u_price": 16000, "t_price": 96000},
                    {"cat": "자재", "item": "석고보드", "spec": "9.5T (3x6)", "unit": "장", "qty": 10, "u_price": 5000, "t_price": 50000},
                    {"cat": "부자재", "item": "목공 본드/타카핀", "spec": "205본드 외", "unit": "식", "qty": 1, "u_price": 30000, "t_price": 30000},
                    {"cat": "인건비", "item": "목수 팀장", "spec": "기공", "unit": "일", "qty": 2, "u_price": 400000, "t_price": 800000},
                    {"cat": "인건비", "item": "목수 조공", "spec": "보조", "unit": "일", "qty": 2, "u_price": 200000, "t_price": 400000},
                    {"cat": "마감자재", "item": "규조토 페인트", "spec": "10L (고급형)", "unit": "통", "qty": 1, "u_price": 120000, "t_price": 120000},
                    {"cat": "마감자재", "item": "줄퍼티/조인트테이프", "spec": "크랙 방지용", "unit": "식", "qty": 1, "u_price": 40000, "t_price": 40000},
                    {"cat": "마감시공", "item": "도장공 인건비", "spec": "퍼티/샌딩/칠", "unit": "인", "qty": 1, "u_price": 250000, "t_price": 250000}
                ]
            }
        ]
    }
}

# --------------------------------------------------------------------------
# [3] 유틸리티 및 PDF 생성 함수
# --------------------------------------------------------------------------
@st.cache_resource
def load_model():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'model_final.pt')
        device = torch.device('cpu')
        model = torch.load(file_path, map_location=device, weights_only=False)
        model.eval()
        return model
    except:
        return None

def process_image(image):
    tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    return tf(image).unsqueeze(0)

def apply_ai_filter(image):
    gray = ImageOps.grayscale(image)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return ImageOps.colorize(edges, black="white", white="#ff4b4b")

def make_radar_chart(values, color):
    categories = ['구조적 위험', '시공 난이도', '예상 비용', '건강 위협', '미관 손상']
    fig = go.Figure(go.Scatterpolar(r=values, theta=categories, fill='toself', line_color=color))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, height=220, margin=dict(t=20,b=20,l=40,r=40))
    return fig

def create_cost_summary(solutions):
    summary_data = []
    for sol in solutions:
        total = 0
        if 'estimate_detail' in sol:
            for item in sol['estimate_detail']:
                total += item['t_price']
        summary_data.append({
            "등급": f"Lv.{sol['lvl']}",
            "시공법": sol['name'],
            "유형": "DIY" if sol['diy'] else "전문가",
            "총 비용": total
        })
    return pd.DataFrame(summary_data)

# --------------------------------------------------------------------------
# [★핵심] PDF 생성 로직 (상세 견적 테이블 - 자재/도구/마감 분리 반영)
# --------------------------------------------------------------------------
def create_pdf_bytes(sol, defect_title):
    """
    상세 견적 항목(규격, 단위, 수량, 단가)이 포함된 전문적인 PDF 생성
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=20*mm, bottomMargin=20*mm)
    elements = []

    # 스타일 설정
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('TitleKR', parent=styles['Title'], fontName=KOREAN_FONT, fontSize=22, spaceAfter=20)
    style_heading = ParagraphStyle('HeadingKR', parent=styles['Heading2'], fontName=KOREAN_FONT, fontSize=14, spaceAfter=10, textColor=colors.HexColor('#0d47a1'))
    style_body = ParagraphStyle('BodyKR', parent=styles['BodyText'], fontName=KOREAN_FONT, fontSize=10, leading=16)
    style_caption = ParagraphStyle('CaptionKR', parent=styles['Normal'], fontName=KOREAN_FONT, fontSize=9, textColor=colors.gray)

    # 1. 제목 및 기본 정보
    elements.append(Paragraph(f"AI 시공 진단 및 견적 보고서", style_title))
    elements.append(Paragraph(f"진단 항목: {defect_title}", style_heading))
    elements.append(Spacer(1, 5*mm))
    
    # 솔루션 요약
    info_text = f"""
    <b>선택된 시공법:</b> Lv.{sol['lvl']} {sol['name']}<br/>
    <b>시공 유형:</b> {'DIY (자가시공)' if sol['diy'] else '전문가 시공'}<br/>
    <b>예상 소요 시간:</b> {sol['duration']}<br/>
    <b>필요 장비:</b> {sol['tools']}
    """
    elements.append(Paragraph(info_text, style_body))
    elements.append(Spacer(1, 5*mm))
    
    elements.append(Paragraph(f"상세 작업 설명", style_heading))
    elements.append(Paragraph(sol['desc'], style_body))
    elements.append(Spacer(1, 8*mm))

    # 시공 과정
    elements.append(Paragraph("📋 작업 순서 (Process)", style_heading))
    list_items = []
    for step in sol['steps']:
        list_items.append(ListItem(Paragraph(step, style_body)))
    
    list_flowable = ListFlowable(
        list_items,
        bulletType='1', 
        start=1,
        leftIndent=10,
        bulletFontName=KOREAN_FONT,
        bulletFontSize=10,
        bulletColor=colors.black
    )
    elements.append(list_flowable)
    elements.append(Spacer(1, 10*mm))

    # 2. 상세 견적서 테이블 (컬럼 세분화)
    elements.append(Paragraph("📋 상세 견적서 (Detailed Estimate)", style_heading))
    
    # 헤더: No, 구분, 품목, 규격, 단위, 수량, 단가, 금액
    data = [['No', '구분', '품목 (Item)', '규격 (Spec)', '단위', '수량', '단가 (Unit)', '금액 (Total)']]
    
    total_cost = 0
    if 'estimate_detail' in sol:
        for idx, item in enumerate(sol['estimate_detail']):
            t_price = item['t_price']
            total_cost += t_price
            
            data.append([
                str(idx + 1),
                item['cat'],
                item['item'],
                item['spec'],
                item['unit'],
                str(item['qty']),
                f"{item['u_price']:,}",
                f"{t_price:,}"
            ])
    
    # 합계 행
    data.append(['', '', '', '', '', '', '총 합계 (Total)', f"{total_cost:,} 원"])

    # 테이블 너비 설정
    col_widths = [10*mm, 15*mm, 45*mm, 40*mm, 15*mm, 15*mm, 20*mm, 25*mm]
    
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), KOREAN_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -2), 'LEFT'),   # 품목명 좌측
        ('ALIGN', (3, 1), (3, -2), 'LEFT'),   # 규격 좌측
        ('ALIGN', (-2, 1), (-1, -2), 'RIGHT'), # 숫자 우측
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # 디자인
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f3f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTWEIGHT', (0, 0), (-1, 0), 'BOLD'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
        
        # 합계 행 스타일
        ('BACKGROUND', (-2, -1), (-1, -1), colors.HexColor('#fff9db')),
        ('FONTSIZE', (-2, -1), (-1, -1), 10),
        ('FONTNAME', (-2, -1), (-1, -1), KOREAN_FONT),
        ('TEXTCOLOR', (-1, -1), (-1, -1), colors.HexColor('#d63384')),
        ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#fab005')),
        ('SPAN', (0, -1), (5, -1)), # 합계 라벨 셀 병합
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph("* 본 견적은 표준 품셈 및 시장 단가 기준이며, 마감 자재(페인트/벽지)의 등급에 따라 비용은 변동될 수 있습니다.", style_caption))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def render_combined_document(sol):
    """
    [HTML 렌더링] 화면 표시용 - 심플 카드 뷰
    """
    desc = sol['desc']
    duration = sol['duration']
    tools = sol['tools']
    
    steps_html = "<br>".join([f"&nbsp;&nbsp;<b>{i+1}.</b> {step}" for i, step in enumerate(sol['steps'])])
    
    total_cost = 0
    if 'estimate_detail' in sol:
        for item in sol['estimate_detail']:
            total_cost += item['t_price']
            
    return f"""
    <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef; margin-bottom: 20px;">
        <div style="margin-bottom:15px; font-size:1rem; line-height:1.5; color:#212529;">
            <b>💡 작업 설명:</b><br>
            <span style="color:#495057;">{desc}</span>
        </div>
        
        <div style="margin-bottom:15px; display:flex; gap:10px; flex-wrap:wrap;">
            <span style="background-color:#e3f2fd; padding:6px 10px; border-radius:6px; color:#0d47a1; font-size:0.9rem;">
                <b>⏱️ 소요 시간:</b> {duration}
            </span>
            <span style="background-color:#fff3e0; padding:6px 10px; border-radius:6px; color:#e65100; font-size:0.9rem;">
                <b>🛠️ 필요 장비:</b> {tools}
            </span>
            <span style="background-color:#e8f5e9; padding:6px 10px; border-radius:6px; color:#2e7d32; font-size:0.9rem;">
                <b>💰 예상 비용:</b> {total_cost:,} 원
            </span>
        </div>

        <div style="background:#ffffff; padding:15px; border-radius:6px; border:1px solid #dee2e6;">
            <b style="color:#1971c2;">📋 시공 프로세스 (Process):</b>
            <div style="margin-top:10px; line-height:1.6; color:#495057; font-size:0.95rem;">
                {steps_html}
            </div>
        </div>
        
        <div style="margin-top:12px; text-align:right; font-size:0.85rem; color:#868e96;">
            ※ 자재 규격, 마감재(페인트/도배) 비용 등 <b>상세 내역은 PDF 견적서</b>를 다운로드하여 확인하세요.
        </div>
    </div>
    """

# --------------------------------------------------------------------------
# [4] 메인 앱 로직
# --------------------------------------------------------------------------
def main():
    with st.sidebar:
        st.title("⚙️ 설정 (Settings)")
        st.write("진단 정확도를 위해 촬영 부위를 선택해주세요.")
        location_context = st.radio(
            "촬영 부위 (Location)",
            ("화장실/바닥 타일", "실내 벽면/천장", "베란다/발코니"),
            index=0
        )
        st.info(f"선택된 모드: **{location_context}**")
        st.divider()
        st.caption("AI Construction Diagnosis v2.4")

    st.title("🏗️ AI 하자 진단 Pro (Cost Analyzer)")
    st.markdown("---")
    
    model = load_model()
    
    col_up1, col_up2 = st.columns([1, 2])
    with col_up1:
        uploaded_file = st.file_uploader("현장 사진 업로드", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        image = Image.open(uploaded_file).convert('RGB')
        filename = os.path.splitext(uploaded_file.name)[0] 
        
        with st.status("🔍 AI Vision Analyzing...", expanded=True) as status:
            time.sleep(0.5)
            st.write("1. 이미지 전처리 및 노이즈 제거 중...")
            
            # 테스트 모드 (하드코딩)
            # 1) 타일 테스트
            if filename == "crack_test":
                 final_scenario_key = "tile_crack"
                 SCENARIOS[final_scenario_key]["best_pick"] = 5
                 st.write(f"2. 테스트 모드 감지: '{filename}'")
                 time.sleep(0.5)
                 st.write("-> 강제 설정: 화장실 바닥 전체 철거 (Lv.5)")
                 
            # 2) 곰팡이 테스트 (요청하신 부분)
            elif filename == "mold_test":
                 final_scenario_key = "mold"
                 SCENARIOS["mold"]["best_pick"] = 4
                 st.write(f"2. 테스트 모드 감지: '{filename}'")
                 time.sleep(0.5)
                 st.write("-> 강제 설정: 결로성 곰팡이 (Lv.4)")
                 
            # 3) 일반 모드 (AI 추론)
            else:
                prediction_label = "crack"
                if model:
                    try:
                        outputs = model(process_image(image))
                        probs = torch.nn.functional.softmax(outputs, dim=1)
                        conf, idx = torch.max(probs, 1)
                        raw_label = ['crack', 'mold'][idx.item()]
                        prediction_label = raw_label
                    except:
                        pass
                
                # 시나리오 결정
                final_scenario_key = "tile_crack" # Default
                if prediction_label == "mold":
                    final_scenario_key = "mold"
                else:
                    if "화장실" in location_context or "바닥" in location_context:
                        final_scenario_key = "tile_crack"
                    else:
                        final_scenario_key = "wall_crack"
                
                # 곰팡이일 경우 Lv.4 추천
                if final_scenario_key == "mold":
                    SCENARIOS["mold"]["best_pick"] = 4
                else:
                    SCENARIOS["tile_crack"]["best_pick"] = 4

                st.write(f"2. 결함 유형 분류: {final_scenario_key.upper()}")

            time.sleep(0.5)
            st.write("3. 마감재 포함 상세 견적 산출 중...")
            status.update(label="✅ 진단 완료!", state="complete", expanded=False)

        data = SCENARIOS.get(final_scenario_key, SCENARIOS['tile_crack'])
        
        c1, c2, c3 = st.columns([1, 1, 1.2])
        with c1:
            st.image(image, caption="Original Image", use_container_width=True)
        with c2:
            st.image(apply_ai_filter(image), caption="AI Defect Detection", use_container_width=True)
        with c3:
            st.subheader(f"📊 {data['title']}")
            st.plotly_chart(make_radar_chart(data['radar'], data['color']), use_container_width=True)

        # ------------------------------------------------------------------
        # [NEW] 타자기 효과 (Streaming Effect) 적용 부분
        # ------------------------------------------------------------------
        
        # 1. Risk Report (HTML 박스 + 타자기 효과)
        # HTML 태그 파손 방지를 위해 '단어 단위'로 쪼개서 출력
        risk_placeholder = st.empty()
        
        def render_risk_box(content):
            risk_placeholder.markdown(f"""
                <div class="risk-box">
                    <div class="risk-title">⚠️ Risk Analysis Report</div>
                    {content}
                </div>
            """, unsafe_allow_html=True)

        time.sleep(0.5)
        
        full_risk_text = data['risk_report']
        curr_risk_text = ""
        
        # 단어(공백) 단위로 루프
        for chunk in full_risk_text.split(' '):
            curr_risk_text += chunk + " "
            render_risk_box(curr_risk_text + "▌") # 커서 효과 추가
            time.sleep(0.04) # 출력 속도 조절
            
        render_risk_box(full_risk_text) # 커서 제거된 최종본 출력

        # 2. AI 종합 소견 (Info 박스 + 타자기 효과)
        # 일반 텍스트이므로 '글자 단위'로 자연스럽게 출력
        st.write("") # 여백
        info_placeholder = st.empty()
        
        full_msg = f"**💡 AI 종합 소견:** {data['msg']}"
        curr_msg = ""
        
        for char in full_msg:
            curr_msg += char
            info_placeholder.info(curr_msg + "▌")
            time.sleep(0.02) # 출력 속도 조절
            
        info_placeholder.info(full_msg) # 최종본 출력

        # ------------------------------------------------------------------
        # [End of NEW Effect]
        # ------------------------------------------------------------------

        st.divider()
        
        st.markdown("### 💰 솔루션별 예상 비용 비교")
        df_summary = create_cost_summary(data['solutions'])
        col_chart, col_table = st.columns([1.5, 1])
        with col_chart:
            fig_bar = px.bar(df_summary, x='등급', y='총 비용', text_auto=',', color='유형', 
                             color_discrete_map={'DIY': '#82c91e', '전문가': '#ff6b6b'},
                             title=f"{data['title']} 단계별 견적 비교")
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(yaxis_tickformat=",", height=320)
            st.plotly_chart(fig_bar, use_container_width=True)
        with col_table:
            st.dataframe(df_summary[['등급', '시공법', '유형', '총 비용']], 
                         column_config={"총 비용": st.column_config.NumberColumn("예상 견적", format="%d 원")}, 
                         hide_index=True, use_container_width=True, height=320)
            
        st.divider()

        st.markdown("### 🛠️ 시공 솔루션 및 통합 견적서")
        best_lvl = data.get('best_pick', 1)
        
        for sol in data['solutions']:
            is_best = (sol['lvl'] == best_lvl)
            prefix = "🏆 [추천] " if is_best else ""
            
            badges = ""
            if sol['diy']: badges += "<span class='badge-base badge-diy'>DIY 가능</span>"
            else: badges += "<span class='badge-base badge-pro'>전문가 시공</span>"
            if is_best: badges += "<span class='badge-base badge-best'>AI 강력 추천</span>"
            
            expander_title = f"{prefix}Lv.{sol['lvl']} {sol['name']}"
            
            with st.expander(expander_title, expanded=is_best):
                st.markdown(badges, unsafe_allow_html=True)
                st.markdown(render_combined_document(sol), unsafe_allow_html=True)
                
                pdf_data = create_pdf_bytes(sol, data['title'])
                
                btn_col1, btn_col2 = st.columns([4, 1])
                with btn_col2:
                    st.download_button(
                        label="📄 PDF 견적서 다운로드",
                        data=pdf_data,
                        file_name=f"상세견적서_Lv{sol['lvl']}_{sol['name']}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

    else:
        st.markdown("""
            <div style='text-align: center; padding: 80px; color: #666;'>
                <h1>📸 진단할 사진을 업로드해주세요</h1>
                <p>화장실 타일 깨짐, 벽면 곰팡이 등을 분석하여<br><b>자재/마감재까지 포함된 상세 견적서</b>를 제공합니다.</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()