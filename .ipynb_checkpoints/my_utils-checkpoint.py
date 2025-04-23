#### Imports ####
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import sqlite3
from pathlib import Path
import string
import os
import requests

#=== function to scan addgene pages ===#
def scan_addgene(parameters):
    ## NOTE: the addgene website will only provide 600 pages in the search results, so will have to figure out a workaround
    ## NOTE: a better workaround is to use a dictionay of molecular biology terms, gene names, and species names
    ## NOTE: 2 second wait time is too little, triggers bot detection on snapgene website
    ## NOTE: Even with 5 second wait time, eventually triggered a (temporary) timeout from addgene website

    ##
    #print(f"Called scan_addgene function with the following parameters: {parameters}")
    print(f"Called scan_addgene function with {len(parameters)} parameters. \n")

    ## Save progress to resume if interrupted
    progress_file = "./scan_addgene_progress.txt"
    print(f"Saving progress to {progress_file}")

    ## Save results
    out_file = "./addgene_IDs.txt"
    print(f"Saving results to {out_file}")
    #
    print("Checking if output file exists")
    if not os.path.exists(out_file):
        with open(out_file, "w") as f:
            pass  # Creates an empty file
        print(f"✅ Created: {out_file}")
    else:
        print(f"⚠️ Already exists: {out_file}")
    
    ## Try to resume from last saved index
    try:
        with open(progress_file, 'r') as f:
            start_index = int(f.read().strip())
    except FileNotFoundError:
        start_index = 0
    #
    print(f"Resuming from index {start_index}")
    
    # Initialize WebDriver
    driver_path = ".//chromedriver-win64//chromedriver-win64//chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    # define sleep time
    sleep_time = 5

    ####
    try:
        
        ## Initialize upper loop
        ## NOTE: need to have code that handles if a search returns no results (blank page)
        #print("Scanning with the following list of characters:", parameters, "\n")
        for i in range(start_index, len(parameters)):

            ##
            param = parameters[i]
            # initialize list to store pladmis IDs
            target_plasmid_IDs = []

            ####
            try:
            
                # Open the target website
                url = 'https://www.addgene.org/'
                driver.get(url)
                time.sleep(sleep_time) # Wait for the page to load
 
                # Locate the search bar element (e.g., by name, id, class, or CSS selector)
                # <input form="search-bar" id="search-text-input" class="suggest-input" aria-expanded="false" aria-haspopup="listbox" type="text" role="combobox" autocomplete="off" placeholder="e.g. 74218, Cas9, transformation protocol" name="q" aria-owns="awesomplete_list_2">
                search_bar = driver.find_element(By.ID, 'search-text-input') 
    
                # Enter text into the search bar
                # to search specifically for GFP-containing plasmids
                #search_text = "GFP"  # Replace with the text you want to enter
                # modifying to pull the whole database
                print("Scanning with current parameter:", param, "\n")
                search_text = param
                search_bar.send_keys(search_text)
    
                # Submit the search (if needed, e.g., by pressing Enter)
                search_bar.send_keys(Keys.RETURN)
                # Wait for the results to load
                time.sleep(sleep_time)

                # Select the plasmids subcategory
                inplasmids_bar = driver.find_element(By.XPATH, "//span[@class='leaf-label' and text()='in Plasmids']")
                inplasmids_bar.click() # click it

                # Wait for the results to load
                time.sleep(sleep_time)

                # <a href="/185404/">GFP1-10-miniCMV-GFP11×11-GFP-tDeg</a>
                # Find all elements with an 'href' attribute
                elements_with_href = driver.find_elements(By.XPATH, "//a[@href]")
                # Extract the href values and store them in a list
                href_list = [element.get_attribute('href') for element in elements_with_href]
                # Print the list of hrefs
                # print("List of hrefs:", href_list)

                # filter the useful href
                # Regular expression to match only URLs starting with 'https://'
                regex = r"addgene.org/\d\d\d\d\d{1,2}/"
                # Filter the list using the regex
                filtered_items = [item for item in href_list if re.search(regex, item)]
                # Print the filtered list
                print("Number of filtered items:", len(filtered_items), "\n")
                #print("Filtered items:", filtered_items, "\n")

                # target page at this step should be showing 20 plasmids per page, but we are getting returned only 14 IDs after regex
                ## NOTE: check if some IDs can have 1-4 digits also
                # manually constructing list of hrefs from first page to determine which are missing
                # <a href="/185404/">GFP1-10-miniCMV-GFP11×11-GFP-tDeg</a>
                # <a href="/87906/">pENTR221-H1-sgGFP1-U6-sgGFP2-7SK-sgGFP3</a>
                # <a href="/133815/">pFSW GFP IRES GFP</a>
                # After first 3 entries, it appears the ones missed have 5 digits, not 6. updating regex

                #### Pull numbers from the filtered strings
                # Remove everything except digits from each string
                clean_IDs = [re.sub(r"\D", "", item) for item in filtered_items]
                # Print the result
                #print("Cleaned IDs", clean_IDs, "\n")
                print("Current number of cleaned IDs:", len(clean_IDs), "\n")

                #### Add items to the list
                target_plasmid_IDs = target_plasmid_IDs + clean_IDs
                #print("Current list of target plasmid IDs", target_plasmid_IDs, "\n")
                print("Current number of target plasmid IDs:", len(target_plasmid_IDs), "\n")

                ## temporarily store the IDs from the current page to compare to the next page
                prev_IDs = clean_IDs

                ## append items to text file
                print(f"Appending current IDs to output file {out_file}")
                with open(out_file, "a") as f:  # "a" = append mode
                    for item in target_plasmid_IDs:
                        f.write(item + "\n")

                #### Initialize lower loop to pass through next 600 pages of results
                ## NOTE: many search pages will have fewer than 600 result pages. Add a loop interrupt if this is the case
                for i in range(1, 601):

                    #
                    print(f"Current search parameter: {param}, Current page Number: {i}")
                    # <a class="page-link" href="/search/catalog/plasmids/?q=gfp&amp;page_number=2">Next</a>
                    # Find the next button and click it
                    next_button = driver.find_element(By.LINK_TEXT, "Next")
                    next_button.click() # click it

                    # Wait for the results to load
                    time.sleep(sleep_time)

                    ##
                    elements_with_href = driver.find_elements(By.XPATH, "//a[@href]")
                    href_list = [element.get_attribute('href') for element in elements_with_href]
                    regex = r"addgene.org/\d\d\d\d\d{1,2}/"
                    filtered_items = [item for item in href_list if re.search(regex, item)]
                    clean_IDs = [re.sub(r"\D", "", item) for item in filtered_items]
                    # add the new IDs to the list
                    target_plasmid_IDs = target_plasmid_IDs + clean_IDs
                    
                    ## check for identical items, break loop if yes
                    print("Checking if IDs on this page are identical to the previous page. \n")
                    if set(clean_IDs) == set(prev_IDs):
                        print("Plasmid IDs match previous page, skipping to next search parameter. \n")
                        break

                    ##
                    else:
                        print("Current IDs do not match IDs from previous page. Proceeding. \n")
                        ##
                        target_plasmid_IDs = target_plasmid_IDs + clean_IDs
                        # remove any duplicates
                        target_plasmid_IDs = list(set(target_plasmid_IDs))
                        # report
                        #print("Current list of target plasmid IDs", target_plasmid_IDs, "\n")
                        print("Number of unique IDs:", len(target_plasmid_IDs), "\n")
                        ## update list of prev page IDs
                        ## temporarily store the IDs from the current page to compare to the next page
                        prev_IDs = clean_IDs
            
            ##
            except:
                ##
                print("Exception encountered, skipping to next search parameter. \n")
                
                ## increment progress tracker
                print("Incrementing progress tracker")
                with open(progress_file, 'w') as f:
                    f.write(str(i + 1))

                ## append items to text file
                print(f"Appending current IDs to output file {out_file}")
                with open(out_file, "a") as f:  # "a" = append mode
                    for item in target_plasmid_IDs:
                        f.write(item + "\n")
            
            ##
            finally:
                ##
                print(f"Completed scan with parameter: {param}")
                ##
                print("Incrementing progress tracker")
                with open(progress_file, 'w') as f:
                    f.write(str(i + 1))
                ## append items to text file
                print(f"Appending current IDs to output file {out_file}")
                with open(out_file, "a") as f:  # "a" = append mode
                    for item in target_plasmid_IDs:
                        f.write(item + "\n")
    ##
    except:
        print("Exception encountered. \n")
        print("Incrementing progress tracker")
        with open(progress_file, 'w') as f:
            f.write(str(i + 1))
        
    ##
    finally:
        # Close the WebDriver
        print(f"Operation complete.")
        driver.quit()


#=== function to parse field elements ===#
def parse_fields(target_text, driver):
    #
    #print(f"Called parse_fields function with target text: {target_text}")
    #
    fields = driver.find_elements(By.CSS_SELECTOR, "li.field")
    #print(f"Identified {len(fields)} fields\n")
    #
    for field in fields:
        #print(f"Current field value: {field}\n")
        if target_text in field.text:
            full_text = field.text.strip()
            label = field.find_element(By.CLASS_NAME, "field-label").text.strip()
            value = full_text.replace(label, "").strip()
            break
    #
    #print(f"Returning value of: {value}\n")
    return(value)


#=== Function to scrape plasmid info and genbank full sequence ===#
## NOTE: the "publication" hyperlink on addgene website is just a link to an internal record page on addgene, pull only citation for now
## NOTE: the file progress tracker helps, but it needs to be augmented by an ability to reset the tracker, and a filecheck for the sequence
## NOTE: in the target folder before starting the scrape, so that we can be sure to get all targer sequences and not redownload unnecessarily
def scrape_plasmid_data(plasmid_IDs, reset=False):


    ##
    #print(f"Called scan_addgene function with the following parameters: {parameters}")
    print(f"Called scrape_plasmid_data function with {len(plasmid_IDs)} plasmid IDs.")

    ## Initialize driver
    print("Initializing web driver")
    driver_path = ".//chromedriver-win64//chromedriver-win64//chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    ## Save progress to resume if interrupted
    progress_file = "./scrape_plasmid_data_progress.txt"
    print(f"Saving progress to {progress_file}")

    ## Reset the progress tracker if true
    if reset:
        print("Resetting progress tracking to 0")
        with open(progress_file, 'w') as f:
            f.write(str(0))
            start_index = 0
    else:
        ## Try to resume from last saved index
        try:
            with open(progress_file, 'r') as f:
                start_index = int(f.read().strip())
        except FileNotFoundError:
            open(progress_file, "w").close()
            start_index = 0
            
    #
    print(f"Resuming from index {start_index}")

    ## Initialize the loop ##
    for i in range(start_index, len(plasmid_IDs)):
        
        #
        try:

            #
            plasmid_ID = plasmid_IDs[i]
            print(f"Scraping data for plasmid {plasmid_ID}")

            ## Check if there is a .gbk file in the target directory. If yes, skip to next plasmid
            # create the output directory for the plasmid info. store locally
            output_dir = Path("../0.local/scrape-addgene/plasmids/" + str(plasmid_ID) + "/")
            #
            print(f"Checking for .gbk files at {output_dir}")
            gbk_files = list(output_dir.glob("*.gbk"))

            ##
            if gbk_files:
                print("Sequence file detected in target directory. Skipping to next plasmid")
            ##
            else:
                #    
                os.makedirs(output_dir, exist_ok=True)  # Create output directory if it doesn't exist
                print(f"Created output directory for plasmid info at {output_dir}")

                # define sleep time
                sleep_time = 5

                # Open the target website
                url = 'https://www.addgene.org/'
                plasmid_url = url + plasmid_ID
                print(f"Opening plasmid webpage at: {plasmid_url}")
                driver.get(plasmid_url)
                time.sleep(sleep_time)

                ## Instantiate the temporary storage
                #print("Instantiating dictionary")
                current_info = {
                    "addgene_ID": None,
                    "plasmid_name": None,
                    "plasmid_purpose": None,
                    "depositor": None,
                    "vector_backbone": None,
                    "backbone_size": None,
                    "total_size": None,
                    "insert_size": None,
                    "vector_type": None,
                    "selectable_markers": None,
                    "bacterial_resistance": None,
                    "growth_temperature": None,
                    "growth_strain": None,
                    "copy_number": None,
                    "gene_insert_name": None,
                    "species": None,
                    "genbank_ID": None,
                    "entrez_gene": None,
                    "tag_fusion_protein": None,
                    "cloning_method": None,
                    "citation": None,
                    "commonly_requested_with": None
                }

                #### Pull the info from the webpage  ####
                print("Scraping plasmid info")
                try: 
                    current_info["addgene_ID"] = plasmid_ID
                except:
                    pass
                try: 
                    current_info["vector_backbone"] = parse_fields("Vector backbone", driver)
                except:
                    pass
                try: 
                    current_info["backbone_size"] = int(parse_fields("Backbone size", driver))
                except:
                    pass
                try: 
                    current_info["total_size"] = int(parse_fields("Total vector size", driver))
                except:
                    pass
                try: 
                    current_info["insert_size"] = current_info["total_size"] - current_info["backbone_size"]
                except:
                    pass
                try: 
                    current_info["vector_type"] = parse_fields("Vector type", driver)
                except:
                    pass
                try: 
                    current_info["selectable_markers"] = parse_fields("Selectable markers", driver)
                except:
                    pass
                try: 
                    current_info["bacterial_resistance"] = parse_fields("Bacterial Resistance", driver)
                except:
                    pass
                try: 
                    current_info["growth_temperature"] = parse_fields("Growth Temperature", driver)
                except:
                    pass
                try: 
                    current_info["growth_strain"] = parse_fields("Growth Strain", driver)
                except:
                    pass
                try: 
                    current_info["copy_number"] = parse_fields("Copy number", driver)
                except:
                    pass
                try: 
                    current_info["gene_insert_name"] = parse_fields("Gene/Insert name", driver)
                except:
                    pass
                try: 
                    current_info["species"] = parse_fields("Species", driver)
                except:
                    pass
                try: 
                    current_info["genbank_ID"] = parse_fields("GenBank ID", driver)
                except:
                    pass
                try: 
                    current_info["entrez_gene"] = parse_fields("Entrez Gene", driver)
                except:
                    pass
                try: 
                    current_info["tag_fusion_protein"] = parse_fields("Fusion Protein", driver)
                except:
                    pass
                try: 
                    current_info["cloning_method"] = parse_fields("Cloning method", driver)
                except:
                    pass

                ## plasmid name ##
                # Find element labelled title
                try:
                    plasmid_name = driver.title
                    #print("Plasmid name:", plasmid_name)
                    current_info["plasmid_name"] = plasmid_name
                except:
                    pass

                ## plasmid purpose ##
                try:
                    labels = driver.find_elements(By.CLASS_NAME, "field-label") # Find all field-label divs
                    # Loop to find the label "Purpose" and get the next sibling (field-content)
                    for label in labels:
                        if label.text.strip() == "Purpose":
                            # Get the parent of the label, then find the corresponding content
                            content = label.find_element(By.XPATH, 'following-sibling::div[@class="field-content"]')
                            plasmid_purpose = content.text.strip()
                            break
                    current_info["plasmid_purpose"] = plasmid_purpose
                except:
                    pass

                ## depositing lab ##
                try:
                    labels = driver.find_elements(By.CLASS_NAME, "field-label")
                    for label in labels:
                        if label.text.strip() == "Depositing Lab":
                            content_div = label.find_element(By.XPATH, 'following-sibling::div[@class="field-content"]')
                            link = content_div.find_element(By.TAG_NAME, "a")
                            depositor = link.text.strip()
                            break
                    #print("depositor:", depositor, "\n")
                    current_info["depositor"] = depositor
                except:
                    pass

                # Extract full text of citation
                try:
                    cite_element = driver.find_element(By.TAG_NAME, "cite")
                    full_text = cite_element.text
                    # Extract DOI (last part of citation text)
                    doi = full_text.split("doi:")[1].split()[0] if "doi:" in full_text else None
                    # Display parsed info
                    #print("DOI:", doi)
                except:
                    pass

                ## commonly requested with ##
                try:
                    # Find all <a class="material-name"> elements inside the "Commonly requested with" panel
                    links = driver.find_elements(By.CSS_SELECTOR, ".panel-body a.material-name")
                    # Extract all digit values from the href attributes
                    digits = []
                    for link in links:
                        href = link.get_attribute("href")
                        match = re.search(r'/(\d+)/', href)
                        if match:
                            digits.append(int(match.group(1)))
                    #print("Extracted digit values:", digits)
                    current_info["commonly_requested_with"] = digits
                except:
                    pass

                ## output the list info
                plasmid_info_file = output_dir + "/" + plasmid_ID + ".txt"

                # Write to file as tab-delimited
                with open(plasmid_info_file, "w",  encoding="utf-8") as f:
                    for key, value in current_info.items():
                        f.write(f"{key}\t{value}\n")

                print(f"Dictionary written to {plasmid_info_file}")

                #### Download the full plasmid fasta sequence ####
                ## locate the sequences button
                # wait for previous processing to complete
                time.sleep(sleep_time) # Wait for the page to load
                # sequences webpage will be plasmid ID followed by 'sequences
                # navigate to sequences page

                sequences_url = plasmid_url + "/sequences"
                #print(sequences_url)
                driver.get(sequences_url)
                time.sleep(sleep_time) # Wait for the page to load
                genbank_link = driver.find_element(By.CSS_SELECTOR, "a.genbank-file-download")
                gbk_url = genbank_link.get_attribute("href")
                filename = gbk_url.split("/")[-1]
                gbk_output_path = os.path.join(output_dir, filename)
                #
                response = requests.get(gbk_url)
                with open(gbk_output_path, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded .gbk file to: {gbk_output_path}")

                ##
                print("Incrementing progress tracker")
                with open(progress_file, 'w') as f:
                    f.write(str(i + 1))

        # Exception
        except:
            print(f"Exception occurred when scraping data for {plasmid_ID}. Proceeding to next ID")
            # increment progress tracker
            print("Incrementing progress tracker")
            with open(progress_file, 'w') as f:
                f.write(str(i + 1))


    # Finally
    #### Close the driver ####
    print("Completed scrape")
    driver.quit()

        
