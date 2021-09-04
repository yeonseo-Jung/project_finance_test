#!/usr/bin/env python
# coding: utf-8

# In[135]:


import requests
import zipfile
import io
import os
import json
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize


# In[17]:


import OpenDartReader
api_key = "ef3149d745caee09f48df5004b905ec4ef3f5d7e"
dart = OpenDartReader(api_key)


# In[9]:


# CIS 계정과목 id
"""
영업수익(매출): "ifrs-full_Revenue" or "ifrs-full_GrossProfit"
영업이익: "dart_OperatingIncomeLoss"
법인세비용차감전순이익: "ifrs-full_ProfitLossBeforeTax"
계속영업순이익: "ifrs-full_ProfitLossFromContinuingOperations"
지배기업의 소유주에게 귀속되는 당기순이익: "ifrs-full_ProfitLossAttributableToOwnersOfParent" or ifrs_ProfitLossAttributableToOwnersOfParent
비지배지분에 귀속되는 당기순이익: "ifrs_ProfitLossAttributableToNoncontrollingInterests"
지배기업의 소유주에게 귀속되는 총포괄손익: "ifrs-full_ComprehensiveIncomeAttributableToOwnersOfParent"
비지배지분에 귀속되는 총포괄손익: "ifrs-full_ComprehensiveIncomeAttributableToNoncontrollingInterests"
기본주당이익: "ifrs-full_BasicEarningsLossPerShare"
희석주당이익: "ifrs-full_DilutedEarningsLossPerShare"
"""

# BS 계정과목 id
"""
자산총계: "ifrs-full_Assets" 
부채총계: "ifrs-full_Liabilities"
자본총계: "ifrs-full_Equity" or "ifrs_Equity"
지배기업의 소유주에게 귀속되는 자본: "ifrs-full_EquityAttributableToOwnersOfParent" or "ifrs_EquityAttributableToOwnersOfParent"
비지배지분: "ifrs-full_NoncontrollingInterests" or "ifrs_NoncontrollingInterests"
자본금: "ifrs-full_IssuedCapital" or "ifrs_IssuedCapital"
보통주자본금: "dart_IssuedCapitalOfCommonStock"
우선주자본금: "dart_IssuedCapitalOfPreferredStock"
이익잉여금: "ifrs-full_RetainedEarnings"
"""


# In[10]:


# 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011"


# In[136]:


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


# In[54]:


# 재무제표를 종류별로 분류하여 각각 DataFrame으로 return 해주는 함수
def finstate_classify(finstate):
    # BS : 재무상태표, IS: 손익계산서, CIS : 포괄손익계산서, CF : 현금흐름표, SCE : 자본변동표
    finstate_bs = pd.DataFrame(columns=finstate.columns)
    finstate_is = pd.DataFrame(columns=finstate.columns)
    finstate_cis = pd.DataFrame(columns=finstate.columns)
    finstate_cf = pd.DataFrame(columns=finstate.columns)
    finstate_sce = pd.DataFrame(columns=finstate.columns)
    i = 0
    for s in finstate["sj_div"]:
        if s == "BS":
            finstate_bs = finstate_bs.append(finstate.loc[i], ignore_index=True)
        elif s == "IS":
            finstate_is = finstate_is.append(finstate.loc[i], ignore_index=True)
        elif s == "CIS":
            finstate_cis = finstate_cis.append(finstate.loc[i], ignore_index=True)
        elif s == "CF":
            finstate_cf = finstate_cf.append(finstate.loc[i], ignore_index=True)
        elif s == "SCE":
            finstate_sce = finstate_sce.append(finstate.loc[i], ignore_index=True)
        i += 1    
    return finstate_bs, finstate_is, finstate_cis, finstate_cf, finstate_sce


# In[55]:


# 분기별 제무재표 데이터를 필요한 columns만 추출해서 table에 할당하여 return 
def finstate_quarter(finstate_df):
    try:
        # 재무제표에서 자본변동표(SCE) 삭제
        rev_data = list(reversed(finstate_df.index))
        del_row = []
        for i in rev_data:
            if finstate_df.loc[i, "sj_div"] == "SCE":
                del_row.append(i)
        finstate_df = finstate_df.drop(index=del_row)
        # 분기별 재무제표에서 필요한 columns만으로 table 생성
        fstate_quarter = finstate_df[["corp_code", "sj_div", "account_id", "account_nm", "thstrm_amount"]]
        fstate_quarter["thstrm_amount"] = pd.to_numeric(finstate_df.thstrm_amount, errors="coerce", downcast="float") 

        return fstate_quarter
    except AttributeError:
        return None


# In[112]:


# 분기별 재무제표를 병합해서 DataFrame으로 return 해주는 함수 
def finstate_all_account(stock_name, years, quarters):
    for bsns_year in years:
        quarter = 1
        for reprt_code in quarters:
            # fstate 변수에 할당된 데이터가 없을 때(즉, 해당 연도 분기의 재무제표가 dart에 공시되어 있지 않은 경우) 예외처리
            try:
                fstate = dart.finstate_all(stock_name, bsns_year, reprt_code, fs_div="CFS")
                fstate = finstate_quarter(fstate).rename(columns={"thstrm_amount": f'thstrm_amount_{bsns_year}_{quarter}'})
                # stock_name, stock_code columns 삽입
                if dart.company(stock_name)["corp_cls"] == "Y":
                    stock_code = dart.company(stock_name)["stock_code"] + ".KS"
                elif dart.company(stock_name)["corp_cls"] == "K":
                    stock_code = dart.company(stock_name)["stock_code"] + ".KQ"
                fstate.insert(0, "stock_code", stock_code)
                fstate.insert(1, "stock_name", stock_name)
                # 계정과목 이름이 중복되는 행 삭제
                fstate = fstate.drop_duplicates(["sj_div", "account_id", "account_nm"], keep=False, ignore_index=True)
            except AttributeError:
                quarter += 1
                continue
            # 병합할 이전 분기 재무제표 dataframe이 없는경우 예외처리
            try:
                # 분기별 재무제표 병합
                if quarter == 1:
                    fstate_corp = fstate
                else:
                    fstate_corp = fstate_corp.merge(fstate, how="outer", on=["stock_name", "stock_code", "corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
            except (ValueError, UnboundLocalError):
                fstate_corp = fstate
            # NULL 데이터를 0으로 바꿈
            fstate_corp = fstate_corp.fillna(0)

            if quarter == 4:
                # 4분기 발생 금액 columns 추가
                i = 0
                for s in fstate_corp["sj_div"]:
                    if s == "BS":
                        fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] = fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}']
                    else:
                        fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] = fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter}'] - fstate_corp.loc[i,  f'thstrm_amount_{bsns_year}_{quarter-1}']
                    i += 1
            quarter += 1
        # 병합할 이전 연도 재무제표 dataframe이 없는경우 예외처리
        try:    
            # 연도별 재무제표 병합
            if bsns_year == years[0]:
                fstate_all_account = fstate_corp
            else:
                fstate_all_account = fstate_all_account.merge(fstate_corp, how="outer", on=["stock_name", "stock_code", "corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
        except (ValueError, UnboundLocalError):
            fstate_all_account = fstate_corp
    # NULL 데이터를 0으로 바꿈 (나중에 row 데이터에 대해 벡터 합을 계산할 때를 위한 작업)
    fstate_all_account = fstate_all_account.fillna(0)
    # 엑셀파일로 저장
    fstate_all_account.to_excel(f"{stock_code}.xlsx")
    return fstate_all_account


# In[58]:


# stock_info 테이블에 기업개황을 추가하는 함수 
def append_stock_info(stock_infos, stock_name):
    if stock_name in stock_infos["stock_name"]:
        pass
    else:
        if dart.company(stock_name)["corp_cls"] == "Y":
            stock_code = dart.company(stock_name)["stock_code"] + ".KS"
            corp_code = str(dart.find_corp_code(stock_name)) + ".KS"
        elif dart.company(stock_name)["corp_cls"] == "K":
            stock_code = dart.company(stock_name)["stock_code"] + ".KQ"
            corp_code = str(dart.find_corp_code(stock_name)) + ".KQ"
        stock_name = dart.company(stock_name)["stock_name"]
        #stock_infos에 info 데이터 추가(append)
        info = [(stock_code, stock_name, corp_code)]
        info_df = pd.DataFrame(info, columns=["stock_code", "stock_name", "corp_code"])
        stock_infos = stock_infos.append(info_df, ignore_index=True)


# In[59]:


def find_stock_code(stock_infos, stock_name):
    i = 0
    for s in stock_infos.stock_name:
        if s == stock_name:
            stock_code = stock_infos.loc[i, "stock_code"]
            break
        i += 1
    if i == len(stock_infos):
        stock_code = None
        print("종목 코드를 찾을 수 없습니다.")
    return stock_code


# In[61]:


def read_xlsx(file_name):
    table = pd.read_excel(f"{file_name}.xlsx")
    table = table.drop(columns="Unnamed: 0")
    return table


# In[130]:


# 재무제표 테이블에서 원하는 계정과목의 금액을 추출해서 리스트로 반환해주는 함수
def find_amounts(finstate, account, accounts):
    columns = list(finstate.columns)
    df = pd.DataFrame(columns=columns)
    i = 0
    for s in finstate["account_id"]:
        # 찾고자 하는 계정과목id 이면 df에 추가 
        if s in accounts[account]:
            df = df.append(finstate.loc[i], ignore_index=True)
        i += 1
    if len(df) == 0:
        return [None] * len(finstate.columns)
    else:
        # df의 각 row값을 벡터 합 시키기
        for i in range(len(df)):
            if i == 0:
                df_tot = df.loc[i]
            else:
                df_tot += df.loc[i]
        return list(df_tot)


# In[113]:


# 재무제표 테이블에서 특정 계정과목의 금액 추출하여 다중회사의 특정 계정과목 테이블에 데이터를 추가하는 함수
def append_amounts(account_df, stock_infos, stock_name, account, accounts): 
    stock_code = find_stock_code(stock_infos, stock_name)
    fstate_all_account = read_xlsx(stock_code)
    # columns
    columns = list(account_df.columns)
    columns_infos = columns[:3]
    columns_quarters = columns[3:]
    infos = list(fstate_all_account.loc[0, columns_infos])
    # 계정과목 금액 찾기
    amounts = find_amounts(fstate_all_account, account, accounts)[6:]
    # infos list와 amounts list 합친 후 account_df에 추가하기 
    data = tuple(infos + amounts)
    data_df = pd.DataFrame([data], columns=columns)
    account_df = account_df.append(data_df, ignore_index=True)
    
    return account_df


# In[134]:


# account table에서 누락된 데이터의 (row, columns) 찾기 
def find_zero_null(df, columns_quarters):
    zero_row_columns = []
    null_row_columns = []
    for quarter in columns_quarters:
        i = 0
        for amount in df[quarter]:
            if amount == None:
                null_row_columns.append([i, quarter])
            elif abs(amount) == 0:
                zero_row_columns.append([i, quarter])
            i += 1
    return zero_row_columns, null_row_columns


# In[129]:


stock_names = ["삼성전자", "SK하이닉스", "현대자동차", "현대모비스", "엔씨소프트", "원익IPS", "휴젤"]


# In[128]:


years = ["2021", "2020", "2019", "2018", "2017"]
quarters = ["11013", "11012", "11014", "11011"]


# In[63]:


columns_infos = ["stock_code", "stock_name", "corp_code"]
columns_quarters = [
 'thstrm_amount_2021_1',
 'thstrm_amount_2021_2',
 'thstrm_amount_2020_1',
 'thstrm_amount_2020_2',
 'thstrm_amount_2020_3',
 'thstrm_amount_2020_4',
 'thstrm_amount_2019_1',
 'thstrm_amount_2019_2',
 'thstrm_amount_2019_3',
 'thstrm_amount_2019_4',
 'thstrm_amount_2018_1',
 'thstrm_amount_2018_2',
 'thstrm_amount_2018_3',
 'thstrm_amount_2018_4',
 'thstrm_amount_2017_1',
 'thstrm_amount_2017_2',
 'thstrm_amount_2017_3',
 'thstrm_amount_2017_4',
]


# In[64]:


accounts = {}
accounts["equity"] = ["ifrs_EquityAttributableToOwnersOfParent", "ifrs-full_EquityAttributableToOwnersOfParent"]
accounts["profit"] = ["ifrs_ProfitLossAttributableToOwnersOfParent", "ifrs-full_ProfitLossAttributableToOwnersOfParent"]


# In[91]:


profit_df = pd.DataFrame(columns=columns_infos+columns_quarters)
equity_df = pd.DataFrame(columns=columns_infos+columns_quarters)


# In[66]:


stock_infos = read_xlsx("stock_infos")


# In[105]:


# profit_df, equity_table 만들기
for stock_name in stock_names: 
    profit_df = append_amounts(profit_df, stock_infos, stock_name, "profit", accounts)
    equity_df = append_amounts(equity_df, stock_infos, stock_name, "equity", accounts)


# In[ ]:


corps = corp_codes(api_key)

# corps에서 stock_code가 존재하는 회사만 stock_codes table에 할당
stock_codes = pd.DataFrame()
i = 0
for s in corps["stock_code"]:
    if len(s) == 6:
        stock_codes = stock_codes.append(corps.loc[i], ignore_index=True)
    i += 1

# stock_codes에서 코스피, 코스닥 시장에 상장된 회사들만 stock_infos table에 할당
columns_infos = ["stock_code", "stock_name", "corp_code"]
stock_infos = pd.DataFrame(columns=columns_infos)
i = 0
for s in stock_codes["corp_name"]:
    market = dart.company(s)["corp_cls"]
    if market == "Y":
        stock_code = stock_codes.loc[i, "stock_code"] + ".KS"
        stock_name = stock_codes.loc[i, "corp_name"]
        corp_code = stock_codes.loc[i, "corp_code"] + ".KS"
        infos = pd.DataFrame([(stock_code, stock_name, corp_code)], columns=columns_infos)
        stock_infos = stock_infos.append(infos, ignore_index=True)
    elif market == "K":
        stock_code = stock_codes.loc[i, "stock_code"] + ".KQ"
        stock_name = stock_codes.loc[i, "corp_name"]
        corp_code = stock_codes.loc[i, "corp_code"] + ".KQ"
        infos = pd.DataFrame([(stock_code, stock_name, corp_code)], columns=columns_infos)
        stock_infos = stock_infos.append(infos, ignore_index=True)  
    i += 1

