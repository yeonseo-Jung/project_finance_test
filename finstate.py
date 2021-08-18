import io
from io import BytesIO
import zipfile
import requests
import json
import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm


try:
    from pandas import json_normalize
except ImportError:
    from pandas.io.json import json_normalize
    
# IS 계정과목 
"""
영업수익(매출): "ifrs-full_Revenue" or "ifrs-full_GrossProfit"
영업이익: "dart_OperatingIncomeLoss"
법인세비용차감전순이익: "ifrs-full_ProfitLossBeforeTax"
계속영업순이익: "ifrs-full_ProfitLossFromContinuingOperations"
지배기업의 소유주에게 귀속되는 당기순이익: "ifrs-full_ProfitLossAttributableToOwnersOfParent" or ifrs_ProfitLossAttributableToOwnersOfParent
비지배지분에 귀속되는 당기순이익: "ifrs_ProfitLossAttributableToNoncontrollingInterests"
기본주당이익: "ifrs-full_BasicEarningsLossPerShare"
희석주당이익: "ifrs-full_DilutedEarningsLossPerShare"
"""

# BS 계정과목
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

"""
<분석 할 기업>
(kospi)
삼성전자
SK하이닉스
NAVER
카카오
현대자동차
현대모비스
LG생활건강
DB하이텍
(kosdaq)
카카오게임즈
sk머티리얼즈
씨젠
원익IPS
휴젤
"""
# 1분기보고서 : "11013", 반기보고서 : "11012", 3분기보고서 : "11014", 사업보고서 : "11011"

# 분기별 제무재표 데이터를 필요한 columns만 추출해서 table에 할당하여 return 
def finstate_quarter(finstate_df):
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

# 각 연도마다 분기별 재무제표 데이터를 dataframe에 할당
def finstate_all_account(api_key, corp_code, years, quarters):
    for bsns_year in years:
        quarter = 1
        for reprt_code in quarters:
            fstate = finstate_all(api_key, corp_code, bsns_year, reprt_code, fs_div="CFS")
            fstate = finstate_quarter(fstate).rename(columns={"thstrm_amount": f'thstrm_amount_{bsns_year}_{quarter}'})
            # 계정과목 이름이 중복되는 행 삭제
            fstate = fstate.drop_duplicates(["sj_div", "account_nm"], keep=False, ignore_index=True)
            # 분기별 재무제표 병합
            if quarter == 1:
                fstate_corp = fstate
            else:
                fstate_corp = fstate_corp.merge(fstate, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
            # NaN을 0으로 대체
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
        # 연도별 재무제표 병합
        if bsns_year == years[0]:
            fstate_all_account = fstate_corp
        else:
            fstate_all_account = fstate_all_account.merge(fstate_corp, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
    # NaN을 0으로 대체
    fstate_all_account = fstate_all_account.fillna(0)
    return fstate_all_account

# 기존 재무제표 dataframe에 추가적으로 분기별 재무제표 dataframe을 병합해주는 함수
def finstate_merge(api_key, finstate_df, bsns_year, quarters):
    corp_code = finstate_df.loc[0, "corp_code"]
    quarter_codes = {
        1: "11013", 
        2: "11012", 
        3: "11014",
        4: "11011",
    }
    i = 0
    for quarter in quarters:
        reprt_code = quarter_codes[quarter]
        fstate = finstate_all(api_key, corp_code, bsns_year, reprt_code, fs_div="CFS")
        fstate = finstate_quarter(fstate).rename(columns={"thstrm_amount": f'thstrm_amount_{bsns_year}_{quarter}'})    
        # 계정과목 이름이 중복되는 행 삭제
        fstate = fstate.drop_duplicates(["sj_div", "account_nm"], keep=False, ignore_index=True)
        # 기존 재무제표에 새로운 분기 재무제표 병합
        if i == 0:
            fstate_all_account = finstate_df.merge(fstate, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
        else:
            fstate_all_account = fstate_all_account.merge(fstate, how="outer", on=["corp_code", "sj_div", "account_id", "account_nm"], suffixes=("", ""))
        i += 1
    # NaN을 0으로 대체
    fstate_all_account = fstate_all_account.fillna(0) 
    return fstate_all_account

