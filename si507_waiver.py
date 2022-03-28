#################################
##### Name: Ruge Xu
##### Uniqname: rugexu
#################################

import os
from bs4 import BeautifulSoup
import re
import requests
import json
import secrets  # file that contains your API key


findLink = re.compile(r'<a href="(.*?)">', re.S)
findName = re.compile(r'<a.*?class="Hero-title.*?>(.*)</a>')
findType = re.compile(r'<span class="Hero-designation">(.*?)</span>', re.S)
findLocality = re.compile(r'<span.*itemprop="addressLocality".*?>(.*?)</span>', re.S)
findRegion = re.compile(r'<span.*itemprop="addressRegion".*?>(.*?)</span>', re.S)
findCode = re.compile(r'<span.*itemprop="postalCode".*?>(.*?)</span>', re.S)
findPhone = re.compile(r'<span.*itemprop="telephone".*?>(.*?)</span>', re.S)


class Cache:
    def __init__(self, cacheDir='cache'):
        self.cacheDir = cacheDir

    def __getitem__(self, url):
        path = self.urlToPath(url)
        if os.path.exists(path):
            fp = open(path, 'r', encoding='utf-8')
            if self.isJson(url):
                data = json.load(fp)
            else:
                data = fp.read()
            fp.close()
            return data
        else:
            raise KeyError(url + ' does not exist')

    def __setitem__(self, url, data):
        path = self.urlToPath(url)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)

        fp = open(path, 'w', encoding='utf-8')
        fp.write(data)
        fp.close()

    def isJson(self, url):
        return url.find("www.nps.gov") == -1

    def urlToPath(self, url):
        if not self.isJson(url):
            path = url[url.find("www.nps.gov"):]
        else:
            path = url[url.find("origin="):]
            path += '/index.json'

        filename = path
        filename = re.sub(r'[^0-9A-Za-z-.,;_]', '_', filename)
        filename = '/'.join(segment[:255] for segment in filename.split('/'))
        return os.path.join(self.cacheDir, filename)


cache = Cache()


class NationalSite:
    '''a national site

    Instance Attributes
    -------------------
    category: string
        the category of a national site (e.g. 'National Park', '')
        some sites have blank category.

    name: string
        the name of a national site (e.g. 'Isle Royale')

    address: string
        the city and state of a national site (e.g. 'Houghton, MI')

    zipcode: string
        the zip-code of a national site (e.g. '49931', '82190-0168')

    phone: string
        the phone of a national site (e.g. '(616) 319-7906', '307-344-7381')
    '''

    def __init__(self, url):
        html = askURL(url)
        bs = BeautifulSoup(html, "html.parser")
        item = str(bs)
        self.name = re.findall(findName, item)[0]
        find = re.findall(findType, item)
        self.category = "no category" if find[0] == "" else find[0]
        find = re.findall(findLocality, item)
        addressLocality = "no locality" if len(find) == 0 else find[0]
        find = re.findall(findRegion, item)
        addressRegion = "no region" if len(find) == 0 else find[0]
        self.address = addressLocality + ", " + addressRegion
        find = re.findall(findCode, item)
        self.zipcode = "no zipcode" if len(find) == 0 else find[0].strip()
        find = re.findall(findPhone, item)
        self.phone = "no phone" if len(find) == 0 else find[0].strip()

    def info(self):
        return "%s (%s): %s %s" % (self.name, self.category, self.address, self.zipcode)


class NearbyPlace:
    def __init__(self, search):
        self.name = search["name"]
        fields = search["fields"]
        self.category = "no category" if fields["group_sic_code_name"] == "" else fields["group_sic_code_name"]
        self.address = "no address" if fields["address"] == "" else fields["address"]
        self.city = "no city" if fields["city"] == "" else fields["city"]

    def info(self):
        return "%s (%s): %s, %s" % (self.name, self.category, self.address, self.city)


def askURL(url):
    try:
        html = cache[url]
        print("Using cache")
        return html
    except KeyError:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/14.0.3 Safari/605.1.15 "
        }
        res = requests.get(url=url, headers=headers)
        res.encoding = "utf-8"
        print("Fetching")
        html = res.text
        cache[url] = html
        return html


def APIrequest(url):
    try:
        data = cache[url]
        print("Using cache")
        return data
    except KeyError:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/14.0.3 Safari/605.1.15 "
        }
        res = requests.get(url=url, headers=headers)
        res.encoding = "utf-8"
        print("Fetching")
        data = res.json()
        cache[url] = json.dumps(data)
        return data


def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "https://www.nps.gov"

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
        e.g. {'michigan':'https://www.nps.gov/state/mi/index.htm', ...}
    '''
    baseurl = "https://www.nps.gov/index.htm"
    linkList = dict()
    html = askURL(baseurl)
    bs = BeautifulSoup(html, "html.parser")
    t_list = bs.select("#HERO > div > div.SearchBar.StrataSearchBar > div > div > div > div.SearchBar-keywordSearch.input-group.input-group-lg > ul > li > a")
    for li in t_list:
        link = re.findall(findLink, str(li))[0]
        name = li.string.lower()
        linkList[name] = "https://www.nps.gov" + link
    return linkList


def get_site_instance(site_url):
    '''Make an instances from a national site URL.

    Parameters
    ----------
    site_url: string
        The URL for a national site page in nps.gov

    Returns
    -------
    instance
        a national site instance
    '''
    return NationalSite(site_url)


def get_sites_for_state(state_url):
    '''Make a list of national site instances from a state URL.

    Parameters
    ----------
    state_url: string
        The URL for a state page in nps.gov

    Returns
    -------
    list
        a list of national site instances
    '''
    html = askURL(state_url)
    bs = BeautifulSoup(html, "html.parser")
    t_list = bs.select("#list_parks > li > div > h3 > a")
    sites = []
    for li in t_list:
        link = re.findall(findLink, str(li))[0]
        site = get_site_instance("https://www.nps.gov" + link + "index.htm")
        sites.append(site)
    return sites


def get_nearby_places(site_object):
    '''Obtain API data from MapQuest API.

    Parameters
    ----------
    site_object: object
        an instance of a national site

    Returns
    -------
    dict
        a converted API return from MapQuest API
    '''
    url = "http://www.mapquestapi.com/search/v2/radius?key=%s&maxMatches=10&origin=%s&radius=10&units=m&ambiguities=ignore&outFormat=json" % (secrets.API_KEY, site_object.zipcode)
    data = APIrequest(url)
    return data


def print_sites_for_state(state, sites):
    title = "List of national sites in %s" % state
    seg = ""
    for i in range(len(title)):
        seg += "-"
    print(seg)
    print(title)
    print(seg)
    i = 1
    for site in sites:
        print("[%d] %s" % (i, site.info()))
        i += 1


def jsonAnalysis(data):
    searchResults = data["searchResults"]
    places = []
    for search in searchResults:
        place = NearbyPlace(search)
        places.append(place)
    return places


def print_nearby_places_for_site(site, places):
    title = "Places near %s" % site.name
    seg = ""
    for i in range(len(title)):
        seg += "-"
    print(seg)
    print(title)
    print(seg)
    for place in places:
        print("- %s" % place.info())


if __name__ == "__main__":
    linkList = build_state_url_dict()
    while 1:
        state = input("Enter a state name (e.g. Michigan, michigan) or \"exit\"\n: ")
        if state == "exit":
            exit()
        stateLowerCase = state.lower()
        if stateLowerCase in linkList:
            sites = get_sites_for_state(linkList[stateLowerCase])
            print_sites_for_state(state, sites)
            while 1:
                number = input("Choose the number for detail search or \"exit\" or \"back\"\n: ")
                if number == "exit":
                    exit()
                if number == "back":
                    break
                if not number.isdigit():
                    print("[Error] Invalid input")
                else:
                    number = int(number)
                    if number < 1 or number > len(sites):
                        print("[Error] Invalid input")
                    elif sites[number - 1].zipcode == "no zipcode":
                        print("[Error] No zipcode for this national site")
                    else:
                        data = get_nearby_places(sites[number - 1])
                        places = jsonAnalysis(data)
                        print_nearby_places_for_site(sites[number - 1], places)
        else:
            print("Error: enter proper state name")
