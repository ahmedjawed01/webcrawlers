from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from web_crawlers.items import CraigslistSampleItem
import urlparse
import os
import re
import requests
from scrapy.http import Response, Request
from scrapy.http import Request
import mechanize,urllib2, urllib, json
import unicodedata
import requests
import requests_cache
import hashlib
from web_crawlers.utils import *
from datetime import date




class MySpider(CrawlSpider):
    name = "sverig"
    allowed_domains = ["sverigesemester.com"]
    url_pages=[]
    for i in range(1,77):
        url_pages.append("http://www.sverigesemester.com/stugor?p="+str(i))
    
    start_urls = ["http://www.sverigesemester.com/holidayrentals"]+url_pages

    rules = (Rule (SgmlLinkExtractor(restrict_xpaths=('//a[@class="details"]',))
    , callback="parse_items", follow= True),
    )

    def parse_items(self, response):
        hxs = HtmlXPathSelector(response)
        
        titles = hxs.select('//div[@id="overview"]')
       
        items = []
        for titles in titles:
            item = CraigslistSampleItem()
            item ["Images"] = titles.select('div[@id="main_pic"]/a/img/@src').extract()
            item ["Heading"] = titles.select('article[@class="description"]/h4/text()').extract()
            item ["Description"] = titles.select('article[@class="description"]/p[@class="mainDescription"]/text()').extract()
            Rent=titles.select('div[@class="info_rental details"]/div[@class="priceDetails"]/span[@class="price price_multiple"]/text()').extract()
            if Rent:
                Rent = re.findall("[0-9].+\-",str(Rent))[0].replace("-","").strip()
            if not Rent:
                 Rent=titles.select('div[@class="info_rental details"]/div[@class="priceDetails"]/span[@class="price price_single"]/text()').extract()
                 Rent=Rent[0].replace("SEK","").strip()


                
            item ["Rent"] = parse_price(Rent)
            GEO = titles.select('img[@class="map"]/@src').extract()
            

            
            GEO = re.findall("\|.+?\&",GEO[0])[0].replace("|","").replace("&","").split(",")
            
            
            #GEO = reverse_geocode(GEO)
            #item ["Street_name"] = GEO.get("street_name","")
            #item ["House_number"] = GEO.get("house_number","")
            #item ["Zip_code_code"] = GEO.get("zip_code","")
            
            info_rental_details = titles.select('div[@class="info_rental details"]/div[@class="col_left"]/p/text()').extract()
            Rooms = None
            for d in info_rental_details:
                if d.find("Sovrum")>0 :
                    
                    Rooms =  parse_price(d)
                elif  d.find(" m")>0 :
                    
                    Area =  parse_price(d)
                
            item['Rooms'] = Rooms
            item['Area'] = Area

            item["Property_type"] = "Holiday Property"
            item["property_url"] = response.url
            item['external_property_id'] = hashtxt(response.url)
            
            items.append(item)
        return(items)
