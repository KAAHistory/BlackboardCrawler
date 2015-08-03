import requests
from lxml import html
from urllib.parse import urlsplit
import urllib
import re
import os
import json
import hashlib
import os.path
from enum import Enum



basefolder = "BlackBoard"
config_file = "config.json"
courses_files = {}

course_links_types = ("/webapps/blackboard/content/listContent.jsp")

class FileStatus(Enum):
        new = 1
        changed = 2
        downloaded = 3

        def describe(self):
                return self.name
        

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

class BlackBoard:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.files = {}
        self.courses = []
        self.login(username, password)
        
    def getRoot(self, url):
        request = self.session.get(url)
        return html.fromstring(request.text)
        
    def postRoot(self, url, payload):
        request = self.session.post(url, data=payload)
        return html.fromstring(request.text)
        
    def login(self, username, password):
        print("Logging in")
        root = self.getRoot("https://bb.au.dk/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_21_1")
        link = root.xpath('//*[@id="module:_304_1"]/div[2]/div/div/p[2]/a/@href')[0]
        request = self.session.get(link)
        payload = {'username': username, 'password': password}
        root = self.postRoot(request.url, payload)
        payload = {root[1][1][2].get('name'): root[1][1][2].get('value')}
        root = self.postRoot(root[1][1].get("action"), payload)
        payload = {root[1][1][0].get('name'): root[1][1][0].get('value'), root[1][1][1].get('name'): root[1][1][1].get('value')}
        root = self.postRoot(root[1][1].get("action"), payload)
        print("\t" + username + " validated")
        print("")
        
    def getCourses(self):
        print("Getting courses")
        root = self.getRoot("https://bb.au.dk/webapps/portal/execute/tabs/tabAction?action=refreshAjaxModule&modId=_22_1&tabId=_2_1&tab_tab_group_id=_2_1")
        course_titles = root.xpath("//div[1]/ul/li/a/text()")
        course_urls = root.xpath("//div[1]/ul/li/a/@href")
        course_ids = [re.search("&id=([^&]+)", url).group(1) for url in course_urls]
        for id, title in zip(course_ids, course_titles):
            print("\tFound: " + title)
            self.courses.append({'id':id, 'title':title})
            ensure_dir(basefolder + "\\" + title)
        print("")
            
    def getPageFolder(self, root):
        print("Getting page")
        #page_folder = self.files
        folders = root.xpath('//*[@id="breadcrumbs"]/*[@role="navigation"]/ol/li/a/text()')
        if len(root.xpath('//*[@id="breadcrumbs"]/*[@role="navigation"]/ol/li/text()')) > 0:
            folders.append(root.xpath('//*[@id="breadcrumbs"]/*[@role="navigation"]/ol/li/text()')[-1])
        folders = [x.strip() for x in folders]
        #for folder in folders:
        #    if folder not in page_folder:
        #        page_folder[folder] = {} 
        #    page_folder = page_folder[folder]
        print("\t" + ' -> '.join(folders))
        return '\\'.join(folders)

    def getFileinfo(self, url):
        request = self.session.head(url, allow_redirects=True)
        file = {}
        id = self.sha256(request.url)
        file['url'] = request.url
        file['last-modified'] = request.headers.get('last-modified')
        file['filename'] = urllib.parse.unquote(urlsplit(request.url).path.split("/")[-1])
        file['status'] = FileStatus.new
        return id, file
            
    def parsePage(self, url):
        #url = "https://bb.au.dk/webapps/blackboard/content/listContent.jsp?course_id=_33462_1&content_id=_194882_1&mode=reset"
        root = self.getRoot(url)
        
        folder = self.getPageFolder(root)
        
        menu = root.xpath('//*[@id="courseMenuPalette_contents"]//li/a')
        for link in menu:
            url = link.get("href")
            if url.startswith(course_links_types):
                if url not in self.course_links:
                    self.course_links[url] = False

        content = root.xpath('//*[@id="content_listContainer"]//li//a')
        for link in content:
            url = link.get("href")
            if url.startswith('/bbcswebdav/'):
                (id, info) = self.getFileinfo("https://bb.au.dk" + link.get("href"))
                info['folder'] = folder
                if id not in self.files:
                    self.files[id] = info
                elif self.files[id]['last-modified'] != info['last-modified']:
                    self.files[id] = info
                    self.files[id]['status'] = FileStatus.changed   
                print("\t\t[ " + self.files[id]['status'].describe() + " ] " + self.files[id]['filename'])
            elif url.startswith(course_links_types):
                if url not in self.course_links:
                    self.course_links[url] = False
        return content
        
    def sha256(self, string):
        return hashlib.sha256(string.encode('utf-8')).hexdigest()

    def parseCourse(self, id):
        self.course_links = {}
        self.course_links['/webapps/blackboard/execute/launcher?type=Course&url=&id=' + id] = False
        missing = True
        while missing:
            missing = False
            for url, visited in self.course_links.items():
                if not visited:
                    missing = True
                    self.course_links[url] = True
                    self.parsePage("https://bb.au.dk" + url)
                    break
        print("")

    def downloadFiles(self):
        print("Downloading files")
        for id, file in self.files.items():
            if file['status'] == FileStatus.new:
                self.downloadFile(file)
    
    def downloadFile(self,file):
       ensure_dir(basefolder + "\\" + file['folder'])
       print("")
       print(file['folder'] + "\\" + file['filename'])
       r = self.session.get(file['url'], stream=True)
       with open(basefolder + "\\" + file['folder'] + "\\" + file['filename'], 'wb') as f:
           for chunk in r.iter_content(chunk_size=1024):
               print('.',end='')
               if chunk: # filter out keep-alive new chunks
                   f.write(chunk)
                   f.flush()
        


def getUserinfo():
        try:
            with open(config_file, "r") as f:
                        config = json.load(f)
        except:
            config = {}
            config['username'] = input("Username: ")
            config['password'] = input("Password: ")
            with open(config_file, "w") as f:
                json.dump(config, f)
        return config


config = getUserinfo()
bb = BlackBoard(config['username'], config['password'])
bb.getCourses()
bb.parseCourse("_33462_1")
bb.downloadFiles()
