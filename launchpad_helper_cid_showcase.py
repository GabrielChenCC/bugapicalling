from launchpad_helper import LaunchpadAssistant
import re

cids = ["202312-32368", "202312-32369","202311-32351"]
projectx="sutton"

lp_api_return={}

for x in cids:
    cid = x

    la = LaunchpadAssistant()

    for bug in la.search_bugs(projectx, cid):
        
        bug_number = bug[0].id
        contents=bug[0].description
        print(contents)
        match = re.search(r"\[Failure rate\](.*?)\[Stage\]", contents, flags=re.DOTALL)

        if match:
          # Extract the captured group (content within the section)
          additional_info = match.group(1).strip()
          print(additional_info)
        else:
          print("Could not find the Additional Information section")
        url = f"https://bugs.launchpad.net/{projectx}/+bug/{bug_number}"
        
        for key in lp_api_return.keys():
             pass 
              
        if bug_number in lp_api_return.keys():
            # add cid number            
            lp_api_return[bug_number]["CID"].append(cid)
        
        else:
            title = bug[1]["title"]
            # Extract the content between the triple quotes
            pattern1 = r'"(.*?)"'
            match1 = re.search(pattern1, title)

            if match1:
                content = match1.group(1)
            #print(content)
            else:
                print("No content found")

            lp_api_return_single = {"link":url, "title":content, "CID":[cid]}
            lp_api_return.update({bug_number:lp_api_return_single})
print(lp_api_return)

