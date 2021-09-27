import pandas as pd
import os
from . import finstate_table

class FinanceStatement:
    
    def finstate_all(self, dart, stock_name, stock_code, bsns_year, reprt_code, path):
        try:
            os.mkdir(f'{path}/{stock_code}')
            path = f'{path}/{stock_code}'
            finstate_table.finstate_all(dart, stock_name, stock_code, bsns_year, reprt_code, path)

        except FileExistsError:
            path = f'{path}/{stock_code}'
            finstate_table.finstate_all(dart, stock_name, stock_code, bsns_year, reprt_code, path)
        


    def make_accounts(self, account_nm, account_id, path):    # account_nm: single_list, account_id: double_list
        try:
            f = open(f'{path}/accounts.txt', 'x')
            i = 0
            for ac_nm in account_nm:
                ac_id = account_id[i]
                finstate_table.make_accounts(ac_nm, ac_id, path)
                i += 1
            
        except FileExistsError:   
            i = 0
            for ac_nm in account_nm:
                ac_id = account_id[i]
                finstate_table.make_accounts(ac_nm, ac_id, path)
            i += 1

