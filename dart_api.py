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

# 분기별 제무재표에서 필요한 정보만 추출해서 DataFrame에 할당하여 return 하는 함수
def finstate_quarter(finstate_df):
    # 재무제표에서 자본변동표(SCE) 삭제
    rev_data = list(reversed(finstate_df.index))
    del_row = []
    for i in rev_data:
        if finstate_df.loc[i, "sj_div"] == "SCE":
            del_row.append(i)
    finstate_df = finstate_df.drop(index=del_row)
    # 분기별 재무제표에서 필요한 columns만으로 table 생성
    finstate_df = finstate_df[["corp_code", "sj_div", "account_id", "account_nm", "thstrm_amount"]]
    finstate_df["thstrm_amount"] = pd.to_numeric(finstate_df.thstrm_amount, errors="coerce", downcast="float") 
    
    return finstate_df

# 각 연도마다 분기별 재무제표 데이터를 dataframe에 할당하는 함수
def finstate_all_account(api_key, corp_code, years, quarters):
    for bsns_year in years:
        quarter = 1
        for reprt_code in quarters:
            fstate = finstate_all(api_key, corp_code, bsns_year, reprt_code, fs_div="CFS")
            fstate = finstate_quarter(fstate).rename(columns={"thstrm_amount": f'thstrm_amount_{bsns_year}_{quarter}'})
            # 계정이름 중복되는 행 삭제
            fstate = fstate.drop_duplicates(["sj_div", "account_nm"], keep=False, ignore_index=True)

            if quarter == 1:
                fstate_corp = fstate
            else:
                fstate_corp = fstate_corp.merge(fstate, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
            fstate_corp = fstate_corp.fillna(0)

            if quarter == 4:
                # 4분기 발생 금액 columns 추가
                i = 0
                for s in fstate_corp.sj_div:
                    if s == "BS":
                        fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] = fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}']
                    else:
                        fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] = fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] - fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter-1}']
                    i += 1
            quarter += 1

        if bsns_year == years[0]:
            fstate_all_account = fstate_corp
        else:
            fstate_all_account = fstate_all_account.merge(fstate_corp, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
    
    return fstate_all_account




