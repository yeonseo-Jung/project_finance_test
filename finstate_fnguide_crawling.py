import requests as re
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd

# 단일회사 연간 재무제표 주요계정 및 재무비율 크롤링 함수 
def get_finstate_annual(stock_code):

    ''' 경로 탐색'''
    url = re.get('http://comp.fnguide.com/SVO2/ASP/SVD_main.asp?pGB=1&gicode=A%s'%(stock_code))
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


# 단일회사 연간 재무제표 주요계정 및 재무비율 크롤링 함수 
def get_finstate_quarter(stock_code):

    ''' 경로 탐색'''
    # 경로 탐색 
    url = re.get(f'https://comp.fnguide.com/SVO2/ASP/SVD_Finance.asp?pGB=1&gicode=A{stock_code}')
    url = url.content

    html = BeautifulSoup(url,'html.parser')
    body = html.find('body')

    fn_body = body.find('div',{'class':'fng_body asp_body'})
    table = fn_body.find('div',{'id':'divSonikQ'})

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

        # columns(최근 4개 분기) 

        thead = table.find("thead")
        quarters = thead.find("tr").find_all("th")

        quarter_arr = []
        for q in quarters[1:]:
            quarter_arr.append(q.text)

        Table.index = quarter_arr

    Table = Table.T

    return Table
