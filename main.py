#!/usr/bin/env python3

import re
import requests
from time import sleep
import smtplib
import itertools
import pickle

############################
# Items To Configure       #
############################
# Stores To Search
STORES = ['125', '85']  # [Parkville, Rockville]
# Item Links
ITEMS = [
    'https://www.microcenter.com/product/628346/evga-geforce-rtx-3080-ftw3-ultra-gaming-triple-fan-10gb-gddr6x-pcie-40-graphics-card'
]
# Your phone number @ your provider for texts
# or you can use normal email
recipient = ['<Phone>@<provider.net>']
# Personal Gmail Account you will send the text from
gmail_sender = 'gmail@gmail.com'
# Generated Gmail App Password
gmail_passwd = '<App Password>'


class DictDiffer(object):
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])


while True:
    for store, item in itertools.product(STORES, ITEMS):
        cookies = dict(storeSelected=store)
        msgText = ""
        stockCurrent = {}

        # Query Page
        respData = requests.get(item, cookies=cookies).text
        # Get SKU Num
        skuNum = re.findall(r'\"sku\": \"(\d+)\"', str(respData))
        # Is it in stock
        inStock = re.findall(r'\'inStock\':\'(True|False)\',', str(respData))
        # Price
        productPrice = re.findall(r'data-price=\"(\d{1,3}\.\d{2})\"', str(respData))
        # Store ID
        storeId = re.findall(r'\'storeNum\':\'(.*?)\',', str(respData))
        # Store Name
        storeName = re.findall(r'at (.*?) Store', str(respData))
        # Item Name
        productName = re.search('data-name=\"(.*?)\"', str(respData)).groups()[0]

        stockCurrent[skuNum[0]] = inStock[0]

        for stock in inStock:
            if stock == "True":
                print(f'{productName} -- In Stock at {storeName[0]}')
                msgText = f"{msgText} {productName} -- SKU: {skuNum[0]} -- {productPrice[0]}\n{item}\n\n"
            elif stock == "False":
                print(f"{productName} -- Out of stock at {storeName[0]}")
            else:
                print("Error retrieving stock")

        stockDiff = False

        try:
            stockLast = pickle.load(open(fr"items_in_stock_{store}", "rb"))
            stockDiff = DictDiffer(stockCurrent, stockLast).changed()
        except FileNotFoundError:
            pass
        finally:
            with open(fr"items_in_stock_{store}", "wb") as outfile:
                pickle.dump(stockCurrent, outfile)

        if stockDiff and inStock[0] == 'True':

            SUBJECT = f'{productName} at Microcenter'
            TEXT = f'{msgText}\n\nAt the {storeName[0]} Store'

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login(gmail_sender, gmail_passwd)

            BODY = '\r\n'.join(['To: %s' % recipient,
                                'From: %s' % gmail_sender,
                                'Subject: %s' % SUBJECT,
                                '', TEXT])
            try:
                server.sendmail(gmail_sender, recipient, BODY)
                print('Email sent')
            except Exception as e:
                print('Error sending mail')
            server.quit()
    sleep(100)
