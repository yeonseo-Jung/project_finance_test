import io
from io import BytesIO
import zipfile
import requests
import json
import xml.etree.ElementTree as ET
import pandas as pd


try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize

# 다중회사 주요계정 출력 함수
def finstate(api_key, corp_code, bsns_year, reprt_code):
    url = "https://opendart.fss.or.kr/api/"
    url += "fnlttMultiAcnt.json" if "," in corp_code else "fnlttSinglAcnt.json"
    
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year":  bsns_year,   # 사업년도
        "reprt_code": reprt_code, # 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011"       
    }
    
    r = requests.get(url, params=params)
    jo = json.loads(r.text)
    if "list" not in jo:
        return None
    return json_normalize(jo, "list")

# 회사 고유번호 및 회사명 출력 함수 
def corp_codes(api_key):
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = { "crtfc_key": api_key, }
    
    r = requests.get(url, params=params)
    
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    xml_data = zf.read("CORPCODE.xml")
    
    # XML to DataFrame
    tree = ET.XML(xml_data)
    all_records = []
    
    element = tree.findall("list")
    for i, child in enumerate(element):
        record = {}
        for i, subchild in enumerate(child):
            record[subchild.tag] = subchild.text
        all_records.append(record)
    return pd.DataFrame(all_records)  

# 단일회사 전체 재무제표 출력 함수
def finstate_all(api_key, corp_code, bsns_year, reprt_code, fs_div="CFS"):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year":  bsns_year,   # 사업년도
        "reprt_code": reprt_code, # 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011" 
        "fs_div": fs_div, # 연결재무제표: "CFS", 재무제표: "OFS"
    }
    
    r = requests.get(url, params=params)
    jo = json.loads(r.text)
    if "list" not in jo:
        return None
    return json_normalize(jo, "list")

# XBRL 표준계정과목체계(계정과목)
def xbrl_taxonomy(api_key, sj_div='BS1'):
    url = 'https://opendart.fss.or.kr/api/xbrlTaxonomy.json'
    params = {
        'crtfc_key': api_key,
        'sj_div': sj_div, # "CFS":연결재무제표, "OFS":재무제표
    }
    r = requests.get(url, params=params)
    jo = json.loads(r.text)
    if 'list' not in jo:
        return None
    return json_normalize(jo, 'list')






