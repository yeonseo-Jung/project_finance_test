import pandas as pd
import os
from . import finstate_tables

class FinanceStatement:
    
    def finstate_all(self, api_key, stock_name, stock_code, bsns_year, reprt_code, path):
        try:
            os.mkdir(f'{path}/{stock_code}')
            finstate_tables.finstate_all(api_key, stock_name, stock_code, bsns_year, reprt_code, path)

        except FileExistsError:
            path_tables = f'{path}/{stock_code}'
            finstate_tables.finstate_all(api_key, stock_name, stock_code, bsns_year, reprt_code, path_tables)
        


    def make_accounts(self, account_nm, account_id, path): 
        try:
            f = open(f'{path}/accounts.txt', 'x')
            i = 0
            for ac_nm in account_nm:
                ac_id = account_id[i]
                finstate_tables.make_accounts(ac_nm, ac_id, path)
                i += 1
            
        except FileExistsError:   
            i = 0
            for ac_nm in account_nm:
                ac_id = account_id[i]
                finstate_tables.make_accounts(ac_nm, ac_id, path)
            i += 1

