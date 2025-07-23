# this python file is used to preprocess the data of different sources to a unified 
# knowledge base foramt, i.e. a list of text contents to mimic internal knowledge base
# or tools such as screening, news search, etc.

import json
import os
import csv
from typing import List, Tuple, Dict, Any

def infer_dataset_name(folder_path: str) -> str:
    folder_name = os.path.basename(folder_path).lower()
    if 'ofac-sdn' in folder_name:
        return "US OFAC Specially Designated Nationals (SDN)"
    elif 'fbi-most-wanted' in folder_name:
        return "US FBI Most Wanted"
    elif 'canada-sanctions' in folder_name:
        return "Canadian Consolidated Autonomous Sanctions"
    else:
        return "Unknown Dataset"

def format_entity_description(entity: Dict[str, Any], dataset_name: str) -> str:
    properties = entity.get('properties', {})
    schema = entity.get('schema', 'Unknown')
    lines = [dataset_name]
    
    name = ""
    if 'name' in properties and properties['name']:
        name = properties['name'][0] if isinstance(properties['name'], list) else properties['name']
    elif 'caption' in entity:
        name = entity['caption']
    
    if name:
        lines.append(f"{name}")
    
    lines.append(f"{schema}")
    
    if schema == "Person":
        if 'gender' in properties and properties['gender']:
            gender = properties['gender'][0] if isinstance(properties['gender'], list) else properties['gender']
            lines.append(f"{gender.title()}")
        
        if 'birthDate' in properties and properties['birthDate']:
            birth_dates = properties['birthDate'] if isinstance(properties['birthDate'], list) else [properties['birthDate']]
            lines.append(f"DOB: {birth_dates[0]}")
        
        if 'nationality' in properties and properties['nationality']:
            nationalities = properties['nationality'] if isinstance(properties['nationality'], list) else [properties['nationality']]
            lines.append(f"{nationalities[0].upper()}")
    
    elif schema in ["Organization", "LegalEntity"]:
        if 'country' in properties and properties['country']:
            countries = properties['country'] if isinstance(properties['country'], list) else [properties['country']]
            lines.append(f"{countries[0].upper()}")
        
        if 'incorporationDate' in properties and properties['incorporationDate']:
            inc_dates = properties['incorporationDate'] if isinstance(properties['incorporationDate'], list) else [properties['incorporationDate']]
            lines.append(f"Inc: {inc_dates[0]}")
    
    elif schema == "Vessel":
        if 'flag' in properties and properties['flag']:
            flags = properties['flag'] if isinstance(properties['flag'], list) else [properties['flag']]
            lines.append(f"Flag: {flags[0].upper()}")
        
        if 'imoNumber' in properties and properties['imoNumber']:
            imo_numbers = properties['imoNumber'] if isinstance(properties['imoNumber'], list) else [properties['imoNumber']]
            lines.append(f"IMO: {imo_numbers[0]}")
    
    return '\n'.join(lines)

def process_json_files(data_raw_path: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    sources = []
    descriptions = []
    ids = []
    names = []
    
    for folder_name in os.listdir(data_raw_path):
        folder_path = os.path.join(data_raw_path, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
        
        json_file_path = os.path.join(folder_path, 'entities.ftm.json')
        
        if not os.path.exists(json_file_path):
            continue
        
        print(f"Processing {json_file_path}...")
        
        dataset_name = infer_dataset_name(folder_path)
        
        with open(json_file_path, 'r', encoding='utf-8') as file:
            line_count = 0
            for line in file:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entity = json.loads(line)
                    
                    if not entity.get('target', True):
                        continue
                    
                    schema = entity.get('schema', '')
                    if schema not in ['Person', 'Organization', 'LegalEntity', 'Vessel']:
                        continue
                    
                    description = format_entity_description(entity, dataset_name)
                    entity_id = entity.get('id', '')
                    entity_name = entity.get('caption', '')
                    
                    sources.append(dataset_name)
                    descriptions.append(description)
                    ids.append(entity_id)
                    names.append(entity_name)
                    
                    line_count += 1
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON in {json_file_path}: {e}")
                    continue
        
        print(f"Processed {line_count} entities from {folder_name}")
    
    return sources, descriptions, ids, names

def save_results_to_files(sources: List[str], descriptions: List[str], ids: List[str], names: List[str], output_dir: str = "."):
    descriptions_file = os.path.join(output_dir, "entity_descriptions.txt")
    with open(descriptions_file, 'w', encoding='utf-8') as f:
        for i, desc in enumerate(descriptions):
            f.write(f"{i+1}:\n")
            f.write(desc)
            f.write("\n\n")
    
    csv_file = os.path.join(output_dir, "processed_data.csv")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Source', 'ID', 'Name', 'Description'])
        for source, entity_id, name, desc in zip(sources, ids, names, descriptions):
            writer.writerow([source, entity_id, name, desc])
    
    import json
    data = {
        "sources": sources,
        "descriptions": descriptions,
        "ids": ids,
        "names": names,
        "count": len(descriptions)
    }
    
    json_file = os.path.join(output_dir, "processed_data.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(descriptions)} entities to {csv_file}, {json_file}, {descriptions_file}")

def show_entity_type_examples(sources: List[str], descriptions: List[str], ids: List[str], names: List[str]):
    person_examples = []
    org_examples = []
    vessel_examples = []
    
    for i, desc in enumerate(descriptions):
        if "Person" in desc and len(person_examples) < 1:
            person_examples.append((i, desc, ids[i], names[i]))
        elif "Organization" in desc and len(org_examples) < 1:
            org_examples.append((i, desc, ids[i], names[i]))
        elif "LegalEntity" in desc and len(org_examples) < 1:
            org_examples.append((i, desc, ids[i], names[i]))
        elif "Vessel" in desc and len(vessel_examples) < 1:
            vessel_examples.append((i, desc, ids[i], names[i]))
        
        if len(person_examples) >= 1 and len(org_examples) >= 1 and len(vessel_examples) >= 1:
            break
    
    print("\nExamples:")
    
    if person_examples:
        print("\nPerson:")
        idx, desc, entity_id, name = person_examples[0]
        print(desc)
    
    if org_examples:
        print("\nOrganization:")
        idx, desc, entity_id, name = org_examples[0]
        print(desc)
    
    if vessel_examples:
        print("\nVessel:")
        idx, desc, entity_id, name = vessel_examples[0]
        print(desc)

def main(add_tpl_data: bool = False):
    """Main function to process all JSON files and output results"""
    
    # Path to data_raw folder
    data_raw_path = "../data_raw"
    
    print("Starting to process JSON files...")
    sources, descriptions, ids, names = process_json_files(data_raw_path)
    
    # Process TPL data if requested
    if add_tpl_data:
        tpl_csv_path = "../data_intake/tpl_most_wanted.csv"
        tpl_sources, tpl_descriptions, tpl_ids, tpl_names = process_tpl_csv(tpl_csv_path)
        
        # Combine the data
        sources.extend(tpl_sources)
        descriptions.extend(tpl_descriptions)
        ids.extend(tpl_ids)
        names.extend(tpl_names)
    
    print(f"\nProcessed {len(descriptions)} entities total")
    
    # Show different entity type examples
    show_entity_type_examples(sources, descriptions, ids, names)
    
    # Save results to files including CSV
    save_results_to_files(sources, descriptions, ids, names)
    
    return sources, descriptions, ids, names

def demonstrate_usage():
    """Demonstrate how to access and use the processed data"""
    
    # Load the processed data from JSON file
    with open("processed_entities.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sources = data['sources']
    descriptions = data['descriptions']
    ids = data['ids']
    names = data['names']
    
    print("="*60)
    print("DEMONSTRATION: How to use the processed data")
    print("="*60)
    
    print(f"\nTotal entities processed: {data['count']}")
    
    # Find a specific entity by ID
    target_id = "NK-22HtK7WrxZ2sU3rmhz6PuZ"  # Michael Kuajien
    try:
        index = ids.index(target_id)
        print(f"\nExample - Finding entity by ID '{target_id}':")
        print(f"Index: {index}")
        print(f"Source: {sources[index]}")
        print(f"Name: {names[index]}")
        print("Description:")
        print(descriptions[index])
    except ValueError:
        print(f"Entity with ID '{target_id}' not found")
    
    # Show stats by source
    print(f"\nDataset statistics:")
    ofac_count = sum(1 for source in sources if "US OFAC" in source)
    fbi_count = sum(1 for source in sources if "US FBI" in source)
    canada_count = sum(1 for source in sources if "Canadian" in source)
    tpl_count = sum(1 for source in sources if "Toronto Police" in source)
    
    print(f"- US OFAC SDN: {ofac_count} entities")
    print(f"- US FBI Most Wanted: {fbi_count} entities") 
    print(f"- Canadian Sanctions: {canada_count} entities")
    if tpl_count > 0:
        print(f"- Toronto Police Service Most Wanted: {tpl_count} entities")
    
    # Show entity type breakdown
    person_count = sum(1 for desc in descriptions if "Type: Person" in desc)
    org_count = sum(1 for desc in descriptions if "Type: Organization" in desc)
    legal_count = sum(1 for desc in descriptions if "Type: LegalEntity" in desc)
    vessel_count = sum(1 for desc in descriptions if "Type: Vessel" in desc)
    
    print(f"\nEntity type breakdown:")
    print(f"- Persons: {person_count}")
    print(f"- Organizations: {org_count}")
    print(f"- Legal Entities: {legal_count}")
    print(f"- Vessels: {vessel_count}")
    
    print(f"\nCSV file structure:")
    print("Column 1: Source (e.g., 'US OFAC Specially Designated Nationals (SDN)')")
    print("Column 2: ID (e.g., 'NK-22HtK7WrxZ2sU3rmhz6PuZ')")
    print("Column 3: Name/Caption (e.g., 'Michael Kuajien')")
    print("Column 4: Description (full text description)")

def format_tpl_entity_description(row: Dict[str, str]) -> str:
    lines = ["Toronto Police Service Most Wanted"]
    
    if row.get('name'):
        lines.append(f"Name: {row['name']}")
    
    lines.append("Type: Person")
    
    if row.get('gender'):
        gender_map = {'M': 'Male', 'F': 'Female'}
        gender = gender_map.get(row['gender'], row['gender'])
        lines.append(f"Gender: {gender}")
    
    if row.get('date_of_birth'):
        lines.append(f"Date of Birth: {row['date_of_birth']}")
    
    if row.get('age'):
        lines.append(f"Age: {row['age']}")
    
    if row.get('link'):
        lines.append(f"Source URL: {row['link']}")
    
    if row.get('homicide_case'):
        lines.append(f"Homicide Case: {row['homicide_case']}")
    
    if row.get('case_number'):
        lines.append(f"Case Number: {row['case_number']}")
    
    if row.get('division'):
        lines.append(f"Division: {row['division']}")
    
    return '\n'.join(lines)

def extract_id_from_url(url: str) -> str:
    """Extract ID from TPL URL ending"""
    if url and url.endswith('/'):
        url = url[:-1]
    
    if url:
        return url.split('/')[-1]
    
    return ""

def process_tpl_csv(tpl_csv_path: str) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Process TPL CSV file and return lists of sources, descriptions, IDs, and names"""
    
    sources = []
    descriptions = []
    ids = []
    names = []
    
    if not os.path.exists(tpl_csv_path):
        print(f"TPL CSV file not found: {tpl_csv_path}")
        return sources, descriptions, ids, names
    
    print(f"Processing {tpl_csv_path}...")
    
    with open(tpl_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        line_count = 0
        
        for row in reader:
            if not row.get('name'):
                continue
            
            description = format_tpl_entity_description(row)
            
            entity_id = row.get('suspect_id', '')
            if not entity_id and row.get('link'):
                entity_id = extract_id_from_url(row['link'])
            
            if not entity_id:
                entity_id = f"TPL-{line_count}"
            
            entity_name = row.get('name', '')
            
            sources.append("Toronto Police Service Most Wanted")
            descriptions.append(description)
            ids.append(entity_id)
            names.append(entity_name)
            
            line_count += 1
    
    print(f"Processed {line_count} entities from TPL CSV")
    return sources, descriptions, ids, names

if __name__ == "__main__":
    import sys
    
    # Configuration variable
    add_tpl_data = False
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if '--include-tpl' in sys.argv or '--tpl' in sys.argv:
            add_tpl_data = True
            print("Including TPL data in processing...")
    
    # You can also set this directly in the code
    # add_tpl_data = True
    
    sources, descriptions, ids, names = main(add_tpl_data=add_tpl_data)
    
    # Demonstrate usage
    demonstrate_usage()
