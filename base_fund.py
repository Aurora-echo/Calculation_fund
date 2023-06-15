'''
成本(count) = 份额(share) × 成本价 (cost_price)
金额(amount) = 最新净值(latest_net_worth) ×份额(share)
今日收益(today_revenue)： （今日估值(today_valuation) - 昨日净值(yesterday_net_worth)）× 份额(share)
总收益(total_revenue)： （今日估值(oday_valuation) - 成本价(cost_price)）× 份额(share)
盈亏率(profit_and_loss_ratio)： （总收益(total_revenue)/成本(count)）× 100

目前共购买（您的成本）(full_cost) =  成本(count) + 成本(count) + 成本(count) + ... + 成本(count)
持有金额（截止昨天）(yesterday_holding_amount)= 金额(amount) + 金额(amount) + 金额(amount) + ... + 金额(amount)
持有收益（截止昨天）(yesterday_holding_income_)= 总收益(total_revenue) + 总收益(total_revenue) + 总收益(total_revenue) + ... + 总收益(total_revenue)
今日收益(full_today_revenue)  =  今日收益(today_earnings) + 今日收益(today_earnings) + 今日收益(today_earnings) + ... + 今日收益(today_earnings)
持有金额 （算上今天）(today_holding_amount)=  持有金额（截止昨天）(yesterday_holding_amount)+ 今日收益(full_today_earnings)
'''

import requests
import json
import re
import time
from prettytable import PrettyTable,FRAME,ALL,NONE,RANDOM,MSWORD_FRIENDLY,PLAIN_COLUMNS,HEADER
from datetime import datetime, date, timedelta
from lxml import etree
from bs4 import BeautifulSoup
import logging

fund_list = []
all_fund_rise_fall_list = []
low_fund_list = []
hight_fund_list = []
total_revenue = 0
full_today_revenue = 0
today_total_revenuc = 0
yesterday_holding_income = 0
full_cost = 0
full_today_holding_amount = 0
#持有金额（截止昨天）
yesterday_holding_amount = 0
yesterday = str(date.today() + timedelta(days=-1))
six_days_ago = str(date.today() + timedelta(days=-11))
#颜色
red = '\033[31m'
green = '\033[32m'
default = '\033[0m'
blue = '\033[34m'
statistics_table = PrettyTable([blue+'基金名称'+default,blue+'成本'+default,blue+'金额'+default,blue+'成本净值'+default,blue+'今日净值'+default,blue+'涨跌幅度'+default,blue+'今日收益'+default,blue+'总收益'+default,blue+'盈亏率'+default,blue+' 近期涨跌,'+six_days_ago+'到'+yesterday+default],align='l',width=100,reversesort=True)
statistics_table.align[blue+'成本'+default]='l'
statistics_table.sortby = blue+'成本'+default
#statistics_table.sortby = blue+'涨跌幅度'+default
statistics_table.set_style(PLAIN_COLUMNS)
logging.basicConfig(filename='fund.log',format='%(asctime)s %(levelname)s: %(message)s',level=20,filemode='a',datefmt='%Y-%m-%d %H:%M:%S')
#requests和elasticsearch模块请求日志禁用
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)

#截取小数点后两位方法
def save_two_number(num,n):
        logging.info("save_two_number:start to calculate '{}' and keep '{}' decimal places...".format(num,n))
        num_x , num_y = str(num).split('.')
        num = float(num_x+'.'+num_y[0:n])
        logging.info("save_two_number:the results of '{}'".format(num))
        return num

#获取纳斯达克、白银等基金信息
def get_lof_fund_info():
    logging.info("get_lof_fund_info:start to calculate lof fund")
    headers = {'content-type': 'application/json',
               'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0',
               'Connection': 'close'}
    url='http://fund.eastmoney.com/'+common_fund_code+'.html'
    logging.info("get_lof_fund_info:lof fund url is {}".format(url))
    trytimes = 3
    for i in range(trytimes):
        try:
            lof_fund_info_r = requests.get(url,headers=headers)
            lof_fund_info_r_html=str(lof_fund_info_r.content,'utf-8')
            lof_fund_info_r_html_soup = BeautifulSoup(lof_fund_info_r_html,'lxml')
            lof_fund_info_r_html_soup_value = lof_fund_info_r_html_soup.find_all('dd', {'class': 'dataNums'})[1].find('span').getText()
            lof_fund_info_r_html_soup_name = lof_fund_info_r_html_soup.find('a', {'href': url, 'target': "_self"}).getText()
            lof_fund_info_r_html_soup_data = lof_fund_info_r_html_soup.find('dl', {'class': "dataItem02"}).find('p').getText()
            logging.info("get_lof_fund_info:calculate lof fund info name:{},value:{},data:{}".format(lof_fund_info_r_html_soup_name,lof_fund_info_r_html_soup_value,lof_fund_info_r_html_soup_data))
            return {'name':lof_fund_info_r_html_soup_name,'value':lof_fund_info_r_html_soup_value,'data':lof_fund_info_r_html_soup_data}
        except requests.exceptions.RequestException as e:
            logging.info("get_lof_fund_info:get lof fund info is fail ,Retry...")
            print("获取" + common_fund_code + "信息超时！正在重试第" + str(i + 1) + "次")
    logging.debug("get_lof_fund_info:get lof info is fail , exit now ...")
    print("获取" + common_fund_code + "信息失败！请稍后重试!")
    exit(0)

#获取普通基金信息
def get_common_fund_info():
    logging.debug("get_common_fund_info:start to calculate common fund ")
    url = "http://fundgz.1234567.com.cn/js/%s.js" % common_fund_code
    headers = {'content-type': 'application/json',
               'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0',
               'Connection':'close'}
    # requests 请求重试三次，三次之后还失败，直接返回获取XX超时，程序退出,同时设定每个请求时间为3秒
    trytimes = 3
    for i in range(trytimes):
        try:
            common_fund_info_r = requests.session()
            common_fund_info_r.keep_alive=False
            common_fund_info_r = requests.get(url, headers=headers,timeout=3)
            # 返回指定解码方式
            common_fund_info_r.content.decode("utf-8")
            common_fund_info_content = common_fund_info_r.text
            pattern = r'^jsonpgz\((.*)\)'
            common_fund_info_content = re.findall(pattern, common_fund_info_content)
            return (common_fund_info_content)
        except requests.exceptions.RequestException as e:
            print (repr(e))
            print ("获取" + common_fund_code + "信息超时！正在重试第" + str(i+1) + "次")
    print ("获取" + common_fund_code + "信息失败！请稍后重试!")
    exit(0)

#计算计算信息，返回基金信息数组
def count_all_fund():
    common_fund_info_content = get_common_fund_info()
    if common_fund_info_content[0]=='' :
        common_fund_info_content = get_lof_fund_info()
        count_lof_fund(common_fund_info_content)
        return
    for i in common_fund_info_content:
        fund_info = json.loads(i)
        # 成本
        count = round(float(cost_price) * float(share))
        #金额
        amount = round(float(fund_info['dwjz'])*float(share),2)
        # 判断今日涨跌幅度颜色
        if fund_info['gszzl'] > str(0):
            fund_info_gszzl_colour = red + '+' + fund_info['gszzl'] + '%' + default
        else:
            fund_info_gszzl_colour = green + fund_info['gszzl'] + '%' + default
        # 今日收益
        today_revenue = round((float(fund_info['gsz']) - float(fund_info['dwjz'])) * float(share), 2)
        # 判断今日收益情况颜色
        if today_revenue > 0:
            today_revenue_colour = red + str(today_revenue) + default
        else:
            today_revenue_colour = green + str(today_revenue) + default
        # 总收益
        total_revenue = round((float(fund_info['gsz']) - float(cost_price)) * float(share), 2)
        # 判断总收益情况（算上今天）颜色
        if total_revenue > 0:
            total_revenue_colour = red + "+" + str(total_revenue) + default
        else:
            total_revenue_colour = green + str(total_revenue) + default
        # 基金盈亏率
        profit_and_loss_ratio = round(total_revenue / (float(count)) * 100, 2)
        # 判断基金盈亏率颜色
        if profit_and_loss_ratio > 0:
            profit_and_loss_ratio_colour = red + str(profit_and_loss_ratio) + '%' + default
        else:
            profit_and_loss_ratio_colour = green + str(profit_and_loss_ratio) + '%' + default
        # 目前共购买(您的成本)
        global full_cost
        full_cost = round(full_cost + count)
        # 持有金额（截至昨天）
        global yesterday_holding_amount
        yesterday_holding_amount = round(float(yesterday_holding_amount) + amount, 2)
        # 持有收益（截止昨天）
        global yesterday_holding_income
        yesterday_holding_income = round(yesterday_holding_income + (float(fund_info['dwjz']) - float(cost_price)) * float(share),2)
        #　今日收益
        global full_today_revenue
        full_today_revenue = round(full_today_revenue + today_revenue,2)
        # 持有金额（算上今天）
        global  full_today_holding_amount
        full_today_holding_amount = round(yesterday_holding_amount + full_today_revenue,2)
        if float(fund_info['gszzl']) <= -3 :
            low_fund_list.append(fund_info['name'] + "  跌幅为：" + green + fund_info['gszzl'] + "%" + default)
        if float(fund_info['gszzl']) >= 3 :
            hight_fund_list.append(fund_info['name'] + "  涨幅为：" + red + '+' + fund_info['gszzl'] + "%" + default)
        rise_fall = get_change_recent_days(common_fund_code)
        statistics_table.add_row([fund_info['name'],count,amount,cost_price,fund_info['gsz'],fund_info_gszzl_colour,today_revenue_colour,total_revenue_colour,profit_and_loss_ratio_colour,rise_fall])

def count_lof_fund(dict):
    # 成本
    count = round(float(cost_price) * float(share),2)
    # 金额
    amount = round(float(dict['value']) * float(share),2)
    # 总收益
    total_revenue = round((float(dict['value']) - cost_price)*float(share),2)
    if total_revenue > 0:
        total_revenue_colour = red + "+" + str(total_revenue) + default
    else:
        total_revenue_colour = green + str(total_revenue) + default
    #盈亏率
    profit_and_loss_ratio = round(total_revenue / float(count) * 100,2)
    #基金盈亏率颜色
    if profit_and_loss_ratio > 0 :
        profit_and_loss_ratio_colour = red + str(profit_and_loss_ratio) + '%' + default
    else:
        profit_and_loss_ratio_colour = green + str(profit_and_loss_ratio) + '%' + default
    # 涨跌幅度
    rise_fall = get_change_recent_days(common_fund_code)

    #目前共购买(您的成本)
    global full_cost
    full_cost = round(full_cost + count)
    #持有金额（截止昨天)：
    global yesterday_holding_amount
    yesterday_holding_amount = round(float(yesterday_holding_amount) + (float(share) * float(dict['value'])), 2)
    # 持有收益（截止昨天）
    global yesterday_holding_income
    yesterday_holding_income = round(float(yesterday_holding_income) + float(total_revenue),2)
    # 持有金额（算上今天）
    global full_today_holding_amount
    full_today_holding_amount = round(full_today_holding_amount + amount, 2)
    statistics_table.add_row([dict['name'], count, amount,cost_price,"--", "--", "--", total_revenue_colour,profit_and_loss_ratio_colour, rise_fall])

#保存基金信息数组
def save_day_info(str):
    fund_list.append(str)

#获取基金最近五天的涨跌率
def get_change_recent_days(code):
    rise_fall_str = ''
    url = "http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code=%s&page=1&sdate=%s&edate=%s&per=20"%(code,six_days_ago,yesterday)
    headers = {'content-type': 'application/json',
               'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0',
               'Connection':'close'}
    r = requests.get(url,headers=headers)
    content = r.text
    #通过正则，只拿取content的内容
    test_html=re.findall('content:"(.*?)",records:',content)[0]
    #把字符串变成_Element的对象，可利用xpath函数
    html = etree.HTML(test_html)
    #利用xpath，获取tr标签下的td标签的文本内容
    html_data = html.xpath('//tr/td/text()')
    rise_fall_list = []
    #判断数组元素最后一位是不是%，是的话就取出来
    for number in html_data:
        if number[-1] == '%':
            rise_fall_list.append(number)
    rise_fall_list.reverse()
    for index in range(0,len(rise_fall_list)):
        if rise_fall_list[index] > '0' :
            rise_fall_list[index] = red+rise_fall_list[index]+default
        else:
            rise_fall_list[index] = green+rise_fall_list[index]+default
    for rise_fall in rise_fall_list:
         rise_fall_str = rise_fall_str + rise_fall + ' , '
    rise_fall_str = rise_fall_str[:-3]
    return rise_fall_str

if __name__ == '__main__':
    #更改数组 my_fund = [["基金代码",成本,份额]，[],[],[],[]...]，例如： [["001632",3.6019,119.04],["161725",1.2207,2048.01]]["001344", 1.5383, 4927.45],
    my_fund = [["001344", 1.4919, 5750.96],["001668", 2.9180, 1096.64],["004813", 3.0516, 527.08],["540008", 3.7152, 129.53],["006257", 1.9878, 254.68],["001156", 2.0486, 978.34],
               ["164906", 1.0690, 958.86],["005733", 0.9910, 756.79],["161725", 1.2377, 2657.29],["160225", 1.6008, 624.70],["519674", 6.0657, 294.28],["009484", 1.0543, 12180.87],
               ["002519",1.0716,10944.78],["161130",2.0492,622.18]]
    logging.info("开始计算基金，本次计算的数组是："+str(my_fund))
    print ("共有" + str(len(my_fund)) + "支基金，统计日期：" + time.strftime('%Y-%m-%d %H:%M',time.localtime(time.time())))
    for i in my_fund:
        common_fund_code = i[0]
        cost_price = i[1]
        share = i[2]
        a = count_all_fund()
        save_day_info(a)
    print (statistics_table)
    #判断"预估今日收益"颜色
    if full_today_revenue > 0:
        full_today_revenue_colour = red + '+' + str(full_today_revenue) + '    恭喜发财！' + default
    else:
        full_today_revenue_colour = green + str(full_today_revenue) + '    请你笑起来！'+ default
    print ("-"*200)
    print("基金统计")
    print("目前共购买(您的成本) " + str(full_cost) + ' 元')
    print("持有金额（截止昨天)：" + str(yesterday_holding_amount) + ' 元')
    print("持有收益（截止昨天)：" + str(yesterday_holding_income) + ' 元')
    print ("今日收益：" + str(full_today_revenue_colour))
    print ("持有金额（算上今天)： " + str(full_today_holding_amount) + ' 元')

    if low_fund_list:
        print ("今日估值跌幅3%以上的基金有：")
        for low_fund in low_fund_list:
            print ('  '+low_fund)
    if hight_fund_list:
        print ("今日涨幅3%以上的基金有：")
        for hight_fund in hight_fund_list:
            print ('  '+hight_fund)


