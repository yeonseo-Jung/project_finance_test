#!/usr/bin/env python
# coding: utf-8

# In[216]:


import pandas as pd
import os


# In[217]:


import OpenDartReader
api_key = "ef3149d745caee09f48df5004b905ec4ef3f5d7e"
dart = OpenDartReader(api_key)


# In[218]:


# 재무제표를 종류별로 분류하여 각각 DataFrame으로 return 해주는 함수
def fstate_classify(finstate):
    try:
        # 금액 관련 columns의 자료형을 object에서 float으로 변경
        amounts = ["thstrm_amount", "thstrm_add_amount", "frmtrm_amount", "frmtrm_q_amount", "frmtrm_add_amount"]
        for s in amounts:
            finstate[s] = pd.to_numeric(finstate[s], errors="coerce", downcast="float")

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
        
        a = [fstate_bs, fstate_is, fstate_cis, fstate_cf, fstate_sce]
        finstates = {}
        i = 0
        for fs in a:
            if len(fs) == 0:
                pass
            else:
                finstates[a[i]] = fs
            i += 1
                
        return finstates
    
    except AttributeError:
        return None


# In[219]:


# 단일회사 분기별 전체 재무제표를 종류별로 할당해서 엑셀로 저장해주는 함수 
def finstate_all(stock_name, stock_code, bsns_year, reprt_code, path):
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
           


# In[220]:


# 저장된 엑셀파일을 읽어들여 dataframe에 할당하여 출력해주는 함수
def read_xlsx(file_name):
    table = pd.read_excel(f"{file_name}.xlsx")
    table = table.drop(columns="Unnamed: 0")
    return table


# In[221]:

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
        accounts[account_nm].append(account_id)