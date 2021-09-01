#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import requests
from io import BytesIO


# In[106]:


import OpenDartReader
api_key = "ef3149d745caee09f48df5004b905ec4ef3f5d7e"
dart = OpenDartReader(api_key)


# In[3]:


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


# In[4]:


# 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011"


# In[3]:


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


# In[4]:


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


# In[176]:


# 각 연도마다 분기별 재무제표를 dataframe에 할당
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
    # NULL 데이터를 0으로 바꿈
    fstate_all_account = fstate_all_account.fillna(0)
    # 엑셀파일로 저장
    fstate_all_account.to_excel(f"{stock_code}.xlsx")
    return fstate_all_account


# In[205]:


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
        return None
    else:
        # df의 각 row값을 합치기(병합개녕이 아니라 plus)
        for i in range(len(df)):
            if i == 0:
                df_tot = df.loc[i]
            else:
                df_tot += df.loc[i]
        return list(df_tot)


# In[221]:


# stock_info table에 회사정보 추가하는 함수 
def append_stock_info(stock_infos, stock_name):
    if stock_name in stock_info["stock_name"]:
        pass
    else:
        if dart.company(stock_name)["corp_cls"] == "Y":
            stock_code = dart.company(stock_name)["stock_code"] + ".KS"
        elif dart.company(stock_name)["corp_cls"] == "K":
            stock_code = dart.company(stock_name)["stock_code"] + ".KQ"
        stock_name = dart.company(stock_name)["stock_name"]
        corp_code = str(dart.find_corp_code(stock_name))
        
        info = [(stock_code, stock_name, corp_code)]
        info_df = pd.DataFrame(info, columns=["stock_code", "stock_name", "corp_code"])
        stock_infos = stock_infos.append(info_df, ignore_index=True)
    return stock_infos


# In[200]:


def find_stock_code(stock_infos, stock_name):
    i = 0
    for s in stock_infos.stock_name:
        if s == stock_name:
            stock_code = stock_infos.loc[i, "stock_code"]
            break
        i += 1
    if i == len(stock_infos):
        stock_code = "종목 코드를 찾을 수 없습니다."
    return stock_code


# In[202]:


# 단일회사 재무제표 table에서 특정 계정과목의 금액 추출하여 새로운 table 생성하는 함수
def append_amounts(account_df, stock_name, account): 
    stock_code = find_stock_code(stock_infos, stock_name)
    fstate_all_account = pd.read_excel(f"{stock_code}.xlsx")
    fstate_all_account = fstate_all_account.drop(columns="Unnamed: 0")
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


# In[196]:


years = ["2021", "2020", "2019", "2018", "2017"]
quarters = ["11013", "11012", "11014", "11011"]
stock_names = ["삼성전자", "SK하이닉스", "현대자동차", "현대모비스", "엔씨소프트", "원익IPS", "휴젤"]
accounts = {}
accounts["equity"] = ["ifrs_EquityAttributableToOwnersOfParent", "ifrs-full_EquityAttributableToOwnersOfParent"]
accounts["profit"] = ["ifrs_ProfitLossAttributableToOwnersOfParent", "ifrs-full_ProfitLossAttributableToOwnersOfParent"]
columns_infos = ["stock_name", "stock_code", "corp_code"]
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


# In[225]:


stock_infos = pd.DataFrame(columns=columns_infos)


# In[208]:


profit_df = pd.DataFrame(columns=columns_infos+columns_quarters)
equity_df = pd.DataFrame(columns=columns_infos+columns_quarters)


# In[226]:


for stock_name in stock_names:    
    stock_infos = append_stock_info(stock_infos, stock_name)


# In[209]:


for stock_name in stock_names: 
    try:
        profit_df = append_amounts(profit_df, stock_name, "profit")
        equity_df = append_amounts(equity_df, stock_name, "equity")
    except TypeError:
        continue


# In[55]:


# account table에서 결측 데이터 찾기 
zero_row_columns = []
for quarter in columns_quarters:
    i = 0
    for amount in fstate_core_account[quarter]:
        if abs(amount) == 0:
            zero_row_columns.append([i, quarter])
        i += 1

