import pandas as pd
import os
import requests
import zipfile
import io
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import OpenDartReader

try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize




# 재무제표를 종류별로 분류하여 각각 DataFrame으로 return 해주는 함수
def finstate_classify(finstate):
    # 재무제표 데이터가 None
    try:
        # 금액 관련 columns의 자료형을 object에서 float으로 변경
        amounts = ["thstrm_amount", "thstrm_add_amount", "frmtrm_amount", "frmtrm_q_amount", "frmtrm_add_amount"]
        for s in amounts:
            # reprt_code가 11011(사업보고서)인 경우 예외처리
            try:
                finstate[s] = pd.to_numeric(finstate[s], errors="coerce", downcast="float")
            except KeyError:
                continue

        # BS: 재무상태표, IS: 손익계산서, CIS: 포괄손익계산서, CF: 현금흐름표, SCE: 자본변동표
        fstate_bs = pd.DataFrame(columns=finstate.columns)
        fstate_is = pd.DataFrame(columns=finstate.columns)
        fstate_cis = pd.DataFrame(columns=finstate.columns)
        fstate_cf = pd.DataFrame(columns=finstate.columns)
        fstate_sce = pd.DataFrame(columns=finstate.columns)

        i = 0
        for s in finstate["sj_div"]:
            if s == "BS":
                fstate_bs = fstate_bs.append(finstate.loc[i], ignore_index=True)
            elif s == "IS":
                fstate_is = fstate_is.append(finstate.loc[i], ignore_index=True)
            elif s == "CIS":
                fstate_cis = fstate_cis.append(finstate.loc[i], ignore_index=True)
            elif s == "CF":
                fstate_cf = fstate_cf.append(finstate.loc[i], ignore_index=True)
            elif s == "SCE":
                fstate_sce = fstate_sce.append(finstate.loc[i], ignore_index=True)
            i += 1    
        
        # dataframe에 데이터가 할당 된 재무제표만 return
        a = [fstate_bs, fstate_is, fstate_cis, fstate_cf, fstate_sce]
        finstates = []
        for fs in a:
            if len(fs) == 0:
                pass
            else:
                finstates.append(fs)
    
                
        return finstates
    
    except TypeError:
        return None


# 단일회사 분기별 전체 재무제표를 종류별로 할당해서 엑셀로 저장해주는 함수 
def finstate_all(dart, stock_name, stock_code, bsns_year, reprt_code, path):
    # dart api에서 단일회사 전체 재무제표 호출한 후 종류별로 분류해서 dataframe에 할당
    fstate = dart.finstate_all(stock_name, bsns_year, reprt_code, fs_div="CFS")
    fstates = finstate_classify(fstate)
    
    # 'fstates'에 할당 된 데이터가 없을 땐 pass
    if fstates == None:
        pass
    else:
        # DataFrame을 엑셀로 저장
        for fs in fstates:
            kind = fs.loc[0, "sj_div"]
            kind = kind.lower()
            fs.to_excel(f"{path}/{stock_code}_{kind}_{bsns_year}_{reprt_code}.xlsx")


# 새로운 계정과목 {nm: id} 등록
# 기존에 등록되어 있는 계정과목의 id추가 
def make_accounts(account_nm, account_id, path):
    # 'accounts.txt' 파일을 딕셔너리 자료형으로 할당하기 
    accounts = {}
    with open(f'{path}/accounts.txt', 'r') as f:
        for line in f:
            lines = line.split(",")
            accounts[lines[0]] = lines[1:]

    # 새로운 계정과목 {nm: id} 등록
    if not account_nm in accounts.keys():
        with open(f'{path}/accounts.txt', "a") as f:
            f.write(account_nm+",")
            i = 0
            for val in account_id:
                if i == len(account_id) - 1:
                    f.write(val+"\n")
                else:
                    f.write(val+",")
                i += 1

    # 기존에 등록되어 있는 계정과목의 id추가 
    else:
        for ac_id in account_id:
            accounts[account_nm].append(ac_id)     


# dart에 공시되어 있는 모든 회사들의 기업개황을 dataframe에 할당하는 함수
def corp_codes(api_key):
        url = 'https://opendart.fss.or.kr/api/corpCode.xml'
        params = { 'crtfc_key': api_key, }

        r = requests.get(url, params=params)
        try:
            tree = ET.XML(r.content)
            status = tree.find('status').text
            message = tree.find('message').text
            if status != '000':
                raise ValueError({'status': status, 'message': message})
        except ET.ParseError as e:
            pass

        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xml_data = zf.read('CORPCODE.xml')

        # XML to DataFrame
        tree = ET.XML(xml_data)
        all_records = []

        element = tree.findall('list')
        for i, child in enumerate(element):
            record = {}
            for i, subchild in enumerate(child):
                record[subchild.tag] = subchild.text
            all_records.append(record)
        return pd.DataFrame(all_records)


