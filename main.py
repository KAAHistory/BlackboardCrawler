import requests
from lxml import html
from urllib.parse import urlsplit
import re
import os
import json
import hashlib

basefolder = "BlackBoard"
courses_files = {}

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
		page_folder = self.files
		folders = root.xpath('//*[@id="breadcrumbs"]/*[@role="navigation"]/ol/li/a/text()')
		folders.append(root.xpath('//*[@id="breadcrumbs"]/*[@role="navigation"]/ol/li/text()')[-1])
		folders = [x.strip() for x in folders]
		for folder in folders:
			if folder not in page_folder:
				page_folder[folder] = {} 
			page_folder = page_folder[folder]
		print("\t" + ' -> '.join(folders))
		return page_folder
			
	def parsePage(self, url):
		url = "https://bb.au.dk/webapps/blackboard/content/listContent.jsp?course_id=_33462_1&content_id=_234184_1"
		root = self.getRoot(url)
		
		folder = self.getPageFolder(root)
		
		#menu_url = root.xpath('//*[@id="courseMenuPalette_contents"]//li/a/@href')
		#menu_links = root.xpath('//*[@id="courseMenuPalette_contents"]//li/a/span/@title')
		#print("Found menu")
		#for link in menu_links:
		#	print(link)
	
		content = root.xpath('//*[@id="content_listContainer"]//li//a')
		for link in content:
			if link.get("href").startswith('/bbcswebdav/'):
				print(link.get("href"))
				info = self.getFileinfo("https://bb.au.dk" + link.get("href"))
				id = hashlib.sha256(info['url'].encode('utf-8')).hexdigest()
				folder[id] = info
		return content

	def getFileinfo(self, url):
		request = self.session.head(url, allow_redirects=True)
		last_modified = request.headers.get('last-modified')
		filename = urlsplit(request.url).path.split("/")[-1]
		return  {'last-modified': last_modified, 'filename': filename, 'url': request.url}
	



#def download_file(session, url, folder):
#	ensure_dir(folder)
#	r = session.get("https://bb.au.dk" + url, stream=True)
#	name = re.search("/([^/\?]+)(?:\?|$)",r.url).group(1)
#	local_filename = folder + "\\" + urllib.parse.unquote(name)
#	print(local_filename)
#	with open(local_filename, 'wb') as f:
#		for chunk in r.iter_content(chunk_size=1024): 
#			if chunk: # filter out keep-alive new chunks
#				f.write(chunk)
#				f.flush()
				

	

def parseCourse(session, id):
	return parsePage(session, "https://bb.au.dk/webapps/blackboard/execute/launcher?type=Course&url=&id=" + id)
	
				
with open("config.json", "r") as f:
	config = json.load(f)

bb = BlackBoard(config['username'], config['password'])
bb.getCourses()
bb.parsePage("e")