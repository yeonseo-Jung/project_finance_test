#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests as re
from bs4 import BeautifulSoup
import json
import numpy as np
import pandas as pd
from io import BytesIO
from tqdm import tqdm
import time
from datetime import date, timedelta


# In[19]:


# Quantiwise에서 다운받은 재무제표 엑셀 파일을 필요한 부분만 DataFrame에 할당
def get_finstate(finstate_name):    
    # 지정된 폴더의 절대경로로 엑셀파일 가져와서 데이터프레임에 할당하기
    fs = pd.read_excel(f"C:\\Users\\wjddu\\Desktop\\Quantiwise\\{finstate_name}.xlsx")
    # 기존의 bs의 컬럼을 keys, 설정하고자 하는 컬럼을 values로 하는 딕셔너리 생성
    fs_columns = fs.loc[8].values
    col_dict = {}
    i = 0
    while i < len(fs_columns):
        col_dict[fs.columns[i]] = fs_columns[i]
        i+= 1

    # bs에서  계정코드, 이름, 금액단위, 금액 데이터만을 추출해서 컬럼을 재지정한 새로운 dataframe생성
    fs_df = fs.loc[9:].reset_index(drop=True).rename(columns = col_dict)
    
    return fs_df


# In[20]:


# 저장된 엑셀파일을 읽어들여 dataframe에 할당하여 출력해주는 함수
def read_xlsx(file_name):
    table = pd.read_excel(f"{file_name}.xlsx")
    try:
        table = table.drop(columns="Unnamed: 0")
    except KeyError:
        pass 
    return table


# In[21]:


accounts = {
    # 자본
    "A120000.IC": "자본총계", 
    "A120010.IC": "지배주주지분(자기자본)",
    "A120620.IC": "비지배주주지분",
    
    # D/E 비율, 수익성 판단
    "M113800.IC": "이자발생부채",
    "M111500.IC": "재고자산",
    "M234000.IC": "재고자산증가율",
    "M121000.IC": "매출액", 
    "M121005.IC": "매출액(TTM)",
    "M231000.IC": "매출액증가율(YoY)",
    "M231100.IC": "매출액증가율(QoQ)",
    "M121200.IC": "매출총이익",
    "M121500.IC": "영업이익",
    
    # 현금흐름 -> 장래성 판단
    "A400000.IC": "영업활동으로인한현금흐름",
    "A402340.IC": "투자활동으로인한현금흐름",
    # 설비투자 순액
    "A402630.IC": "유형자산의감소",
    "A403200.IC": "유형자산의증가",
    "A404460.IC": "무형자산의감소",
    "A404580.IC": "무형자산의증가",
    "A402610.IC": "생물자산의감소",
    "A403180.IC": "생물자산증가",
    # 자산가치 감소액
    "A400140.IC": "유형자산감가상각비",
    "A400160.IC": "기타무형자산상각비",
    "A400550.IC": "유형자산손상차손",
    "A400570.IC": "무형자산손상차손",
    "A401240.IC": "유형자산손상차손환입",
    "A401250.IC": "무형자산손상차손환입",

    "A400330.IC": "투자부동산처분손실",
    "A400340.IC": "유형,리스자산처분손실",
    "A400350.IC": "무형자산처분손실",
    
}


# In[2]:


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


# In[3]:


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


# In[4]:


# comp.fnguide.com에서 연도별, 분기별 재무비율 크롤링 함수 
def get_finance_ratio(stock_code, kind):    # kind: annual or quarter
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

        try:
            Table.loc[index, columns_arr[1:]] = value_list
            index += 1
        except ValueError:
            pass
        
    return Table


# In[5]:


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


# In[6]:


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


# In[26]:


# 정확한 계정과목 코드로 데이터 찾기
def find_account_quanti(finstate, account_code):
    i = 0
    for code in finstate["Account Code"]:
        if code == account_code:
            search_ac = finstate.loc[i]
            break
        i += 1
        
    try:
        return search_ac
    except:
        pass


# In[7]:


# 재무제표에서 계정과목에 대한 금액 데이터 찾기 함수
def find_account(finstate, account_nm):
    i = 0
    for ac in finstate["Account"]:
        if ac == account_nm:
            return_data = finstate.loc[i]
            break
        
        # 일치하는 계정과목명이 없고 찾고자 하는 계정과목명이 포함된 계정과목이 존재하는 경우
        elif account_nm in ac:
            try:
                return_data.append(finstate.loc[i, "Account"])
            except NameError:
                return_data = []
                return_data.append(finstate.loc[i, "Account"])
        i += 1
    
    try:
        return return_data
    
    except NameError:
        pass


# In[8]:


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
        try:
            fstate_bs = get_finstate(code, finstate_kind)
        # 해당 회사의 bs를 찾지 못했을 때 예외처리
        except AttributeError:
            i += 1
            continue
            
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


# In[9]:


# 안정성 비율 구하는 함수
def get_stable_ratio(bs, cis, finance_ratio):
    # 수중유동성(현금성자산 / 월평균매출액): 초단기적 안정성 지표  
    try:
        cash = find_account(bs, "현금및현금성자산")[-1]
        sales_mean = find_account(cis, "매출액")[1:5].mean() / 3
        liquidity = cash / sales_mean
    # bs 계정과목에 "현금및현금성자산" 혹은 "매출액"이 존재하지 않는다면 금융업일 가능성이 크므로 liquidity = 0으로 가정하고 넘어가자
    except TypeError:
        liquidity = 0

    # 당좌비율(당좌자산 / 유동부채): 단기적 안정성 지표
    quick_ratio = find_account(finance_ratio, "당좌비율")

    # 자기자본비율(자본총계 / 자산총계): 중장기적 안정성 지표
    equity_ratio = find_account(finance_ratio, "자기자본비율")
    
    return liquidity, quick_ratio, equity_ratio


# In[11]:


# 재무적 안정성을 측정하는 함수, 안정성 기준을 통과한 회사들의 데이터만 return
def determ_stability(stock_infos_df):
    nonLiquidity = []
    nonQuick = []
    nonEquity = []
    
    # 시가총액 기준 내림차순 정렬
    stock_infos_df = stock_infos_df.sort_values(by=["시가총액"], ascending=False, ignore_index=True)
    # 최근 4사업연도 자본잠식률 구하기
    imp_df = get_impairment(stock_infos_df, "bs_y")
    
    stable_corps = pd.DataFrame(columns=list(stock_infos_df.columns))
    with tqdm(total = len(imp_df)) as pbar:
        index = 0
        j = 0
        while j < len(imp_df):
            code = imp_df.loc[j, "stock_code"]
            name = imp_df.loc[j, "stock_name"]

            bs = get_finstate(code, "bs_q")
            cis = get_finstate(code, "cis_q")
            fr = get_finance_ratio(code, "annual")
            ratios = get_stable_ratio(bs, cis, fr)

            pbar.update(1)

            cnt = 0

            # 자본잠식률 기준: -50 (%) 미만
            for i in range(2, 6):
                if imp_df.loc[j][i] < -50:
                    cnt += 1


            # 수중유동성 기준: 1.2 이상
            liquidity = ratios[0]
            if liquidity > 1.2:
                cnt += 1
            elif liquidity == 0:
                nonLiquidity.append((code, name))

            # 당좌비율 기준: 90(%) 이상
            try:
                for i in range(1, 5):
                    quick_ratio = ratios[1][i] 
                    if quick_ratio >= 90: 
                        cnt += 1
            except TypeError:
                nonQuick.append((code, name))


            # 자기자본비율 기준: 10 (%)
            try:
                for i in range(1, 5):
                    equity_ratio = ratios[2][i] 
                    if equity_ratio >= 10: 
                        cnt += 1
            except TypeError:
                nonEquity.append((code, name))

            # 모든 안정성 기준을 통과한 기업들의 정보를 할당
            if cnt == 13:
                stable_corps.loc[index] = stock_infos_df.loc[j]
                index += 1

            j += 1
            
    return stable_corps, nonLiquidity, nonQuick, nonEquity


# In[28]:


# 수익성 기준 충족하는지 판단하는 함수
def profitability_corp(stock_code, stock_name, stock_infos_df):
    bs_df = get_finstate(f"{stock_name}_bs")
    cis_df = get_finstate(f"{stock_name}_cis")
    cf_df = get_finstate(f"{stock_name}_cf")
    cm_df = get_finstate(f"{stock_name}_cm")
    
    cnt = 0

    # D/E 비율 (유이자부채 / 자기자본)
    liability = find_account_quanti(cm_df, "M113800.IC")
    equity = find_account_quanti(bs_df, "A120010.IC")
    DE_ratio = liability[3:] / equity[3:]    # 1 미만 
    # D/E 비율 기준: 1 미만 
    if DE_ratio[-1] < 1:
        cnt += 1

    # 수익성 판단: 부가가치
    gross_profit = find_account_quanti(cm_df, "M121200.IC")
    operating_profit = find_account_quanti(cm_df, "M121500.IC")
    val_add = operating_profit[3:] / gross_profit[3:]
    # 수익성 판단 기준: 부가가치 / 영업이익 비율 0.2 이상
    c = 0
    for val in val_add:
        if val >= 0.2:
            c += 1
    if c == len(val_add):
        cnt += 1

    # 재고자산, 매출액(연율화) 추이계산
    inventory = find_account_quanti(cm_df, "M111500.IC")[3:]
    sales_annual = find_account_quanti(cm_df, "M121005.IC")[3:]    
    # 분기별 재고자산, 매출액 증가율
    inventory_increase_rate = find_account_quanti(cm_df, "M234000.IC")[3:].mean()
    sales_increase_rate = find_account_quanti(cm_df, "M231100.IC")[3:].mean()
    # 재고자산회전월수
    Inventory_turnover_month = inventory / sales_annual * 12
    Inventory_turnover_month_mean = Inventory_turnover_month.mean()

    # 매출액 조건: 연평균 매출액 200억 이상 & 4사업연도 매출액 증가율 평균 1 이상
    c = 0
    for sales in sales_annual:
        if sales >= 20000000:
            c += 1
    if c == len(sales_annual) and sales_increase_rate >= 1:
        cnt += 1
    # 재고자산회전월수 조건 1.5 미만
    if Inventory_turnover_month_mean < 1.5:
        cnt += 1
        
    corp = pd.DataFrame(columns=["종목코드", "종목명"])
    if cnt == 4:
        corp.loc[0] = [stock_code[1:], stock_name]
        corp = corp.merge(stock_infos_df)
        
    return corp


# In[30]:


# test
stock_code = "A005930"
stock_name = "삼성전자"
bs_df = get_finstate("삼성전자_bs")
cis_df = get_finstate("삼성전자_cis")
cm_df = get_finstate("삼성전자_cm")
common_stock_infos = get_common_stock_info("kospi")
stock_infos = get_stock_info("kospi", "20211202")
# 보통주만 시세정보 할당 (우선주 제거하기)
# SQL inner join; preserve the order of the left keys
stocks = common_stock_infos.merge(stock_infos)


# In[35]:


corp_df = profitability_corp(stock_code, stock_name, stocks)

# 기업가치 계산을 위한 데이터 수집

# roe 계산 (과거데이터로 미래 roe값 예측하기)
roe_srs = find_account_quanti(cm_df, "M211565.IC")
roe = 0
i = 0
while i <= 12:
    if i <= 4:
        roe += roe_srs[-i-1] * 3
    elif i <= 8:
        roe += roe_srs[-i-1] * 2
    else:
        roe += roe_srs[-i-1]
    i += 1
roe = roe / (12 + 8 + 4)

stocks_com = find_account_quanti(cm_df, "M702200.IC")[-1]    # 보통주상장주식수
stocks_pref = find_account_quanti(cm_df, "M702300.IC")[-1]    # 우선주상장주식수
treasury_com = find_account_quanti(cm_df, "M511000.IC")[-1]    # 보통주기말자기주식수
treasury_pref = find_account_quanti(cm_df, "M512000.IC")[-1]    # 우선주기말자기주식수

stock_num = stocks_com + stocks_pref - treasury_com - treasury_pref

equity = find_account_quanti(bs_df, "A120010.IC")[-1]    # 지배주주지분(자기자본)

# 할인율(r), 회사채 BBB- 5년 수익률
url = "https://www.kisrating.co.kr/ratingsStatistics/statics_spread.do"
resp = re.get(url)
html = BytesIO(resp.content)
df_r = pd.read_html(html, encoding="utf-8")[0]
r = round(df_r.loc[10, "5년"] * 0.01, 4)

# 기업가치 및 적정주가, 매도가, 매수가 계산
w = 1
corp_val = equity + equity * (roe - r) * (w / 1 + r - w)    # w = 초과이익 지속계수
price_sell = (equity + equity * (roe - r) / r) / stock_num    #(w = 1)
price_prop = (equity + equity * (roe - r) * 0.9 / (1 + r - 0.9)) / stock_num    #(w = 0.9)
price_buy = (equity + equity * (roe - r) * 0.8 / (1 + r - 0.8)) / stock_num    #(w = 0.8)


# In[36]:


corp_df.loc[0, ["corp_val", "price_sell", "price_prop", "price_buy"]] = [corp_val, price_sell, price_prop, price_buy]


# In[37]:


corp_df

