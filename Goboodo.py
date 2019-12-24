import json
import random
import requests
from bs4 import BeautifulSoup
import os
import pickle
from storeImages import StoreImages
from makePDF import createBook
import sys

#suppress urllib3 warning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#load config
with open('settings.json') as ofile:
    settings = json.load(ofile)

class  Goboodo:
    def __init__(self,id,):
        self.id = id
        self.country = settings['country']
        self.resethead()
        self.pageLinkDict = {}
        self.pageList = []
        self.lastCheckedPage = ""
        self.obstinatePages = []
        self.path = os.path.join(os.getcwd(),id)
        self.dataPath = os.path.join(self.path,'data')
        self.found = False
        if os.path.isdir(self.dataPath):
            self.found = True
        else:
            os.mkdir(self.path)
            os.mkdir(self.dataPath)
        with open('proxies.txt','r') as ofile:
            self.plist = ofile.readlines()

    def getProxy(self):
        prox =  random.choice(self.plist)
        return prox.strip()

    def createPageDict(self,jsonResponse):
        for pageData in jsonResponse[0]['page']:
            self.pageList.append(pageData['pid'])
            self.pageLinkDict[pageData['pid']]={}
            self.pageLinkDict[pageData['pid']]['src'] = ""
            self.pageLinkDict[pageData['pid']]['order'] = pageData['order']

    def getInitialData(self):
        if self.found == False:
            initUrl = "https://books.google."+self.country+"/books?id="+self.id+"&printsec=frontcover"
            page_data = requests.get(initUrl, headers=self.head,verify=False)
            soup = BeautifulSoup(page_data.content, "html5lib")
            print(f'Downloading {soup.findAll("title")[0].contents[0]}')
            scripts = (soup.findAll('script'))
            stringResponse = ("["+scripts[6].text.split("_OC_Run")[1][1:-2]+"]")
            jsonResponse = json.loads(stringResponse)
            self.createPageDict(jsonResponse)
            print(f'The total pages available are {len(self.pageList)}')
            for elem in jsonResponse[3]['page']:
                page = elem['pid']
                self.pageList.remove(page)
                self.pageLinkDict[page]['src'] = elem['src']
        else:
            try:
                with open(os.path.join(self.dataPath,'obstinate_pages.pkl'),'rb') as ofile:
                    self.pageList = pickle.load(ofile)
                with open(os.path.join(self.dataPath,'pageLinkDict.pkl'),'rb') as ofile:
                    self.pageLinkDict = pickle.load(ofile)
            except:
                print('Please delete the corresponding folder and start again')
                exit(0)

    def insertIntoPageDict(self, subsequentJsonData):
        if(len(self.pageList)==0):
            return False
        for pageData in subsequentJsonData['page']:
            if('src' in pageData.keys() and pageData['src']!=""):
                lastPage = pageData['pid']
                self.pageLinkDict[lastPage]['src'] = pageData['src']
                try:
                    self.pageList.remove(lastPage)
                    print(f'Fetched link for {lastPage}.')
                except Exception as e:
                    pass
        return True

    def fetchPageLinks(self,proxy=None):
        self.resethead()
        if(proxy):
            link = self.getProxy()
            proxyDict = {
                "http": 'http://'+link,
                "https": 'https://'+link,
            }
            print(f'Using proxy {proxy} for the url of page {self.pageList[0]}',)
            try:
                self.b_url = "https://books.google."+self.country+"/books?id=" + str(self.id) + "&pg=" + str(self.pageList[0]) + "&jscmd=click3"
                page_data = requests.get(self.b_url, headers=self.head,proxies=proxyDict,verify=False)
            except Exception as e:
                print(e)
            return page_data.json()
        else:
            self.b_url = "https://books.google."+self.country+"/books?id="+str(self.id)+"&pg="+ str(self.pageList[0]) +"&jscmd=click3"
            page_data = requests.get(self.b_url, headers=self.head,verify=False)
            return page_data.json()

    def resethead(self):
        try:
            req = requests.get("https://google."+self.country,verify=False)
            self.head = {
                'Host': 'books.google.co.in',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.00',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'close',
                'Cookie': "NID=" + str(req.cookies['NID']),
                        }
        except Exception as e:
            print(e)

    def processBook(self):
        downloadService = StoreImages(self.path,settings['proxy_images'])
        downloadService.getImages(settings['max_retry_images'])
        service = createBook(self.id, self.path)
        service.makePdf()

    def start(self):
        self.getInitialData()
        try:
            lastFirstList = self.pageList[0]
        except:
            print('There appears to be no page links to be fetched, fetching the images for downloaded links')
            return self.processBook()
        maxPageLimit = 0
        maxPageLimitHIT = settings['max_retry_links']
        proxyFlag = 0
        while True:
            try:
                if (proxyFlag):
                    prox = self.getProxy()
                    interimData = self.fetchPageLinks(prox)
                else:
                    interimData = self.fetchPageLinks()
            except:
                pass
            self.insertIntoPageDict(interimData)
            try:
                if (maxPageLimit == self.pageList[0]):
                    maxPageLimitHIT -= 1
                if (maxPageLimitHIT == 1):
                    maxPageLimitHIT = settings['max_retry_links']
                    print(f'Could not fetch link for page {self.pageList[0]}')
                    self.obstinatePages.append(self.pageList[0])
                    self.pageList = self.pageList[1:]
                if (lastFirstList == self.pageList[0]):
                    maxPageLimit = lastFirstList
                    if(settings['proxy_links']):
                        proxyFlag = 1
                else:
                    proxyFlag = 0
                lastFirstList = self.pageList[0]
            except:
                break
        with open(os.path.join(self.dataPath, 'obstinate_pages.pkl'), 'wb+') as ofile:
            pickle.dump(self.obstinatePages, ofile)
        with open(os.path.join(self.dataPath, 'pageLinkDict.pkl'), 'wb+') as ofile:
            pickle.dump(self.pageLinkDict, ofile)
        self.processBook()

if __name__ == "__main__":
    id = "nOJ0DwAAQBAJ"

    print('''
 ____            ____                    ____              
/\  _`\         /\  _`\                 /\  _`\            
\ \ \L\_\    ___\ \ \L\ \    ___     ___\ \ \/\ \    ___   
 \ \ \L_L   / __`\ \  _ <'  / __`\  / __`\ \ \ \ \  / __`\ 
  \ \ \/, \/\ \L\ \ \ \L\ \/\ \L\ \/\ \L\ \ \ \_\ \/\ \L\ \
   \ \____/\ \____/\ \____/\ \____/\ \____/\ \____/\ \____/

-----------------------------------------------------------------                                
    ''')
    book = Goboodo(id)
    book.start()
