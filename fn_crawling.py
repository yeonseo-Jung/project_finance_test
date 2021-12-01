#!/usr/bin/env python
# coding: utf-8

# In[35]:


import requests as re
from bs4 import BeautifulSoup
import json
import numpy as np
import pandas as pd
from io import BytesIO
from tqdm import tqdm
import time
from datetime import date, timedelta


# In[39]:


# comp.fnguide.com에서 단일회사 연간 재무제표 주요계정 및 재무비율 크롤링 함수 
def get_finstate_highlight_annual(stock_code):

    ''' 경로 탐색'''
    url = re.get(f'http://comp.fnguide.com/SVO2/ASP/SVD_main.asp?pGB=1&gicode=A{stock_code}')
    url = url.content

    html = BeautifulSoup(url,'html.parser')
    body = html.find('body')

    fn_body = body.find('div',{'class':'fng_body asp_body'})
    ur_table = fn_body.find('div',{'id':'div15'})
    table = ur_table.find('div',{'id':'highlight_D_Y'})

    tbody = table.find('tbody')



    tr = tbody.find_all('tr')

    Table = pd.DataFrame()

    for i in tr:

        ''' 항목 가져오기'''
        category = i.find('span',{'class':'txt_acd'})

        if category == None:
            category = i.find('th')   

        category = category.text.strip()


        '''값 가져오기'''
        value_list =[]

        j = i.find_all('td',{'class':'r'})

        for value in j:
            temp = value.text.replace(',','').strip()

            try:
                temp = float(temp)
                value_list.append(temp)
            except:
                value_list.append(0)

        Table['%s'%(category)] = value_list

        ''' 기간 가져오기 '''    

        thead = table.find('thead')
        tr_2 = thead.find('tr',{'class':'td_gapcolor2'}).find_all('th')
        
        
        year_list = []

        for i in tr_2:
            try:
                temp_year = i.find('span',{'class':'txt_acd'}).text
            except:
                temp_year = i.text

            year_list.append(temp_year)
        
        Table.index = year_list

    Table = Table.T

    return Table


# In[40]:


# comp.fnguide.com에서 단일회사 연간 재무제표 주요계정 및 재무비율 크롤링 함수 
def get_finstate(stock_code, finstate_kind):
    
    finstate_dict = {
        "cis_y": "divSonikY",
        "cis_q": "divSonikQ",
        "bs_y": "divDaechaY",
        "bs_q": "divDaechaQ",
        "cfs_y": "divCashY",
        "cfs_q": "divCashQ",
    }
    kind = finstate_dict[finstate_kind]
    
    # 경로 탐색 
    url = re.get(f'https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A{stock_code}')
    url = url.content

    html = BeautifulSoup(url,'html.parser')
    body = html.find('body')

    fn_body = body.find('div',{'class':'fng_body asp_body'})
    table = fn_body.find('div',{'id':f'{kind}'})

    tbody = table.find('tbody')
    tr = tbody.find_all('tr')

    # 기간 가져오기 
    # 테이블 컬럼 리스트 할당
    thead = table.find("thead")
    terms = thead.find("tr").find_all("th")

    columns_arr = []
    for q in terms:
        columns_arr.append(q.text)    
    columns_arr[0] = "Account"
    
    Table = pd.DataFrame(columns=columns_arr)
    
    index = 0
    for i in tr:

        # 계정과목이름 
        account_nm = i.find('span',{'class':'txt_acd'})

        if account_nm == None:
            account_nm = i.find('th')   

        account_nm = account_nm.text.strip()
        Table.loc[index, "Account"] = account_nm

        # 금액 
        value_list =[]

        values = i.find_all('td',{'class':'r'})

        for value in values:
            temp = value.text.replace(',','').strip()

            try:
                temp = float(temp)
                value_list.append(temp)
            except:
                value_list.append(0)

        Table.loc[index, columns_arr[1:]] = value_list
        
        index += 1
        
    return Table


# In[41]:


# comp.fnguide.com에서 연도별, 분기별 재무비율 크롤링 함수 
def get_finstate_ratio(stock_code, kind):    # kind: annual or quarter
    if kind == "annual":
        k = 0
    elif kind == "quarter":
        k = 1
    else:
        print("두번째 변수에 annual 또는 quarter 둘 중 하나를 입력해주세요.")
    
    # 경로 탐색 
    url = re.get(f'https://comp.fnguide.com/SVO2/ASP/SVD_FinanceRatio.asp?pGB=1&gicode=A{stock_code}')
    url = url.content

    html = BeautifulSoup(url,'html.parser')
    body = html.find('body')

    fn_body = body.find('div',{'class':'fng_body asp_body'})
    table = fn_body.find_all('div',{'class':'um_table'})[k]

    tbody = table.find('tbody')
    tr = tbody.find_all('tr')

    # 기간 가져오기 
    thead = table.find("thead")
    terms = thead.find("tr").find_all("th")

    # 테이블 컬럼 리스트 할당
    columns_arr = []
    for q in terms:
        columns_arr.append(q.text)    
    columns_arr[0] = "Account"

    Table = pd.DataFrame(columns=columns_arr)

    index = 0
    for i in tr:

        # 계정과목이름 
        account_nm = i.find('span',{'class':'txt_acd'})

        if account_nm == None:
            account_nm = i.find('th')   

        account_nm = account_nm.text.strip()

        # 비율 종류 부분 없애기
        cle = ["안정성비율", "성장성비율", "수익성비율", "활동성비율", "성장성비율", "수익성비율"]
        if account_nm in cle:
            continue

        Table.loc[index, "Account"] = account_nm

        # 금액 
        value_list =[]

        values = i.find_all('td',{'class':'r'})

        for value in values:
            temp = value.text.replace(',','').strip()

            try:
                temp = float(temp)
                value_list.append(temp)
            except:
                value_list.append(0)

        Table.loc[index, columns_arr[1:]] = value_list

        index += 1
        
    return Table


# In[42]:


# 한국거래소(KRX) 웹사이트에서 전종목 정보 크롤링 함수 
def get_stock_info(market, date):    # market: kospi or kosdaq or konex    # date: ex) 20211001
    # Request URL
    url = 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd'
    # Form Data
    parms = {
        'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
        'share': '1',
        'money': '1',
        'csvxls_isNo': 'false',
    }

    if market == "kospi":
        parms['mktId'] = 'STK'
    elif market == "kosdaq":
        parms['mktId'] = 'KSQ'
    elif market == "konex":
        parms['mktId'] = "KNX"
        
    # 날짜 정보
    parms['trdDd'] = date
    
    # Request Headers ()
    headers = {
        'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020201',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    }

    r = re.get(url, parms, headers=headers)

    jo = json.loads(r.text)
    df = pd.DataFrame(jo['OutBlock_1'])
    
    # 크롤링 한 데이터 테이블에서 필요한 정보만 추출하고 컬럼 명 변경해서 데이터프레임에 할당
    columns = ["종목코드", "종목명", "시장구분", "종가", "시가", "고가", "저가", "거래량", "거래대금", "시가총액", "상장주식수"]
    data = df[["ISU_SRT_CD", "ISU_ABBRV", "MKT_NM", "TDD_CLSPRC", "TDD_OPNPRC", "TDD_HGPRC", "TDD_LWPRC", "ACC_TRDVOL", "ACC_TRDVAL", "MKTCAP", "LIST_SHRS"]]
    stock_info_df = pd.DataFrame(columns=columns)
    stock_info_df[columns] = data
    
    # 금액 및 주식 수 데이터를 계산 가능하도록 콤마(,)제거하고 실수형 데이터로 변경하기
    i = 0
    while i < len(stock_info_df):
        col = stock_info_df.columns
        j = 3
        srs = stock_info_df.loc[i, ["종가", "시가", "고가", "저가", "거래량", "거래대금", "시가총액", "상장주식수"]]
        for data in srs:
            stock_info_df.loc[i, col[j]] = float(data.replace(",", ""))
            j += 1
        i += 1

    return stock_info_df


# In[48]:


# 한국거래소(KRX) 웹사이트에서 보통주 정보 크롤링 함수 
def get_common_stock_info(market):    # market: kospi or kosdaq or konex  
    # Request URL
    url = 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd'
    # Form Data
    parms = {
        'bld': 'dbms/MDC/STAT/standard/MDCSTAT01901',
        'share': '1',
        'csvxls_isNo': 'false',
    }

    if market == "kospi":
        parms['mktId'] = 'STK'
    elif market == "kosdaq":
        parms['mktId'] = 'KSQ'
    elif market == "konex":
        parms['mktId'] = "KNX"
        
    
    # Request Headers ()
    headers = {
        'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020201',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    }

    r = re.get(url, parms, headers=headers)

    jo = json.loads(r.text)
    df = pd.DataFrame(jo['OutBlock_1'])
    
    # 종목 정보 테이블에서 보통주만 추출하기 
    df_common = pd.DataFrame()
    i = 0
    j = 0
    while i < len(df):
        if df.loc[i, "KIND_STKCERT_TP_NM"] == "보통주":
            df_common.loc[j, ["종목코드", "종목명"]] = list(df.loc[i, ["ISU_SRT_CD", "ISU_ABBRV"]])
            j += 1
        i += 1
    
    return df_common


# In[32]:


# 재무제표에서 계정과목에 대한 금액 데이터 찾기 함수
def find_account(finstate, account_nm):
    i = 0
    for ac in finstate["Account"]:
        if ac == account_nm:
            return_arr = finstate.loc[i]
            break
        
        # 일치하는 계정과목명이 없고 찾고자 하는 계정과목명이 포함된 계정과목이 존재하는 경우
        elif account_nm in ac:
            try:
                return_arr.append(finstate.loc[i, "Account"])
            except NameError:
                return_arr = []
                return_arr.append(finstate.loc[i, "Account"])
        i += 1
    
    try:
        return return_arr
    
    except NameError:
        print("NotFound")


# In[5]:


def find_stock(df, stock_code):
    i = 0
    for code in df["stock_code"]:
        if stock_code == code:
            return_srs = df.loc[i]
        i += 1
        
    try:
        return return_srs
    except:
        print("NonFound")


# In[59]:


# 자본잠식률 구하는 함수
def get_impairment(stock_infos, finstate_kind):    # finstate_kind -> annual: bs_y or quarter: bs_q
    
    noneType_arr = []
    zeroCapital_arr = []
    imp_df = pd.DataFrame(columns=["stock_code", "stock_name", "impairment_ratio_0", "impairment_ratio_1", "impairment_ratio_2", "impairment_ratio_3"])
    i = 0
    index = 0
    while i < len(stock_infos):
        code = stock_infos.loc[i, "종목코드"]
        name = stock_infos.loc[i, "종목명"]
        fstate_bs = get_finstate(code, finstate_kind)
        imp_df.loc[index, ["stock_code", "stock_name"]] = [code, name]

        for j in range(-1, -5, -1): 
            try:
                try:
                    nonOwn = find_account(fstate_bs, "비지배주주지분")[j]
                except TypeError:
                    nonOwn = 0
                equity = find_account(fstate_bs, "자본")[j] - nonOwn
                capital = find_account(fstate_bs, "자본금")[j]
                impairment = (capital - equity) / capital
                # 해당 연도 컬럼에 자본잠식률 할당
                imp_df.loc[index, f"impairment_ratio_{-j-1}"] = impairment

            except TypeError:
                if not list(stock_infos.loc[i, ["종목코드", "종목명"]]) in noneType_arr:
                    noneType_arr.append(list(stock_infos.loc[i, ["종목코드", "종목명"]]))
                    break
            except ZeroDivisionError:
                if not list(stock_infos.loc[i, ["종목코드", "종목명"]]) in zeroCapital_arr:
                    zeroCapital_arr.append(list(stock_infos.loc[i, ["종목코드", "종목명"]]))
                    break

        index += 1
        i += 1

    return imp_df


# In[69]:


# 최근 4분기 or 4사업연도 동안 자본잠식률 = -100% 이하인 기업 추출
def get_corp_impairment(imp_df):
    imp_arr = []
    i = 0
    for imp in imp_df["impairment_ratio_0"]:
        if imp <= -100 and imp_df.loc[i, "impairment_ratio_1"] <= -100 and imp_df.loc[i, "impairment_ratio_2"] <= -100 and imp_df.loc[i, "impairment_ratio_3"] <= -100:
            imp_arr.append((imp_df.loc[i, "stock_code"], imp_df.loc[i, "stock_name"], imp_df.loc[i, "impairment_ratio_0"], imp_df.loc[i, "impairment_ratio_1"], imp_df.loc[i, "impairment_ratio_2"], imp_df.loc[i, "impairment_ratio_3"]))
        i += 1    

    return imp_arr

