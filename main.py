from flask import Flask, render_template
from flask import request
import geonamescache
from tenacity import retry
from tenacity import stop_after_delay
from tenacity import RetryError
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from translate import Translator
import pandas as pd
import json
from pytrends.request import TrendReq
import time, random
from pytrends.exceptions import TooManyRequestsError
import geonamescache
import json, os
import plotly
import plotly.express as px

gc = geonamescache.GeonamesCache()
all_cities=list(gc.get_cities().values())

country_lang_dict={
    "China":"Chinese",
    "Egypt":"Arabic",
    "France":"French",
    "Germany":"German",
    "India":"Hindi",
    "Italy":"Italian",
    "Japan":"Japanese",
    "Netherlands":"Dutch",
    "Poland":"Polish",
    "Saudi Arabia":"Arabic",
    "South Korea":"Korean",  
}

country_iso_dict={
    "Canada":"CA",
    "China":"CN",
    "Egypt":"EG",
    "England":"GB",
    "Germany":"DE",
    "France":"FR",
    "Germany":"DE",
    "India":"IN",
    "Israel":"IL",
    "Italy":"IT", 
    "Japan":"JP",    
    "Kenya":"KE",
    "Netherlands":"NL",
    "Nigeria":"NG",   
    "Ghana":"GH",
    "Poland":"PL",
    "Saudi Arabia":"SA",
    "South Africa":"ZA",
    "South Korea":"KR",     
    "Spain":"ES",
    "Tanzania":"TZ",
    "Uganda":"UG",
    "United States":"US",
    "Zimbabwe":"ZW", 
    
}
option_tag_string_countries=''
for index,value in enumerate(list(country_iso_dict.keys())):
    option_tag_string_countries=option_tag_string_countries+(f'<option value="{value}">{value}</option>')
    
def filter_cities_by_country_code_new(city_data, target_country_code):
    filtered_cities = []
    
    for city in city_data:
        if city['countrycode'] == target_country_code:
            filtered_cities.append([city.get('name','').replace('City','').replace('city','').strip(),city.get('population',0)])

    # Sort the filtered cities by population in descending order
    filtered_cities.sort(key=lambda x: x[-1], reverse=True)
    return [item[0] for item in filtered_cities]

cities_countries_dict = {}
for idx,item in enumerate(list(country_iso_dict.values())):
    cities_countries_dict[list(country_iso_dict.keys())[idx]] = filter_cities_by_country_code_new(all_cities, item)

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(10))
def sendPytrendReqTimeframe(lst,country_code,timeframe):
    try:
        pytrends = TrendReq(timeout=(3,30),retries=3)
        pytrends.build_payload(lst, cat=0, geo=country_code, gprop='',timeframe=timeframe)
        return (pytrends.interest_over_time(), 'success')
    except Exception as e:
        if 'The server is currently overloaded with other requests' in e:
            raise Exception
        else:
            return (e, 'failed')
        
@retry(wait=wait_exponential(multiplier=1, min=4, max=6), stop=stop_after_attempt(4))
def sendPytrendReqCountry(lst,timeframe):
    try:
        pytrends = TrendReq(timeout=(3,30),retries=3)
        pytrends.build_payload(lst, cat=0, gprop='',timeframe=timeframe)
        return (pytrends.interest_by_region(resolution='COUNTRY'), 'success')
    except Exception as e:
        if 'The server is currently overloaded with other requests' in e:
            raise Exception
        else:
            return (e, 'failed')
        
@retry(wait=wait_exponential(multiplier=1, min=4, max=6), stop=stop_after_attempt(4))
def sendPytrendReqRegion(lst,country_code,timeframe):
    try:
        pytrends = TrendReq(timeout=(3,30),retries=3)
        pytrends.build_payload(lst, cat=0, geo=country_code, gprop='',timeframe=timeframe)
        return (pytrends.interest_by_region(resolution='REGION'), 'success')
    except Exception as e:
        if 'The server is currently overloaded with other requests' in e:
            raise Exception
        else:
            return (e, 'failed')
        
def filter_cities_by_country_code(city_data, target_country_code):
    filtered_cities = []

    for city in city_data:
        if city['countrycode'] == target_country_code:
            filtered_cities.append([city.get('name','').replace('City','').replace('city','').strip(),city.get('population',0)])

    # Sort the filtered cities by population in descending order
    filtered_cities.sort(key=lambda x: x[-1], reverse=True)

    return filtered_cities

app = Flask(__name__)

@app.route('/plot',methods=['POST'])
def plot():
    keyword = request.form.get('keyword')
    country = request.form.get('country')
    # city_flag = request.form.get('includeCity')
    # if city_flag:
    #     city = request.form.get('city')
    # else:
    #     city = None    
    timeframe_flag = request.form.get('timeframe')
    
    if timeframe_flag=="all":
        timeframe = "all"
    elif timeframe_flag=="last5Years":
        timeframe = "today 5-y"
    else:
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        timeframe = f"{start_date} {end_date}"
    translate_flag = request.form.get('translate')   
    country_code=country_iso_dict[country]
    language= False
    if translate_flag:
        if country not in list(country_lang_dict.keys()):
            language=False 
        else:
            language=country_lang_dict[country]

    if language:
        translator= Translator(to_lang=language)            
    if translate_flag and language:
        keyword=translator.translate(keyword)
    # if city_flag:
    #     keyword=keyword+' '+city

    timeframe_df=sendPytrendReqTimeframe([keyword],country_code,timeframe)[0]
#     try:
#         country_df=sendPytrendReqCountry([keyword],timeframe)[0]
#     except:
#         country_df=[]
    try:
        region_df=sendPytrendReqRegion([keyword],country_code,timeframe)[0]
    except:
        region_df=[]
    
    
    if len(timeframe_df)==0:
        graphJSON1=json.dumps({"error":"no"})
    else:
        timeframe_df['date']=timeframe_df.index
        fig1 = px.line(timeframe_df, x='date', y=keyword)
        fig1.update_layout(
            autosize=True,
            width=1000,  # Adjust the width as per your preference
            height=600  # Adjust the height as per your preference
        )  
        graphJSON1 = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    
        
#     if len(country_df)==0:
#         graphJSON2='No Data'
#     else:    
#         country_df['countries']=country_df.index
#         fig2 = px.bar(country_df, x='countries', y=keyword)
#         fig2.update_layout(
#             autosize=False,
#             width=1000,  # Adjust the width as per your preference
#             height=600  # Adjust the height as per your preference
#         )    
#         graphJSON2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
        
         
    if len(region_df)==0:
        graphJSON2='No Data'
    else:      
        region_df['regions']=region_df.index
        fig2 = px.bar(region_df, x='regions', y=keyword)
        fig2.update_layout(
            autosize=True,
            width=1000,  # Adjust the width as per your preference
            height=600  # Adjust the height as per your preference
        )        
        graphJSON2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template(f'plot.html', option_tag_string_countries=option_tag_string_countries, cities_countries_dict=cities_countries_dict,graphJSON1=graphJSON1, graphJSON2=graphJSON2)

@app.route('/')
def select_option():
    return render_template(f'change_plot.html', option_tag_string_countries=option_tag_string_countries, cities_countries_dict=cities_countries_dict)    


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))

