#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import OpenDartReader


# In[2]:


api_key = "ef3149d745caee09f48df5004b905ec4ef3f5d7e"
dart = OpenDartReader(api_key)


# In[56]:


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


# In[13]:


# 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011"


# In[5]:


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


# In[91]:


# 각 연도마다 분기별 재무제표를 dataframe에 할당
def finstate_all_account(corp_name, years, quarters):
    for bsns_year in years:
        quarter = 1
        for reprt_code in quarters:
            # fstate 변수에 할당된 데이터가 없을 때(즉, 해당 연도 분기의 재무제표가 dart에 공시되어 있지 않은 경우) 예외처리
            try:
                fstate = dart.finstate_all(corp_name, bsns_year, reprt_code, fs_div="CFS")
                fstate = finstate_quarter(fstate).rename(columns={"thstrm_amount": f'thstrm_amount_{bsns_year}_{quarter}'})
                # stock_name, stock_code columns 삽입
                stock_code = dart.company(corp_name)["stock_code"]
                fstate.insert(0, "stock_name", corp_name)
                fstate.insert(1, "stock_code", stock_code)
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
    return fstate_all_account


# In[87]:


def find_account(finstate, account):
    columns = list(finstate.columns)
    df = pd.DataFrame(columns=columns)
    i = 0
    for s in finstate["account_id"]:
        # 찾고자 하는 계정과목id 이면 df에 추가 
        if s in account_id_dict[account]:
            df = df.append(finstate.loc[i], ignore_index=True)
        i += 1
    # df의 각 row값을 합치기(병합개녕이 아니라 plus)
    for i in range(len(df)):
        if i == 0:
            df_tot = df.loc[i]
        else:
            df_tot += df.loc[i]
    return df_tot


# In[119]:


years = ["2021", "2020", "2019", "2018", "2017"]
quarters = ["11013", "11012", "11014", "11011"]
corp_names = ["삼성전자", "SK하이닉스", "NAVER", "현대자동차", "현대모비스", "카카오게임즈", "원익IPS", "휴젤"]
account_id_dict = {}
account_id_dict["equity"] = ["ifrs_EquityAttributableToOwnersOfParent", "ifrs-full_EquityAttributableToOwnersOfParent"]
account_id_dict["profit"] = ["ifrs_ProfitLossAttributableToOwnersOfParent", "ifrs-full_ProfitLossAttributableToOwnersOfParent"]


# In[ ]:


for corp_name in corp_names:    
    fstate_all_account = finstate_all_account(corp_name, years, quarters)
    # 재무제표 액셀파일로 저장
    fstate_all_account.to_excel(f"{corp_name}.xlsx")


# In[132]:


fstate_core_account = pd.DataFrame(columns=columns)
c = 0
for corp_name in corp_names:    
    fstate_all_account = finstate_all_account(corp_name, years, quarters)
    # columns 
    columns = list(fstate_all_account.columns)
    columns_infos = columns[0:6]
    columns_quarters = columns[6:]
    # profit 계정과목 찾기
    account = "profit"
    account_tot = find_account(fstate_all_account, account)
    fstate_core_account.loc[2*c, columns_quarters] = account_tot[columns_quarters]
    # columns_infos의 데이터 할당
    infos = list(fstate_all_account.loc[0, columns_infos[0:4]])
    infos.append(account)
    infos.append(account_id_dict[account][0])
    fstate_core_account.loc[2*c, columns_infos] = infos
    # equity 계정과목 찾기
    account = "equity"
    account_tot = find_account(fstate_all_account, account)
    fstate_core_account.loc[2*c+1, columns_quarters] = account_tot[columns_quarters]
    # columns_infos의 데이터 할당
    infos = list(fstate_all_account.loc[0, columns_infos[0:4]])
    infos.append(account)
    infos.append(account_id_dict[account][0])
    fstate_core_account.loc[2*c+1, columns_infos] = infos
    c += 1