from bs4 import BeautifulSoup
import requests
import country_converter as coco
import pandas as pd
from flask import Flask, render_template, send_file, request


app = Flask(__name__)

@app.route("/", methods=["POST","GET"])
def home():
    
    if(request.method == "GET"):
        return render_template("homeget.html")
    
    else:
        #Pull year and month from POST and check they're formatted correctly.
        year = request.form["year"]
        month = request.form["month"]
        if len(year)!=4 or len(month)!=2:
            return render_template("homemistake.html")

        else:
            baseURL = "https://www.ic.gc.ca/eic/site/ica-lic.nsf/eng/lk-3"
            yy = year[2:4]
            intYear = int(year)
            searchURL = baseURL + yy + month + ".html"

            #Access Website retrieve HTML
            r = requests.get(searchURL)
            c = r.content
            soup = BeautifulSoup(c, "html.parser")
        
            #Check the page exists
            title = soup.find("h1").text
            if "Error" in title or intYear<1986 or intYear>2099:
                return render_template("norecord.html")

            #Begin accessing and creating data for dataframe
            else:
                purchases = soup.findAll('ul',class_="list-unstyled")
                purchases = purchases[1:-2]
                
                #Check the soup is the right format handle other format if not.
                if len(purchases)<4:
                    purchases = soup.findAll('ul')
                    purchases = purchases[4:-3]
                
            
                #Create date and year data lists
                if month[0] == "0":
                    m = month[-1]

                date = m+"/1/"+year

                date = [date] 
                yearList = [int(year)]
                
                reviewTypes = []
                buyers = []
                targets = []
                business_activities = []
                countries = []

                for purchase in purchases:
                    
                    #Get the review type
                    rT = purchase.findPrevious("h2").text
                    rT = rT.replace("ions", "ion")
                    rT = rT.replace("sses","ss")
                    reviewTypes.append(rT)
                    
                    #Get the name of the Buyer
                    
                    buyerString = purchase.findPrevious("p").findPrevious("p").contents[1]

                    #Need to check if buyer's name is in French, changes HTML pattern
                    try:
                        buyerString.find_all(lang="fr")
                        buyer = buyerString.text
                        #Get buyer's country for later
                        country = purchase.findPrevious("p").findPrevious("p").contents[2]
                        if "of)" in country:
                            country = country.split(',')[-2]
                        else:    
                            country = country.split(',')[-1]
       

                    #If not in French, extract name from the Name, City, Country string
                    except AttributeError:
                        buyerString = buyerString.split(',')
                        if len(",".join(buyerString[0:-3])) > 0:
                            buyer = ",".join(buyerString[0:-3])

                        elif len(",".join(buyerString[0:-2])) > 0:
                            buyer = ",".join(buyerString[0:-2])

                        else:
                            buyer = ",".join(buyerString[0:-1])

                        #Get the Buyer's Country for later
            
                        if "of)" in buyerString[-1]:
                
                            country = buyerString[-2]
                        
                        else:    
                            country = buyerString[-1]



                    buyers.append(buyer)

                    #Now we'll format the buyer's country
                    start = country.find("(") + 1
                    end = country.find(")")
                    
                    #Sometimes they don't include the parentheses so check for that
                    countryCode = country[start:start+3]
                    """
                    if start!=0:
                        countryCode = country[start:start+4]
                    else: 
                        countryCode = country[:4]
                    
                    """
                    
             
                    #print(countryCode)
                    countries.append(countryCode)

                    #Get Targets and their Activities
                    #Set up Dict with activities as keys and empty sets as value
                    targetDict = {}
                    for i, target in enumerate(purchase.findAll("li")):
                        targetActivity = target.p.text.split(": ")[1].strip()

                        #Lower the case of activities after the first one
                        if i != 0 and targetActivity not in targetDict.keys():
                            firstLetter = targetActivity[0].lower()
                            targetActivity = firstLetter + targetActivity[1:]

                        targetDict[targetActivity] = set()


                    #Match Target names to their activities
                    for i, target in enumerate(purchase.findAll("li")):
                        
                        targetActivity = target.p.text.split(": ")[1].strip()
                        #Lower the case of activities after the first one
                        if i != 0 and targetActivity not in targetDict.keys():
                            firstLetter = targetActivity[0].lower()
                            targetActivity = firstLetter + targetActivity[1:]
                        
                        #Check if it's French again
                        try:
                            target.contents[0].find_all(lang="fr")
                            target = target.contents[0].text
                        
                        except AttributeError:
                            targetName = target.contents[0].strip()
                            targetName = targetName.split(",")
                            
                            #Remove location info from target names
                            if len(targetName[0:-3]) != 0:
                                targetName = ",".join(targetName[0:-3])
                            
                            elif len(targetName[0:-2]) != 0:
                                targetName = ",".join(targetName[0:-2])

                            elif len(targetName[0:-1]) != 0 :
                                targetName = ",".join(targetName[0:-1])
                            
                            else:
                                targetName = ",".join(targetName[0:])

                        #Remove " and " from lists of target names
                        if " and " in targetName:
                            andIndex = targetName.index(" and ")
                            if targetName[andIndex-1]==",":
                                targetName = targetName.replace(" and ", " ")
                            else:
                                targetName = targetName.replace(" and ", ", ")

                        targetDict[targetActivity].add(targetName)

                        
                    #Turn the Activity-Target Dict into strings
                    targetStr = ""
                    activityStr = ""
                    for (i,activity) in enumerate(targetDict.keys()):
                        activityStr += activity
                        targetStr+= ", ".join(targetDict[activity])
                        if i+1<len(targetDict.keys()):
                            activityStr+="; "
                            targetStr+="; "

                    activityStr = activityStr.replace(".;",";")
                    business_activities.append(activityStr)
                    targets.append(targetStr)

                #Format the country names properly
                countries = coco.convert(names=countries, to='name_short', not_found = None)
                print(countries)
                for i,country in enumerate(countries):
                    if country == "United States":
                        countries[i] = "USA"
                    
                    if country=="United Kingdom":
                        countries[i]="UK"

                #Prepare Date and Year columns
                date = date*len(buyers)

                yearList = yearList*len(buyers)

                #Create Dict and turn into Pandas DF
                DFDict = {"Investor":buyers,"Canadian Business":targets,"Date":date,"Year":yearList,"Type of Review/Noti":reviewTypes,"Business Activities": business_activities, "Industry (NAICS*) Code":None, "Industry (NAICS*) Code ":None, "Industry (NAICS*) Category":None, "Industry (NAICS*) Category ":None, "Industry (NAICS*) Major":None,"Industry (NAICS*) Major ":None, "Countries":countries}
                df = pd.DataFrame(DFDict)

                #Save DF to Excel
                filename = year + month + "InvestmentCanadaDecisions.xlsx"
                df.to_excel(filename)
                
                return send_file(filename)

if __name__ == "__main__":
    app.run(debug=True)
